# Example output

Real output from a real run against DataHub's `showcase-ecommerce` sample —
13 dbt models, 157 columns, 18 documents. Nothing here is illustrative or
hand-written.

One number to explain before you spot it: `EVIDENCE.md` here says it read **19**
documents, not 18. The sample ships 18; the nineteenth is the one this tool
publishes with `--publish-gaps`, and this copy was regenerated after that ran. A
first run against a fresh `datahub datapack load showcase-ecommerce` reports 18.

| File | What it is |
| --- | --- |
| [`schema.yml`](schema.yml) | The generated dbt test file — drop straight into `models/` |
| [`EVIDENCE.md`](EVIDENCE.md) | Every emitted test with its citation, every refused test with its reason |
| [`dbt-build-pass.log`](dbt-build-pass.log) | The 75 generated tests, executed |
| [`dbt-build-refused.log`](dbt-build-refused.log) | The retracted tests added back — they fail |
| [`dbt-build-fail.log`](dbt-build-fail.log) | The generated tests against deliberately corrupted data |

## 1. The generated tests run

**`dbt-build-pass.log`** — all 75 tests execute against dbt 1.12 + DuckDB, over
13 seeded models:

```
Done. PASS=101 WARN=0 ERROR=0 SKIP=0 NO-OP=0 REUSED=0 TOTAL=101
```

The seed data deliberately contains NULLs in every column the catalog's
documentation describes as sometimes-empty — `orders.promotion_id`,
`order_items.return_date`, `customers.account_mgr_id` and ten others. The suite
passes anyway, because no `not_null` test was generated for those columns.

## 2. The refusals were right

**`dbt-build-refused.log`** — the interesting one. `dbt-testgen validate
--with-refused` adds back the 13 `not_null` tests that were retracted because the
documentation contradicts the schema flag. Same seeds, same 75 tests, plus those
13:

```
Done. PASS=101 WARN=0 ERROR=13 SKIP=0 NO-OP=0 REUSED=0 TOTAL=114
```

```
FAIL 4 not_null_customers_account_mgr_id
FAIL 4 not_null_orders_promotion_id
FAIL 4 not_null_orders_sales_rep_id
FAIL 4 not_null_order_items_dispatch_date
FAIL 4 not_null_order_items_estimated_delivery
FAIL 4 not_null_order_items_return_date
FAIL 4 not_null_order_details_dispatch_date
FAIL 4 not_null_order_details_estimated_delivery
FAIL 4 not_null_order_details_promotion_id
FAIL 4 not_null_order_details_return_date
FAIL 4 not_null_product_categories_parent_category_id
FAIL 4 not_null_products_warranty_period
FAIL 4 not_null_promotions_promotion_end_date
```

The 101 evidenced tests still pass, and **exactly** the 13 retracted ones fail.
DataHub's schema marks every one of those columns NOT NULL. DataHub's own
documentation says otherwise — `orders.promotion_id` is null on roughly 65% of
orders — and the documentation is right.

Four of the thirteen are on `order_details`, which has no documentation of its
own. Those were retracted because DataHub records `order_details` as a view over
`order_items` and `orders`, so the caveats written there travel down the lineage
edge.

## 3. The tests are not vacuous

**`dbt-build-fail.log`** — four defects injected into the seeds
(`inject_defects.py` at the repo root):

1. a duplicate value in `customers.customer_id`, declared "Primary key."
2. an empty `orders.order_id`, also a documented key
3. `Refunded` in `orders.order_status` — outside the six states the Orders Table
   document lists
4. `order_items.order_id = 999999`, pointing at no order

Ten tests failed:

```
FAIL unique_customers_customer_id
FAIL not_null_orders_order_id
FAIL accepted_values_orders_order_status__Pending__Open__Shipped__Complete__Cancelled__On_Hold
FAIL relationships_addresses_customer_id__customer_id__ref_customers_
FAIL relationships_orders_customer_id__customer_id__ref_customers_
FAIL relationships_order_history_customer_id__customer_id__ref_customers_
FAIL relationships_order_details_customer_id__customer_id__ref_customers_
FAIL relationships_order_items_order_id__order_id__ref_orders_
FAIL relationships_order_history_order_id__order_id__ref_orders_
FAIL relationships_order_details_order_id__order_id__ref_orders_

Done. PASS=91 WARN=0 ERROR=10 SKIP=0 NO-OP=0 REUSED=0 TOTAL=101
```

Four defects, ten failures. The broken key in `customers` surfaced in four
downstream models and the broken `order_id` in three more, because the
`relationships` tests were built from foreign keys a human declared in writing.
One upstream defect, caught everywhere it actually lands.

## Reproducing

```bash
datahub docker quickstart
datahub datapack load showcase-ecommerce
pip install -e ".[validate]"

dbt-testgen generate                                    # schema.yml + EVIDENCE.md
dbt-testgen validate && (cd validation && dbt build --profiles-dir .)
dbt-testgen validate --with-refused && (cd validation && dbt build --profiles-dir .)
python inject_defects.py && (cd validation && dbt build --profiles-dir .)
```
