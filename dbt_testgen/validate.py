"""Scaffold a runnable dbt project so the generated tests can be proven, not asserted.

A generated `schema.yml` is only worth trusting if it parses and executes. This
builds a throwaway dbt+DuckDB project whose seed data is synthesised from the
same DataHub schema the tests came from, so `dbt build` exercises every emitted
test against data that satisfies the catalog's own contract.
"""

from __future__ import annotations

import csv
import pathlib
import random
from typing import Sequence

from .catalog import Dataset, Field
from .inference import ModelPlan

PROJECT_YML = """name: 'testgen_validation'
version: '1.0.0'
profile: 'testgen_validation'
model-paths: ["models"]
seed-paths: ["seeds"]
target-path: "target"
clean-targets: ["target", "dbt_packages"]
"""

PROFILES_YML = """testgen_validation:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: 'validation.duckdb'
      threads: 4
"""


def _sample_value(f: Field, row: int, pk_pool: dict[str, list[int]], plan: ModelPlan) -> str:
    """Produce a value that honours whatever the catalog asserts about the column."""
    t = f.native_type.upper()

    # accepted_values tests constrain the domain — respect them.
    for test in plan.tests:
        if test.column == f.path and test.name == "accepted_values" and test.config:
            vals = test.config["values"]
            return vals[row % len(vals)]

    if f.is_numeric:
        if f.path.lower().endswith("_id") or f.path.lower() == "id":
            pool = pk_pool.get(f.path.lower())
            if pool:
                return str(pool[row % len(pool)])
            return str(row + 1)
        if t in {"FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"}:
            return f"{round(random.uniform(1, 1000), 2)}"
        return str(random.randint(1, 500))

    if "DATE" in t or "TIME" in t:
        return f"2026-0{(row % 9) + 1}-1{row % 9}"
    if "BOOL" in t:
        return "true" if row % 2 else "false"
    return f"{f.path}_{row + 1}"


def scaffold(
    root: pathlib.Path,
    plans: Sequence[ModelPlan],
    schema_yaml: str,
    *,
    rows: int = 12,
) -> pathlib.Path:
    """Write a complete dbt project under `root` and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "dbt_project.yml").write_text(PROJECT_YML, encoding="utf-8")
    (root / "profiles.yml").write_text(PROFILES_YML, encoding="utf-8")

    models_dir = root / "models"
    seeds_dir = root / "seeds"
    models_dir.mkdir(exist_ok=True)
    seeds_dir.mkdir(exist_ok=True)

    # Primary-key pools, so foreign keys point at rows that genuinely exist and
    # `relationships` tests are a real check rather than a tautology.
    pk_pool: dict[str, list[int]] = {}
    for plan in plans:
        for t in plan.tests:
            if t.name == "unique":
                pk_pool[t.column.lower()] = list(range(1, rows + 1))

    written = 0
    for plan in plans:
        ds: Dataset = plan.dataset
        if not plan.tests:
            continue
        cols = [f for f in ds.fields]
        if not cols:
            continue

        # Seeds are suffixed so they never collide with the model of the same
        # name — dbt refuses to build two resources with one database identity.
        seed_path = seeds_dir / f"{ds.table}_seed.csv"
        with seed_path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([f.path for f in cols])
            for r in range(rows):
                w.writerow([_sample_value(f, r, pk_pool, plan) for f in cols])

        (models_dir / f"{ds.table}.sql").write_text(
            f"-- generated for validation only\nselect * from {{{{ ref('{ds.table}_seed') }}}}\n",
            encoding="utf-8",
        )
        written += 1

    (models_dir / "schema.yml").write_text(schema_yaml, encoding="utf-8")
    return root
