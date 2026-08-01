# dbt-testgen

**Generates dbt tests from DataHub — and tells you which ones it refused to write.**

Built for *Build with DataHub: The Agent Hackathon* · Metadata-Aware Code Generation.

---

## The number that matters is the second one

```
75 tests emitted.  139 tests refused.
```

Every test generator reports the first number. This one reports the second,
because that is where the damage is. A generated test nobody can justify fails on
correct data, and the reflex is to delete it — along with the tests that mattered.
Six months later the suite is decoration.

So every emitted test here cites a sentence a human wrote, and every refused test
names the evidence that was missing.

## Why refuse anything? Because the obvious signal is noise

The usual way to generate `not_null` is to read the catalog's nullability flag.
Before trusting it, this tool counts it. On DataHub's own `showcase-ecommerce`
sample:

| Platform | NOT NULL | nullable | varies? |
| --- | --- | --- | --- |
| dbt | 157 | 0 | no — constant |
| s3 | 102 | 0 | no — constant |
| snowflake | 0 | 212 | no — constant |
| postgres | 0 | 102 | no — constant |

573 column records, zero variance anywhere. `customers.customer_id` is NOT NULL
according to dbt and S3, and nullable according to Snowflake and Postgres — the
same physical column. **The flag records which connector wrote it, not anything
about the data.** A `not_null` test generated from it asserts nothing.

That is the whole design. The only thing in this catalog that actually varies per
column is what a human wrote about it, so that is what the tests are built from.

## Where the evidence comes from

This DataHub deployment holds 18 documents. Ten of them describe columns, in
markdown tables nothing else reads:

```
| `promotion_id`       | FK → promotions. NULL means no promotion applied (~65% of orders). |
| `account_mgr_id`     | FK → corpuser. Assigned sales rep (B2B accounts only). NULL for B2C. |
| `product_id`         | FK → products. Composite PK part 1. |
| `payment_method_code`| `CreditCard`, `PurchaseOrder`, or `AccountBalance`. |
```

None of that is inferable from a column name or a type. It gives primary keys,
composite keys, foreign keys that point at things which *aren't tables*, closed
value sets, and — the useful one — which columns are legitimately empty.

## What it refuses, and why

| Count | Refusal |
| --- | --- |
| 119 | `not_null` — the flag behind it is a per-platform constant |
| 13 | `not_null` **retracted** — documentation says the column is nullable |
| 3 | `relationships` — nothing in the catalog declares a target |
| 2 | `relationships` — the documented target is not a table |
| 2 | `unique` — the documented key is composite |

The 13 retractions are the interesting ones. DataHub's schema marks
`orders.promotion_id` NOT NULL. DataHub's documentation says it is null on about
65% of orders. **This tool believes the human and drops the test**, then proves it
was right:

```bash
dbt-testgen validate --with-refused
cd validation && dbt build --profiles-dir .
```

```
Done. PASS=101 WARN=0 ERROR=13 SKIP=0 TOTAL=114
```

The 101 evidenced tests still pass. Exactly the 13 retracted ones fail, and
nothing else. That is the retraction demonstrated rather than asserted.

The two non-table foreign keys are the other favourite. `customers.account_mgr_id`
is documented `FK → corpuser` — a DataHub user, not a warehouse table. A
name-matching generator points it at whatever table the name resembles. This one
reads the sentence and declines.

## What it emits

| Test | Count | Evidence |
| --- | --- | --- |
| `not_null` | 25 | a documented key column, or a documented FK in a document that annotates nulls elsewhere |
| `relationships` | 22 | a document declares the target, **and** the catalog contains it with a joinable column |
| `accepted_values` | 20 | a document enumerates a closed set |
| `unique` | 8 | a document declares the column the primary key |

All 75 execute in dbt 1.12 against DuckDB: **`PASS=101 ERROR=0`**. Inject four
defects — duplicate key, null key, invalid status, dangling FK — and you get ten
failures, because the relationships cascade downstream. Logs in
[`examples/`](examples/).

## What it found that nobody asked for

Reading the whole catalog at once shows things a per-model linter structurally
cannot.

**Six columns are described in a way that matches no documented value.** Not just
model-vs-model drift — model-vs-*documentation* drift:

```
order_status     orders/order_details description:  1=Pending, 2=Processing, 3=Shipped
                 Orders Table document:             Pending, Open, Shipped, Complete,
                                                    Cancelled, On Hold
customer_class   customers description:             Platinum, Gold, Silver
                 order_details description:         Retail, Enterprise, Online
                 Customers Table document:          Premium, Standard
```

`order_status` is described as holding *integers* and documented as holding
*strings*, with three states versus six. A generator that trusted the description
would emit `accepted_values: [1, 2, 3]` — wrong type and wrong cardinality. Every
one of these descriptions is prefixed `e.g.`, which is the tell: it is an
illustration, not a contract. So no test is generated from any of them, the
documented set is used instead, and the drift is reported.

**PII tagging disagrees with the PII documentation.** The `customers` document
lists exactly which columns are personal data. The schema's glossary terms tag
eight more, including numeric surrogate keys. Over-tagging is not harmless
caution — it trains people to ignore the label.

## It writes back

```bash
dbt-testgen generate --write-back
```

Publishes each model's evidenced coverage to DataHub as a structured property,
so the catalog gains something it did not have: which models are actually tested,
and how well. Values range from 16.7% to 73.3% across the sample — the spread is
the point, since coverage computed from a constant flag would be a constant 100%.

The property definition is created on first run. That single call uses the Python
SDK rather than MCP, because the MCP server can set a structured property's
*value* but has no tool to declare the property itself; everything else — reads
and the value writes — goes through MCP.

## Quickstart

Requires a running DataHub (`datahub docker quickstart && datahub datapack load
showcase-ecommerce`) and Python 3.10+.

```bash
pip install -e ".[validate]"
dbt-testgen generate --out generated
```

Output lands in `generated/`:
- `schema.yml` — drop into your dbt project's `models/`
- `EVIDENCE.md` — every emitted test with its citation, every refused test with its reason

```bash
dbt-testgen validate                  # scaffold a runnable dbt+DuckDB project
dbt-testgen validate --with-refused   # add the retractions back; they should fail
dbt-testgen generate --write-back     # publish coverage to DataHub
dbt-testgen generate --flat-test-args # dbt < 1.12 parameter style
```

If the MCP server is not on your `PATH`, point at it explicitly:

```bash
export DBT_TESTGEN_MCP_COMMAND=/path/to/mcp-server-datahub
```

## How it works

```
DataHub ──MCP──▶ catalog.py     schemas, lineage, documents, nullability census
                      │
                      ▼
                 documents.py   parse the markdown humans wrote
                      │
                      ▼
                 inference.py   rules that emit with a citation, or refuse with a reason
                      │
                      ▼
                 emit.py        schema.yml + EVIDENCE.md
                      │
                      ├───────▶ validate.py  scaffold dbt+DuckDB, run for real
                      │
                      └──MCP──▶ DataHub      write coverage back
```

Reads use `search`, `list_schema_fields`, `get_lineage`, `search_documents` and
`grep_documents`; the write-back uses `add_structured_properties`.

### Where lineage does real work

`order_details` is a view over eleven models. DataHub records those edges, so a
column arriving from `order_items` keeps what a human wrote about it there — that
is how `order_details.return_date` gets its `not_null` retracted despite having no
documentation of its own.

Two rules keep it honest. A view inherits what a column *means* — what it
references, whether it can be empty — never what role it plays in its source
table's key, since `inventories.product_id` being half a composite key says
nothing about the same column in a flattened view. And when two upstreams
document the column as referencing different things, nothing is inherited: the
conflict is reported instead of silently resolved.

### The rules

| Rule | Emits when | Refuses when |
| --- | --- | --- |
| `not_null` | the column is a documented key, or a documented FK in a document whose author annotates nulls elsewhere | only the schema flag supports it, or documentation contradicts it |
| `unique` | a document declares the column the primary key | the key is composite, or undocumented |
| `relationships` | a document names the target **and** the catalog holds it with a joinable column | the target is not a table, or only the column name suggests one |
| `accepted_values` | a document enumerates a closed set | the list is prefixed `e.g.`, or is a range like `` `1`–`5` `` |

## Why this isn't something DataHub already ships

DataHub ships `datahub-quality`, which creates assertions **inside DataHub**, and
skills for connector planning and PR review. This runs the other way: it generates
dbt tests **in your repository**, as a file you commit and review, and the
coverage write-back closes the loop by telling the catalog what is now enforced.

## Feedback to DataHub

Found while building this, and submitted to the hackathon's feedback track:

- **`get_entities` returns no content for Document entities.** The
  `search_documents` docstring says "Use `get_entities()` with a document URN to
  retrieve full content when needed" — it comes back as a bare `{"urn": ...}`.
  `grep_documents` is the only way to read a document, which works but means you
  cannot read one you have not already guessed a pattern for.
- **No MCP tool creates a structured-property definition,** only sets values
  against one. An agent that wants to contribute a new property has to drop out of
  MCP and into the SDK.
- **`datahub datapack load` is broken on Windows** — `urlparse("C:\\x\\y.json")`
  returns scheme `"c"`, the drive letter. Already fixed upstream in
  [#18479](https://github.com/datahub-project/datahub/pull/18479) and
  [#18634](https://github.com/datahub-project/datahub/pull/18634); noting it
  because it is still broken in the released `1.6.0.17` wheel that the quickstart
  installs, so every Windows participant hits it on step one.
- **`datahub datapack --help` crashes when stdout is not a TTY**, because
  `DATAPACK_AGENT_CONTEXT.md` is missing from the published wheel
  ([#18497](https://github.com/datahub-project/datahub/issues/18497)). The guard is
  `if not sys.stdout.isatty()`, so it fires only for pipes, scripts and agents. The
  feature is called *agent* context and the agent path is the broken one.
- **A partial datapack load reports success.** Full notes in the feedback
  submission.

## Limitations

- **It is only as good as the documentation.** On a catalog with no written
  documentation this tool emits almost nothing — correctly, but unhelpfully. The
  refusal report then doubles as a list of what is worth writing down first.
- Composite keys are reported, not enforced: dbt's built-in `unique` takes one
  column, so that needs `dbt_utils.unique_combination_of_columns`.
- Document parsing expects markdown column tables. The shapes it accepts and the
  shapes it deliberately rejects are pinned down in
  [`tests/test_documents.py`](tests/test_documents.py).
- Inferring `not_null` from a documented FK with no null caveat is the one rule
  that reasons from absence. It is gated on the author having annotated nulls
  somewhere else in the same document, but it is still the weakest evidence here
  and is labelled as such in `EVIDENCE.md`.
- The validator synthesises data satisfying the catalog's contract, so it proves
  the tests execute and catch defects — it does not profile your real warehouse.

## Licence

Apache 2.0.
