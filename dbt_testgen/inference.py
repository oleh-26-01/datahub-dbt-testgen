"""Turn DataHub metadata into dbt tests — and into a list of tests refused.

The refusals are the point. Any model can produce a `schema.yml`; the failure
mode of a generated test suite is not too few tests, it is tests nobody can
justify, which fail on correct data and get deleted along with the ones that
mattered.

So every rule here has to name the evidence that justified it, and the evidence
has to be something a human wrote down. Two consequences:

* `not_null` is not emitted from the catalog's nullability flag. That flag is a
  per-platform constant in DataHub's own sample — see `census_finding` — so a
  test derived from it carries no information about the data.
* Where the schema and the documentation disagree, the documentation wins and
  the contradiction is reported.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Iterable, Mapping, Sequence

from .catalog import Dataset, Field
from .documents import ColumnDoc, DocumentFacts

# Words that look like identifiers but are not foreign keys.
_NOT_FK = {"external_id", "uuid", "guid", "correlation_id", "request_id", "trace_id"}

# "(e.g., Platinum, Gold, Silver)" in a column description. A naive generator
# reads this as an enumeration; it is an illustration, and the word "e.g." says
# so. Matched here only so the refusal can be counted and explained.
_ILLUSTRATIVE_LIST = re.compile(
    r"(?i)\b(?:e\.g\.?|for example|such as)[:,]?\s*\(?([^)."
    r"]+)\)?"
)


@dataclass
class Test:
    """A single dbt test plus the metadata that justified it."""

    column: str
    name: str                      # not_null | unique | relationships | accepted_values
    because: str                   # human-readable evidence
    source: str = "document"       # document | document+lineage | schema
    config: dict | None = None     # extra YAML for parametrised tests

    def to_yaml_obj(self, *, nest_arguments: bool = True):
        """Render as dbt YAML.

        dbt 1.12 deprecated passing generic-test parameters as bare keys; they
        now belong under `arguments:`. Older projects still expect the flat
        form, so both are supported.
        """
        if self.config is None:
            return self.name
        if nest_arguments:
            return {self.name: {"arguments": self.config}}
        return {self.name: self.config}


@dataclass
class Refusal:
    """A test that was not written, and the evidence that stopped it."""

    kind: str        # see REFUSAL_KINDS
    dataset: str
    column: str
    would_have: str  # the test a schema-driven generator would have emitted
    because: str     # why this one didn't


REFUSAL_KINDS = {
    "nullability-flag": "not_null declined — the flag behind it is a per-platform constant",
    "contradicted": "not_null retracted — documentation says the column is nullable",
    "non-table-fk": "relationships declined — the documented target is not a table",
    "unresolved-fk": "relationships declined — nothing in the catalog declares a target",
    "illustrative-enum": "accepted_values declined — the list is prefixed 'e.g.'",
    "composite-pk": "unique declined — the documented key is composite",
    "undocumented-pk": "unique declined — no document declares a primary key",
    "conflicting-upstreams": "relationships declined — upstream models document the column "
                             "as referencing different things",
}


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
    refusals: list[Refusal] = dc_field(default_factory=list)

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


def _plural_forms(stem: str) -> list[str]:
    """Candidate table names for a foreign-key stem.

    Only used to work out what a *name-matching* generator would have guessed,
    so its refusals can be counted honestly. No test is emitted from it.
    """
    forms = [stem, stem + "s"]
    if stem.endswith("y") and len(stem) > 1 and stem[-2] not in "aeiou":
        forms.append(stem[:-1] + "ies")
    if stem.endswith(("s", "x", "z", "ch", "sh")):
        forms.append(stem + "es")
    forms.append(_singular(stem))
    return forms


def _name_matched_fk(f: Field, tables: Mapping[str, Dataset], ds: Dataset) -> Dataset | None:
    name = f.path.lower()
    if not name.endswith("_id") or name in _NOT_FK:
        return None
    stem = name[:-3]
    for candidate in _plural_forms(stem):
        target = tables.get(candidate)
        if target is not None and target.urn != ds.urn:
            return target
    if "_" in stem:
        tail = stem.rsplit("_", 1)[-1]
        for candidate in _plural_forms(tail):
            target = tables.get(candidate)
            if target is not None and target.urn != ds.urn:
                return target
    return None


def _description_list(f: Field) -> list[str] | None:
    """The enumeration a naive generator would have read out of a description."""
    if not f.description:
        return None
    m = _ILLUSTRATIVE_LIST.search(f.description)
    if not m:
        return None
    raw = [v.strip(" .'\"") for v in re.split(r",| or ", m.group(1))]
    vals = [v for v in raw if v and len(v) < 40 and " " not in v.strip()]
    return vals if len(vals) >= 2 else None


def _annotating_authors(docs: DocumentFacts) -> set[str]:
    """Documents whose author demonstrably tracks nullability.

    If a document explicitly notes that some of its columns are sometimes
    empty, then the columns it does *not* so annotate carry a weak but real
    signal. If it never mentions NULL at all, silence means nothing and no
    `not_null` is inferred from it.
    """
    return {
        d.doc_urn for d in docs.columns.values() if d.declares_nullable
    }


def _inherit_docs(
    ds: Dataset, docs: DocumentFacts, by_urn: Mapping[str, Dataset]
) -> tuple[dict[str, tuple[ColumnDoc, str]], list[tuple[str, list[str]]]]:
    """Carry column documentation along DataHub's recorded lineage edges.

    `order_details` is a view over eleven models; DataHub records those edges,
    so a column arriving from `order_items` keeps whatever a human wrote about
    it there. This is the one place lineage does real work, and it only fires
    for columns with no documentation of their own.

    Two rules keep it honest. A view inherits what a column *means* — what it
    references, whether it can be empty — never what role it plays in its
    source table's key, since `inventories.product_id` being half a composite
    key says nothing about the same column in a flattened view. And when two
    upstreams describe the column as referencing different things, nothing is
    inherited at all: the conflict is reported instead of silently resolved.
    """
    inherited: dict[str, tuple[ColumnDoc, str]] = {}
    conflicts: list[tuple[str, list[str]]] = []

    upstream_models = [
        up for up in (by_urn.get(u) for u in ds.upstreams)
        if up is not None and up.platform == "dbt" and up.urn != ds.urn
    ]

    for f in ds.fields:
        col = f.path.lower()
        if docs.get(ds.table, col):
            continue
        candidates = [
            (up.table, doc)
            for up in upstream_models
            if (doc := docs.get(up.table, col)) is not None
        ]
        if not candidates:
            continue

        targets = {d.fk_target for _, d in candidates if d.fk_target}
        if len(targets) > 1:
            conflicts.append((col, sorted(targets)))
            continue

        # Most conservative first: a nullability caveat anywhere upstream applies
        # here too. Then plain references ahead of key-role annotations. Then
        # authors who annotate nullability at all, since their silence about
        # this column is itself evidence — otherwise which upstream happens to
        # come first would decide whether a `not_null` is emitted.
        annotating_docs = _annotating_authors(docs)
        candidates.sort(key=lambda td: (
            td[1].declares_nullable is None,
            td[1].composite_pk_part is not None or td[1].declares_pk,
            td[1].doc_urn not in annotating_docs,
            td[0],
        ))
        table, doc = candidates[0]
        inherited[col] = (doc, table)

    return inherited, conflicts


def plan_model(
    ds: Dataset,
    catalog_tables: Mapping[str, Dataset],
    docs: DocumentFacts,
    by_urn: Mapping[str, Dataset] | None = None,
) -> ModelPlan:
    plan = ModelPlan(dataset=ds)

    if not ds.fields:
        plan.findings.append(
            Finding("warn", ds.table,
                    "No schema in DataHub — ingest the schema before generating tests.")
        )
        return plan

    inherited, conflicts = _inherit_docs(ds, docs, by_urn or {})
    for col, targets in conflicts:
        plan.refusals.append(Refusal(
            "conflicting-upstreams", ds.table, col, "relationships",
            f"{ds.table} is built from several models that document `{col}` as referencing "
            f"different things ({', '.join(targets)}). Picking one would be a guess.",
        ))
    annotating = _annotating_authors(docs)
    composite = docs.composite_pk(ds.table)
    declared_pk = docs.primary_key(ds.table)

    for f in ds.fields:
        col = f.path.lower()
        own = docs.get(ds.table, col)
        doc, via = (own, "") if own else inherited.get(col, (None, ""))
        source = "document" if own else ("document+lineage" if doc else "schema")
        origin = f" (documented on `{via}`, inherited across a lineage edge DataHub records)" if via else ""

        _plan_not_null(plan, ds, f, doc, source, origin, annotating, composite, declared_pk)
        _plan_unique(plan, ds, f, declared_pk, composite)
        _plan_relationships(plan, ds, f, doc, source, origin, catalog_tables)
        _plan_accepted_values(plan, ds, f, doc, via, source, origin, docs)

    if composite:
        plan.findings.append(
            Finding("info", ds.table,
                    f"Documented composite primary key ({', '.join(composite)}). dbt's built-in "
                    f"`unique` test takes a single column, so no uniqueness test is emitted — "
                    f"enforcing this needs `dbt_utils.unique_combination_of_columns`.")
        )

    _pii_findings(ds, plan, docs)
    return plan


def _plan_not_null(plan, ds, f, doc, source, origin, annotating, composite, declared_pk) -> None:
    """`not_null`, emitted only where a human's writing supports it."""
    col = f.path.lower()
    is_key = (declared_pk is not None and declared_pk.column == col) or col in composite

    if doc is not None and doc.declares_nullable:
        if not f.nullable:
            plan.refusals.append(Refusal(
                "contradicted", ds.table, f.path, "not_null",
                f"DataHub's schema marks {ds.table}.{f.path} NOT NULL, but the catalog's own "
                f"documentation says otherwise: {doc.cite()}{origin}. The documentation wins.",
            ))
        return

    if is_key:
        why = (f"{f.path} is documented as "
               + ("part of the composite primary key" if col in composite else "the primary key")
               + f" of {ds.table}; a key column cannot be null")
        plan.tests.append(Test(f.path, "not_null", why, source))
        return

    if doc is not None and doc.fk_target and doc.doc_urn in annotating:
        plan.tests.append(Test(
            f.path, "not_null",
            f"{f.path} is documented as a foreign key with no nullability caveat, in a document "
            f"that annotates other columns as nullable — the omission is deliberate{origin}",
            source,
        ))
        return

    if not f.nullable:
        plan.refusals.append(Refusal(
            "nullability-flag", ds.table, f.path, "not_null",
            f"DataHub marks {ds.table}.{f.path} NOT NULL, but every dbt column in this catalog "
            f"carries that flag — it identifies the connector, not the column.",
        ))


def _plan_unique(plan, ds, f, declared_pk, composite) -> None:
    col = f.path.lower()
    if declared_pk is not None and declared_pk.column == col:
        plan.tests.append(Test(
            f.path, "unique",
            f"{f.path} is declared the primary key of {ds.table}: {declared_pk.cite()}",
        ))
    elif col in composite:
        plan.refusals.append(Refusal(
            "composite-pk", ds.table, f.path, "unique",
            f"{f.path} is only part {composite.index(col) + 1} of a documented composite key "
            f"({', '.join(composite)}) — unique on it alone would fail on correct data.",
        ))


def _plan_relationships(plan, ds, f, doc, source, origin, catalog_tables) -> None:
    col = f.path.lower()
    declared = doc.fk_target if doc is not None else None

    if declared:
        target = catalog_tables.get(declared) or catalog_tables.get(_singular(declared))
        if target is None:
            plan.refusals.append(Refusal(
                "non-table-fk", ds.table, f.path, "relationships",
                f"documentation declares {f.path} points at `{declared}`, which is not a model in "
                f"this catalog — {doc.cite()}. A name-matching generator would have pointed this "
                f"at whatever table the column name resembles.",
            ))
            return
        if col not in target.column_names:
            plan.refusals.append(Refusal(
                "unresolved-fk", ds.table, f.path, "relationships",
                f"documentation points {f.path} at `{target.table}`, but that model has no "
                f"`{f.path}` column to join on.",
            ))
            return
        plan.tests.append(Test(
            f.path, "relationships",
            f"documentation declares {f.path} references {target.table}, and "
            f"{target.table}.{f.path} exists in the catalog: {doc.cite()}{origin}",
            source, {"to": f"ref('{target.table}')", "field": f.path},
        ))
        return

    guess = _name_matched_fk(f, catalog_tables, ds)
    if guess is not None:
        plan.refusals.append(Refusal(
            "unresolved-fk", ds.table, f.path, "relationships",
            f"the name {f.path} resembles a key into `{guess.table}`, but nothing in the catalog "
            f"declares that relationship. Resemblance is not evidence.",
        ))


def _plan_accepted_values(plan, ds, f, doc, via, source, origin, docs) -> None:
    col = f.path.lower()
    declared = docs.declared_values(ds.table, col)
    if declared is None and via:
        declared = docs.declared_values(via, col)

    if declared:
        values, title = declared
        plan.tests.append(Test(
            f.path, "accepted_values",
            f"{title} enumerates {len(values)} legal values for {f.path}{origin}",
            source, {"values": values},
        ))
        return

    naive = _description_list(f)
    if naive:
        plan.refusals.append(Refusal(
            "illustrative-enum", ds.table, f.path, "accepted_values",
            f"the column description offers \"{', '.join(naive)}\" — but prefixed with \"e.g.\", "
            f"which makes it an illustration, not a closed set. Enforcing it would reject valid "
            f"data.",
        ))


def _pii_findings(ds: Dataset, plan: ModelPlan, docs: DocumentFacts) -> None:
    tagged = {f.path.lower() for f in ds.fields if f.is_pii}
    documented = {
        c for (t, c), d in docs.columns.items() if t == ds.table.lower() and d.declares_pii
    }
    if not tagged and not documented:
        return

    over = sorted(tagged - documented)
    if over and documented:
        plan.findings.append(
            Finding(
                "warn", ds.table,
                f"Tagged PII in the schema but not marked PII in the document that lists this "
                f"table's personal data: {', '.join(over)}. The document marks "
                f"{len(documented)} column(s) — {', '.join(sorted(documented))}. Over-broad "
                f"tagging devalues the label, which is how real PII ends up ignored.",
            )
        )
    under = sorted(documented - tagged)
    if under:
        plan.findings.append(
            Finding(
                "warn", ds.table,
                f"Documented as personal data but carrying no PII glossary term in the schema: "
                f"{', '.join(under)}. Masking and access policies keyed on the term will miss "
                f"these columns.",
            )
        )


def census_finding(census: Mapping[str, Mapping[str, int]]) -> Finding | None:
    """State plainly whether the nullability flag varies at all.

    This is the measurement the whole `not_null` policy rests on, so it is
    reported as a number rather than asserted.
    """
    if not census:
        return None
    parts, constant = [], []
    for platform, counts in sorted(census.items()):
        nullable = counts.get("nullable", 0)
        not_null = counts.get("not_null", 0)
        total = nullable + not_null
        if not total:
            continue
        if nullable == 0:
            parts.append(f"{platform} {not_null}/{total} NOT NULL")
            constant.append(platform)
        elif not_null == 0:
            parts.append(f"{platform} {nullable}/{total} nullable")
            constant.append(platform)
        else:
            parts.append(f"{platform} {not_null}/{total} NOT NULL, {nullable} nullable")
    if not parts:
        return None

    if len(constant) == len(census):
        message = (
            "Nullability in this catalog carries no information: every platform reports one "
            "constant value for every column it holds — " + "; ".join(parts) + ". The same "
            "physical column is NOT NULL or nullable depending only on which connector you ask, "
            "so `not_null` generated from the flag would assert nothing. This tool emits it from "
            "documentation instead."
        )
        return Finding("warn", "catalog-wide", message)
    return Finding(
        "info", "catalog-wide",
        "Nullability flags by platform: " + "; ".join(parts) + ".",
    )


def cross_model_findings(
    plans: Sequence[ModelPlan], docs: DocumentFacts | None = None
) -> list[Finding]:
    """Checks that only make sense with the whole catalog in view.

    A per-model linter cannot see these: they need every occurrence of a column
    name across the warehouse, plus the prose written about it, which is exactly
    the view a metadata catalog provides and a dbt project does not.
    """
    findings: list[Finding] = []
    docs = docs or DocumentFacts()

    # The same column described with different value sets in different models,
    # and — more usefully — described differently from how it is documented.
    described: dict[str, dict[str, list[str]]] = {}
    for p in plans:
        for f in p.dataset.fields:
            vals = _description_list(f)
            if vals:
                described.setdefault(f.path.lower(), {})[p.dataset.table] = vals

    for column, by_model in sorted(described.items()):
        authoritative: dict[str, tuple[list[str], str]] = {}
        for p in plans:
            hit = docs.declared_values(p.dataset.table, column)
            if hit:
                authoritative[p.dataset.table] = hit
        distinct = {tuple(v) for v in by_model.values()}
        doc_sets = {tuple(v) for v, _ in authoritative.values()}
        if len(distinct | doc_sets) < 2:
            continue

        detail = "; ".join(f"`{m}` description says {', '.join(v)}"
                           for m, v in sorted(by_model.items()))
        if authoritative:
            seen: list[tuple[list[str], str]] = []
            for vals, title in authoritative.values():
                if (vals, title) not in seen:
                    seen.append((vals, title))
            src = "; ".join(f"{title} says {', '.join(v)}" for v, title in sorted(seen,
                                                                                 key=lambda x: x[1]))
            spread = (f"described {len(distinct)} different ways across {len(by_model)} models"
                      if len(distinct) > 1 else
                      f"described the same way in {len(by_model)} models")
            findings.append(Finding(
                "warn", "cross-model",
                f"`{column}` is {spread}, and the description matches no documented value. "
                f"{detail}. Meanwhile {src}. Every description is prefixed \"e.g.\", so no "
                f"accepted_values test is generated from them; the documented set is used "
                f"instead, and the drift is reported here.",
            ))
        elif len(distinct) > 1:
            findings.append(Finding(
                "warn", "cross-model",
                f"`{column}` is described with conflicting value sets — {detail}. Nothing in the "
                f"catalog's documentation settles which is right, so no accepted_values test is "
                f"generated for this column at all.",
            ))

    return findings


def plan_all(
    datasets: Sequence[Dataset], docs: DocumentFacts | None = None
) -> list[ModelPlan]:
    docs = docs or DocumentFacts()
    tables = {d.table.lower(): d for d in datasets}
    by_urn = {d.urn: d for d in datasets}
    return [plan_model(d, tables, docs, by_urn) for d in datasets]


def refusal_summary(plans: Sequence[ModelPlan]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for p in plans:
        for r in p.refusals:
            counts[r.kind] = counts.get(r.kind, 0) + 1
    return counts
