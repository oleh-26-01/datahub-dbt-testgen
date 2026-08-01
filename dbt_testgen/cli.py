"""Command line entry point."""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

from .catalog import connect, ensure_property_definition
from .emit import to_evidence_report, to_schema_yaml
from .inference import census_finding, cross_model_findings, plan_all, refusal_summary

COVERAGE_PROPERTY = "dbt_testgen.evidenced_coverage_pct"
COVERAGE_PROPERTY_URN = f"urn:li:structuredProperty:{COVERAGE_PROPERTY}"


async def _run(args) -> int:
    gms = args.gms or "http://localhost:8080"
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

        print("Reading the deployment's documents…", file=sys.stderr)
        docs = await cat.documents(datasets)
        print(f"  {docs.documents_with_columns}/{docs.documents_read} documents describe "
              f"columns; {len(docs.columns)} columns documented, "
              f"{len(docs.value_tables)} enumerations declared", file=sys.stderr)

        print("Measuring nullability across platforms…", file=sys.stderr)
        census = await cat.nullability_census()

        plans = plan_all(datasets, docs)
        cross = cross_model_findings(plans, docs)
        census_note = census_finding(census)
        if census_note:
            cross = [census_note] + list(cross)

        if args.command == "validate":
            from .validate import scaffold

            root = pathlib.Path(args.project)
            scaffold(
                root,
                plans,
                to_schema_yaml(plans, test_key=args.test_key,
                               nest_arguments=not args.flat_test_args,
                               include_refused=args.with_refused),
            )
            if args.with_refused:
                retracted = sum(
                    1 for p in plans for r in p.refusals if r.kind == "contradicted"
                )
                print(f"\nPROOF MODE: {retracted} retracted not_null tests added back.",
                      file=sys.stderr)
                print("`dbt build` should now fail exactly those, and nothing else.",
                      file=sys.stderr)
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
        schema_path.write_text(
            to_schema_yaml(plans, test_key=args.test_key,
                           nest_arguments=not args.flat_test_args),
            encoding="utf-8",
        )
        report_path.write_text(
            to_evidence_report(plans, cross, census, docs.documents_read), encoding="utf-8"
        )

        total = sum(len(p.tests) for p in plans)
        refusals = refusal_summary(plans)
        print(f"\nWrote {total} tests to {schema_path}", file=sys.stderr)
        print(f"Refused {sum(refusals.values())} tests — reasons in {report_path}",
              file=sys.stderr)
        for kind, count in sorted(refusals.items(), key=lambda kv: -kv[1]):
            print(f"    {count:4}  {kind}", file=sys.stderr)
        for f in cross:
            if f.severity == "warn":
                print(f"  warn  {f.dataset}: {f.message[:200]}…", file=sys.stderr)
        for p in plans:
            for f in p.findings:
                if f.severity == "warn":
                    print(f"  warn  {f.dataset}: {f.message[:200]}…", file=sys.stderr)

        if args.write_back:
            print(f"\nPublishing coverage to DataHub as {COVERAGE_PROPERTY}…", file=sys.stderr)
            try:
                ensure_property_definition(
                    gms, COVERAGE_PROPERTY, "Evidenced test coverage %",
                    "Percentage of a model's columns carrying at least one dbt test that "
                    "cites documented evidence. Written by dbt-testgen.",
                )
            except Exception as exc:            # noqa: BLE001 - surfaced, not swallowed
                print(f"  could not create the property definition: {exc}", file=sys.stderr)
                return 1

            ok, failed = 0, []
            for p in plans:
                if not p.tests:
                    continue
                wrote, err = await cat.write_coverage(
                    p.dataset.urn, COVERAGE_PROPERTY_URN, str(p.coverage)
                )
                if wrote:
                    ok += 1
                else:
                    failed.append((p.dataset.table, err))
            print(f"  updated {ok} entities", file=sys.stderr)
            for table, err in failed:
                print(f"  FAILED {table}: {err}", file=sys.stderr)
            if failed:
                return 1

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
                    help="publish evidenced test coverage back to DataHub")
    ap.add_argument("--with-refused", action="store_true",
                    help="add the retracted not_null tests back, to prove they fail")
    args = ap.parse_args(argv)
    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
