"""Command line entry point."""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

from .catalog import connect
from .emit import to_evidence_report, to_schema_yaml
from .inference import cross_model_findings, plan_all

COVERAGE_PROPERTY = "dbt_test_coverage_pct"


async def _run(args) -> int:
    async with connect(args.gms, allow_writes=args.write_back) as cat:
        datasets = await cat.dbt_datasets(limit=args.limit)
        if not datasets:
            print("No dbt datasets found in DataHub.", file=sys.stderr)
            print("Load some metadata first, e.g. `datahub datapack load showcase-ecommerce`.",
                  file=sys.stderr)
            return 1

        print(f"Found {len(datasets)} dbt models; reading schemas and lineage…", file=sys.stderr)
        for i, ds in enumerate(datasets, 1):
            await cat.hydrate(ds)
            print(f"  [{i}/{len(datasets)}] {ds.table}: {len(ds.fields)} columns",
                  file=sys.stderr)

        plans = plan_all(datasets)
        cross = cross_model_findings(plans)

        if args.command == "validate":
            from .validate import scaffold

            root = pathlib.Path(args.project)
            scaffold(
                root,
                plans,
                to_schema_yaml(plans, test_key=args.test_key,
                               nest_arguments=not args.flat_test_args),
            )
            print(f"\nScaffolded a runnable dbt project at {root.resolve()}", file=sys.stderr)
            print(f"  models: {len(list((root / 'models').glob('*.sql')))}"
                  f"  seeds: {len(list((root / 'seeds').glob('*.csv')))}", file=sys.stderr)
            print(f"\nRun the generated tests for real:\n"
                  f"  cd {root} && dbt build --profiles-dir .", file=sys.stderr)
            return 0

        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        schema_path = out / "schema.yml"
        report_path = out / "EVIDENCE.md"
        schema_path.write_text(to_schema_yaml(plans, test_key=args.test_key, nest_arguments=not args.flat_test_args), encoding="utf-8")
        report_path.write_text(to_evidence_report(plans, cross), encoding="utf-8")

        total = sum(len(p.tests) for p in plans)
        warns = [f for p in plans for f in p.findings if f.severity == "warn"]
        print(f"\nWrote {total} tests to {schema_path}", file=sys.stderr)
        print(f"Wrote evidence to {report_path}", file=sys.stderr)
        for f in warns:
            print(f"  warn  {f.dataset}: {f.message}", file=sys.stderr)
        for f in cross:
            if f.severity == "warn":
                print(f"  warn  catalog-wide: {f.message[:160]}…", file=sys.stderr)

        if args.write_back:
            print("\nWriting coverage back to DataHub…", file=sys.stderr)
            ok = 0
            for p in plans:
                if p.tests and await cat.write_coverage(
                    p.dataset.urn, COVERAGE_PROPERTY, str(p.coverage)
                ):
                    ok += 1
            print(f"  updated {ok}/{len(plans)} entities with {COVERAGE_PROPERTY}",
                  file=sys.stderr)

        return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dbt-testgen",
        description="Generate dbt tests grounded in DataHub metadata.",
    )
    ap.add_argument("command", choices=["generate", "validate"],
                    help="`generate` writes schema.yml + EVIDENCE.md; "
                         "`validate` scaffolds a runnable dbt+DuckDB project to prove them")
    ap.add_argument("--gms", default=None, help="DataHub GMS URL (default $DATAHUB_GMS_URL)")
    ap.add_argument("--out", default="generated", help="output directory")
    ap.add_argument("--limit", type=int, default=50, help="max models to process")
    ap.add_argument("--test-key", default="data_tests", choices=["data_tests", "tests"],
                    help="`data_tests` for dbt>=1.8, `tests` for older projects")
    ap.add_argument("--flat-test-args", action="store_true",
                    help="emit pre-1.12 flat test parameters instead of nested `arguments`")
    ap.add_argument("--project", default="validation",
                    help="where `validate` scaffolds the throwaway dbt project")
    ap.add_argument("--write-back", action="store_true",
                    help="publish test coverage back to DataHub as a structured property")
    args = ap.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
