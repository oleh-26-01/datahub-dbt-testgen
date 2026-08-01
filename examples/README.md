# Example output

Real output from a real run against DataHub's `showcase-ecommerce` sample data —
13 dbt models, 157 columns. Nothing here is illustrative or hand-written.

| File | What it is |
| --- | --- |
| [`schema.yml`](schema.yml) | The generated dbt test file — drop straight into `models/` |
| [`EVIDENCE.md`](EVIDENCE.md) | Every test with the DataHub metadata that justified it, plus catalog-wide findings |
| [`dbt-build-pass.log`](dbt-build-pass.log) | `dbt build` on data satisfying the catalog's contract |
| [`dbt-build-fail.log`](dbt-build-fail.log) | The same tests against deliberately corrupted data |

## What the logs demonstrate

**`dbt-build-pass.log`** — all 195 generated tests execute against dbt 1.12 + DuckDB:

```
Done. PASS=221 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=221
```

**`dbt-build-fail.log`** — the important one. Generated tests are worthless if they
pass on anything. Four defects were injected into the seed data:

1. a duplicate value in `customers.customer_id` (the primary key)
2. an empty string in `customers.cust_email` (recorded NOT NULL in DataHub)
3. `NotAValidClass` in `customers.customer_class` (outside the documented enum)
4. `addresses.country_id = 999999`, pointing at a row that does not exist

Eight tests failed:

```
FAIL unique_customers_customer_id
FAIL not_null_customers_cust_email
FAIL accepted_values_customers_customer_class__Platinum__Gold__Silver
FAIL relationships_addresses_country_id__country_id__ref_countries_
FAIL relationships_addresses_customer_id__customer_id__ref_customers_
FAIL relationships_orders_customer_id__customer_id__ref_customers_
FAIL relationships_order_details_customer_id__customer_id__ref_customers_
FAIL relationships_order_history_customer_id__customer_id__ref_customers_

Done. PASS=213 WARN=0 ERROR=8 SKIP=0 NO-OP=0 REUSED=0 TOTAL=221
```

Four defects, eight failures. The duplicate primary key in `customers` broke
referential integrity in **four downstream models** — `addresses`, `orders`,
`order_details` and `order_history` — because the `relationships` tests were
derived from lineage the catalog already knew about. That propagation is the
argument for generating tests from a catalog rather than per-model: one upstream
defect, caught everywhere it actually lands.

## Reproducing

```bash
datahub docker quickstart
datahub datapack load showcase-ecommerce
dbt-testgen validate
cd validation && dbt build --profiles-dir .
```
