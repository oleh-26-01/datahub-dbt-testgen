"""Turn DataHub metadata into dbt tests.

Every rule here cites the metadata that justified it. A test with no evidence is
not emitted — that is the whole point. An LLM asked to write dbt tests will
happily invent a `relationships` test to a table that does not exist; these
rules can only reference tables the catalog actually contains.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Iterable, Sequence

from .catalog import Dataset, Field

# Words that look like identifiers but are not foreign keys.
_NOT_FK = {"external_id", "uuid", "guid", "correlation_id", "request_id", "trace_id"}

# "(e.g., Platinum, Gold, Silver)" / "one of: A, B, C"
_ENUM_HINT = re.compile(
    r"(?:e\.g\.?|for example|one of|values?:|such as)[:,]?\s*\(?([^).]+)\)?",
    re.IGNORECASE,
)


@dataclass
class Test:
    """A single dbt test plus the metadata that justified it."""

    column: str
    name: str                      # not_null | unique | relationships | accepted_values
    because: str                   # human-readable evidence
    config: dict | None = None     # extra YAML for parametrised tests

    def to_yaml_obj(self, *, nest_arguments: bool = True):
        """Render as dbt YAML.

        dbt 1.12 deprecated passing generic-test parameters as bare keys; they
        now belong under `arguments:`. Older projects still expect the flat form,
        so both are supported.
        """
        if self.config is None:
            return self.name
        if nest_arguments:
            return {self.name: {"arguments": self.config}}
        return {self.name: self.config}


@dataclass
class Finding:
    """Something worth telling a human about, that isn't a test."""

    severity: str                  # warn | info
    dataset: str
    message: str


@dataclass
class ModelPlan:
    dataset: Dataset
    tests: list[Test] = dc_field(default_factory=list)
    findings: list[Finding] = dc_field(default_factory=list)

    @property
    def tested_columns(self) -> set[str]:
        return {t.column for t in self.tests}

    @property
    def coverage(self) -> float:
        if not self.dataset.fields:
            return 0.0
        return round(100.0 * len(self.tested_columns) / len(self.dataset.fields), 1)


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("sses") or word.endswith("ches") or word.endswith("shes"):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _looks_like_pk(f: Field, ds: Dataset) -> bool:
    """`customer_id` on table `customers`, or a bare `id`."""
    if f.nullable:
        return False
    name = f.path.lower()
    if name == "id":
        return True
    return name == f"{_singular(ds.table.lower())}_id"


def _plural_forms(stem: str) -> list[str]:
    """Candidate table names for a foreign-key stem.

    `country` -> countries, `address` -> addresses, `region` -> regions. Also
    keeps the bare stem, since some warehouses name tables in the singular.
    """
    forms = [stem, stem + "s"]
    if stem.endswith("y") and len(stem) > 1 and stem[-2] not in "aeiou":
        forms.append(stem[:-1] + "ies")
    if stem.endswith(("s", "x", "z", "ch", "sh")):
        forms.append(stem + "es")
    forms.append(_singular(stem))
    return forms


def _fk_target(f: Field, tables: dict[str, Dataset], ds: Dataset) -> Dataset | None:
    """Resolve `country_id` -> the `countries` dataset, only if it really exists."""
    name = f.path.lower()
    if not name.endswith("_id") or name in _NOT_FK:
        return None
    if _looks_like_pk(f, ds):
        return None
    stem = name[:-3]

    for candidate in _plural_forms(stem):
        target = tables.get(candidate)
        if target is not None and target.urn != ds.urn:
            return target

    # Qualified keys such as `billing_address_id` / `delivery_address_id` refer
    # to the same table as their trailing noun. Only fall back to this once the
    # exact forms above have failed, so `order_item_id` still prefers
    # `order_items` over `items`.
    if "_" in stem:
        tail = stem.rsplit("_", 1)[-1]
        for candidate in _plural_forms(tail):
            target = tables.get(candidate)
            if target is not None and target.urn != ds.urn:
                return target
    return None


def _accepted_values(f: Field) -> list[str] | None:
    """Pull an enum out of a human-written column description."""
    if not f.description or f.is_numeric:
        return None
    m = _ENUM_HINT.search(f.description)
    if not m:
        return None
    raw = [v.strip(" .'\"") for v in re.split(r",| or ", m.group(1))]
    vals = [v for v in raw if v and len(v) < 40 and " " not in v.strip()]
    # Two values could be prose; three or more reads as a genuine enumeration.
    return vals if len(vals) >= 3 else None


def plan_model(ds: Dataset, catalog_tables: dict[str, Dataset]) -> ModelPlan:
    plan = ModelPlan(dataset=ds)

    if not ds.fields:
        plan.findings.append(
            Finding("warn", ds.table, "No schema in DataHub — ingest the schema before generating tests.")
        )
        return plan

    pk_seen = False
    for f in ds.fields:
        # 1. Not-null, straight from the catalog's nullability.
        if not f.nullable:
            plan.tests.append(
                Test(f.path, "not_null", f"DataHub records {ds.table}.{f.path} as NOT NULL")
            )

        # 2. Uniqueness, only for something that reads as the primary key.
        if _looks_like_pk(f, ds) and not pk_seen:
            pk_seen = True
            plan.tests.append(
                Test(f.path, "unique", f"{f.path} is the primary-key column for {ds.table}")
            )

        # 3. Referential integrity, grounded in catalog membership.
        target = _fk_target(f, catalog_tables, ds)
        if target is not None:
            target_pk = next(
                (t.path for t in target.fields if _looks_like_pk(t, target)), None
            )
            if target_pk:
                plan.tests.append(
                    Test(
                        f.path,
                        "relationships",
                        f"{f.path} references {target.table}.{target_pk}, "
                        f"which exists in the catalog",
                        {"to": f"ref('{target.table}')", "field": target_pk},
                    )
                )
            else:
                plan.findings.append(
                    Finding(
                        "info", ds.table,
                        f"{f.path} looks like a key into {target.table}, but that model has no "
                        f"identifiable primary key — skipped rather than guessed.",
                    )
                )

        # 4. Enumerations recovered from documentation.
        vals = _accepted_values(f)
        if vals:
            plan.tests.append(
                Test(
                    f.path, "accepted_values",
                    f"description of {f.path} enumerates {len(vals)} values",
                    {"values": vals},
                )
            )

    _pii_findings(ds, plan)
    return plan


def _pii_findings(ds: Dataset, plan: ModelPlan) -> None:
    pii = [f for f in ds.fields if f.is_pii]
    if not pii:
        return

    # Numeric surrogate keys tagged PII are almost always over-tagging, and
    # over-tagging is as damaging as under-tagging: it trains people to ignore
    # the label.
    suspect = [f for f in pii if f.is_numeric and f.path.lower().endswith("_id")]
    if suspect:
        plan.findings.append(
            Finding(
                "warn", ds.table,
                "Numeric surrogate keys tagged PII: "
                + ", ".join(f.path for f in suspect)
                + ". These are internal identifiers carrying no personal data — "
                  "review the tagging, since over-broad PII marking devalues the label.",
            )
        )

    genuine = [f for f in pii if f not in suspect]
    if genuine:
        plan.findings.append(
            Finding(
                "info", ds.table,
                f"{len(genuine)} PII column(s) present ("
                + ", ".join(f.path for f in genuine[:4])
                + ("…" if len(genuine) > 4 else "")
                + "). Emitted with meta.contains_pii so downstream tooling can enforce masking.",
            )
        )


def cross_model_findings(plans: Sequence[ModelPlan]) -> list[Finding]:
    """Checks that only make sense with the whole catalog in view.

    A per-model linter cannot see these: they require comparing a column against
    every other occurrence of the same column name across the warehouse, which is
    exactly the view a metadata catalog provides and a dbt project does not.
    """
    findings: list[Finding] = []

    # 1. The same column documented with different enumerations in different
    #    models. Either the models genuinely disagree — a data bug — or the
    #    documentation has drifted. Both are worth a human's attention.
    enums: dict[str, dict[str, tuple[str, ...]]] = {}
    for p in plans:
        for t in p.tests:
            if t.name == "accepted_values" and t.config:
                enums.setdefault(t.column, {})[p.dataset.table] = tuple(t.config["values"])

    for column, by_model in enums.items():
        distinct = {vals for vals in by_model.values()}
        if len(distinct) > 1:
            detail = "; ".join(
                f"`{model}` = {', '.join(vals)}" for model, vals in sorted(by_model.items())
            )
            findings.append(
                Finding(
                    "warn", "cross-model",
                    f"Column `{column}` is documented with conflicting value sets across "
                    f"{len(by_model)} models — {detail}. Either these models disagree about "
                    f"the same concept, or the documentation has drifted. The generated "
                    f"accepted_values tests will enforce whichever set each model declares, "
                    f"so a mismatch will surface as a test failure rather than silent skew.",
                )
            )

    # 2. A column that is NOT NULL in one model but nullable in another is a
    #    common source of broken joins downstream.
    nullability: dict[str, dict[str, bool]] = {}
    for p in plans:
        for f in p.dataset.fields:
            nullability.setdefault(f.path, {})[p.dataset.table] = f.nullable
    for column, by_model in nullability.items():
        if len(by_model) > 1 and len(set(by_model.values())) > 1:
            nn = sorted(m for m, nullable in by_model.items() if not nullable)
            nul = sorted(m for m, nullable in by_model.items() if nullable)
            findings.append(
                Finding(
                    "info", "cross-model",
                    f"Column `{column}` is NOT NULL in {', '.join(f'`{m}`' for m in nn)} "
                    f"but nullable in {', '.join(f'`{m}`' for m in nul)}. Joins across these "
                    f"models can drop rows unexpectedly.",
                )
            )

    return findings


def plan_all(datasets: Sequence[Dataset]) -> list[ModelPlan]:
    tables = {d.table.lower(): d for d in datasets}
    return [plan_model(d, tables) for d in datasets]
