# dbt-testgen

**Generate dbt tests that are grounded in DataHub metadata — and prove they run.**

Built for *Build with DataHub: The Agent Hackathon* · Challenge 2, Metadata-Aware Code Generation.

---

## The problem

Ask an LLM to write dbt tests for your warehouse and it will produce something
that looks right and is quietly wrong. It writes `relationships` tests pointing at
tables that do not exist. It marks columns `not_null` that are nullable in
production. It invents `accepted_values` from the column name. The output reads
plausibly, fails on the first run, and costs an afternoon to unpick.

The model is not stupid — it is guessing, because nobody gave it the schema.

Your catalog already has the answer. DataHub knows every column's real type and
nullability, which tables genuinely feed which, who owns what, and which fields
carry personal data. `dbt-testgen` reads that and writes the tests from it.

**Every emitted test cites the metadata that justified it. Where the catalog is
ambiguous, no test is emitted and the ambiguity is reported instead.**

## What it produces

From the 13 dbt models in DataHub's `showcase-ecommerce` sample:

| Test | Count | Derived from |
| --- | --- | --- |
| `not_null` | 157 | column nullability recorded in DataHub |
| `relationships` | 22 | foreign keys resolved against **tables the catalog actually contains** |
| `unique` | 8 | primary keys identified from naming + non-nullability |
| `accepted_values` | 8 | enumerations recovered from human-written column descriptions |

All 195 execute in dbt 1.12: **`PASS=221 WARN=0 ERROR=0`**.
See [`examples/`](examples/) for the generated files and the full run logs.

## It writes back to the graph

Reading a catalog is table stakes. After generating, `--write-back` publishes each
model's test coverage to DataHub as a structured property (`dbt_test_coverage_pct`),
so the catalog gains something it did not have before: which models are actually
tested. Run it on a schedule and coverage becomes a governable, searchable property
of the estate rather than tribal knowledge.

## Two things it found that nobody asked for

Because it reads the **whole catalog at once**, it sees things a per-model linter
structurally cannot.

**1. Contradictory enumerations across models.** Four columns are documented with
conflicting value sets:

```
customer_class   customers     = Platinum, Gold, Silver
                 order_details = Retail, Enterprise, Online
delivery_type    orders        = Standard, Express, Overnight
                 order_details = Standard, Curbside, Overnight
```

Either these models disagree about the same business concept, or the documentation
has drifted. Both are bugs, and both were invisible until something compared every
model against every other.

**2. Over-broad PII tagging.** Five models tag numeric surrogate keys
(`customer_id`, `region_id`, `address_id`) as PII. Those are internal identifiers
carrying no personal data. Over-tagging is not a harmless excess of caution — it
trains people to ignore the label, which is how genuine PII leaks.

## Quickstart

Requires a running DataHub (`datahub docker quickstart`) and Python 3.10+.

```bash
pip install -e .
dbt-testgen generate --out generated
```

Output lands in `generated/`:
- `schema.yml` — drop into your dbt project's `models/`
- `EVIDENCE.md` — every test, with the metadata that justified it

Useful flags:

```bash
dbt-testgen generate --write-back        # publish coverage back to DataHub
dbt-testgen generate --flat-test-args    # dbt < 1.12 parameter style
dbt-testgen generate --limit 10          # cap models processed
```

### Prove it rather than trust it

The repo ships a validator that scaffolds a throwaway dbt + DuckDB project whose
seed data is synthesised from the *same* DataHub schema, then runs every generated
test against it:

```bash
dbt-testgen validate
cd validation && dbt build --profiles-dir .
```

`PASS=221 WARN=0 ERROR=0`.

To confirm the tests are not vacuous, corrupt the seeds — duplicate a primary key,
blank a `NOT NULL` column, insert an invalid enum value, point a foreign key at a
row that does not exist:

```
FAIL unique_customers_customer_id
FAIL not_null_customers_cust_email
FAIL accepted_values_customers_customer_class
FAIL relationships_addresses_country_id__country_id__ref_countries_
FAIL relationships_orders_customer_id__customer_id__ref_customers_
… 8 failures from 4 injected defects
```

Four defects produce eight failures, because the lineage-derived `relationships`
tests correctly propagate a broken key into every downstream model.

## How it works

```
DataHub  ──MCP──▶  catalog.py    read schemas, lineage, glossary terms
                        │
                        ▼
                   inference.py   apply rules, each carrying its evidence
                        │
                        ▼
                   emit.py        schema.yml + EVIDENCE.md
                        │
                        ├──────▶  validate.py   scaffold dbt+DuckDB, run for real
                        │
                        └──MCP──▶ DataHub       write coverage back
```

All catalog access goes through the **DataHub MCP Server** — `search`,
`list_schema_fields`, `get_lineage` for reads, `add_structured_properties` for the
write-back. There is no direct GraphQL client, deliberately: the MCP server is the
interface an agent would use, so this stays honest about being agent-shaped.

### The inference rules

| Rule | Fires when | Refuses when |
| --- | --- | --- |
| `not_null` | DataHub records the column as NOT NULL | — |
| `unique` | column is `<table_singular>_id` or `id`, and non-nullable | a PK was already found |
| `relationships` | `<x>_id` resolves to a table **present in the catalog** with an identifiable PK | the target is absent, or has no PK — reported as a finding instead |
| `accepted_values` | description enumerates ≥3 single-token values | fewer than 3, or the column is numeric |

The `relationships` rule is the one that matters. It tries the singular, plural and
`y→ies` forms of the stem, then falls back to the trailing noun for qualified keys
like `billing_address_id` → `addresses`. If none of those resolve to a real table,
**it emits nothing** and records why. That refusal is the feature.

## Why this isn't something DataHub already ships

DataHub ships `datahub-quality`, which creates **assertions inside DataHub**, and
skills for connector planning and PR review. This runs in the opposite direction:
it generates **dbt tests in your repository**, as a file you commit and review.

The two are complementary, and the pairing is the point — DataHub knows what
*should* be true, dbt is where you enforce it in CI, and the coverage write-back
closes the loop by telling the catalog what is now actually enforced.

## Upstream contributions

Two bugs found while building this, both reported with fixes:

1. **`datahub datapack load` is broken on Windows.** `urlparse("C:\\path\\file.json")`
   returns scheme `"c"` — the drive letter — so the filesystem registry lookup fails
   with `KeyError: 'Did not find a registered class for c'`. Every Windows user hits
   this on the first documented onboarding step. Three-line fix in
   `datahub/ingestion/fs/fs_base.py`.

2. **`datahub datapack --help` crashes when stdout is not a TTY**, because
   `DATAPACK_AGENT_CONTEXT.md` is missing from the published wheel. The guard is
   `if not sys.stdout.isatty()` — so it fires only for pipes, scripts and agents.
   The feature is called *agent* context and the agent path is the broken one.

## Limitations

- Primary-key detection is naming-convention based (`<table>_id`, `id`). It will
  miss composite keys and unconventional schemes; both are reported rather than
  guessed at.
- `accepted_values` depends on descriptions being written in a recognisable
  `e.g. A, B, C` form. Undocumented enums are not recovered.
- Column-level lineage is fetched but not yet used; using it to propagate
  `not_null` along lineage edges is the obvious next step.
- The validator synthesises data that satisfies the catalog's contract, so it
  proves the tests *execute and catch defects* — it does not profile your real
  warehouse.

## Licence

Apache 2.0.
