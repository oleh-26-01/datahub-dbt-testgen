# Generated test evidence

**75 tests emitted. 139 tests refused.**

Across 11 models, mean column coverage 37.8%. Every emitted test cites a sentence written by a human in one of the 18 documents this DataHub deployment holds. Every refused test names the evidence that was missing.

The second number is the one worth reading. A generated test that cannot be justified fails on correct data, and the reflex is to delete it — along with the tests that mattered.

## What was refused, and why

| Count | Refusal |
| --- | --- |
| 119 | not_null declined — the flag behind it is a per-platform constant |
| 13 | not_null retracted — documentation says the column is nullable |
| 3 | relationships declined — nothing in the catalog declares a target |
| 2 | relationships declined — the documented target is not a table |
| 2 | unique declined — the documented key is composite |

## Nullability census

The measurement behind the `not_null` policy, taken from the catalog itself.

| Platform | NOT NULL | nullable | varies? |
| --- | --- | --- | --- |
| dbt | 157 | 0 | no — constant |
| postgres | 0 | 102 | no — constant |
| s3 | 102 | 0 | no — constant |
| snowflake | 0 | 212 | no — constant |

## Catalog-wide findings

These require comparing every model against every other, which is what a
metadata catalog makes possible and a single dbt project does not.

- **warn** — Nullability in this catalog carries no information: every platform reports one constant value for every column it holds — dbt 157/157 NOT NULL; postgres 102/102 nullable; s3 102/102 NOT NULL; snowflake 212/212 nullable. The same physical column is NOT NULL or nullable depending only on which connector you ask, so `not_null` generated from the flag would assert nothing. This tool emits it from documentation instead.
- **warn** — `condition` is described the same way in 2 models, and the description matches no documented value. `order_details` description says New, Refurbished; `order_items` description says New, Refurbished. Meanwhile Order Items Table says new, refurbished, used. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.
- **warn** — `customer_class` is described 2 different ways across 2 models, and the description matches no documented value. `customers` description says Platinum, Gold, Silver; `order_details` description says Retail, Enterprise, Online. Meanwhile Customers Table says Premium, Standard. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.
- **warn** — `delivery_type` is described 2 different ways across 2 models, and the description matches no documented value. `order_details` description says Standard, Curbside, Overnight; `orders` description says Standard, Express, Overnight. Meanwhile Orders Table says ground, express, overnight, pickup. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.
- **warn** — `order_mode` is described 2 different ways across 2 models, and the description matches no documented value. `order_details` description says online, phone, instore; `orders` description says online, phone, direct. Meanwhile Orders Table says online, direct. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.
- **warn** — `order_status` is described the same way in 2 models, and the description matches no documented value. `order_details` description says 1=Pending, 2=Processing, 3=Shipped; `orders` description says 1=Pending, 2=Processing, 3=Shipped. Meanwhile Orders Table says Pending, Open, Shipped, Complete, Cancelled, On Hold. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.
- **warn** — `product_status` is described 2 different ways across 2 models, and the description matches no documented value. `order_details` description says Active, Inactive, Backordered; `products` description says Available, Discontinued, Planned. Meanwhile Products Table says orderable, planned, under development, obsolete. Every description is prefixed "e.g.", so no accepted_values test is generated from them; the documented set is used instead, and the drift is reported here.

## `order_details`

Coverage: 27.3% of columns (15/55).

| Column | Test | Evidence |
| --- | --- | --- |
| `category_id` | `not_null` | category_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate (documented on `products`, inherited across a lineage edge DataHub records) |
| `category_id` | `relationships` | documentation declares category_id references product_categories, and product_categories.category_id exists in the catalog: "FK → product_categories. Primary category assignment" — Products Table (documented on `products`, inherited across a lineage edge DataHub records) |
| `condition` | `accepted_values` | Order Items Table enumerates 3 legal values for condition (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `customer_class` | `accepted_values` | Customers Table enumerates 2 legal values for customer_class (documented on `customers`, inherited across a lineage edge DataHub records) |
| `customer_id` | `not_null` | customer_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate (documented on `orders`, inherited across a lineage edge DataHub records) |
| `customer_id` | `relationships` | documentation declares customer_id references customers, and customers.customer_id exists in the catalog: "FK → customers. The buyer" — Orders Table (documented on `orders`, inherited across a lineage edge DataHub records) |
| `delivery_type` | `accepted_values` | Orders Table enumerates 4 legal values for delivery_type (documented on `orders`, inherited across a lineage edge DataHub records) |
| `gift_wrap` | `accepted_values` | Order Items Table enumerates 2 legal values for gift_wrap (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `order_id` | `not_null` | order_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `order_id` | `relationships` | documentation declares order_id references orders, and orders.order_id exists in the catalog: "FK → orders" — Order Items Table (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `order_mode` | `accepted_values` | Orders Table enumerates 2 legal values for order_mode (documented on `orders`, inherited across a lineage edge DataHub records) |
| `order_status` | `accepted_values` | Orders Table enumerates 6 legal values for order_status (documented on `orders`, inherited across a lineage edge DataHub records) |
| `payment_method_code` | `accepted_values` | Orders Table enumerates 3 legal values for payment_method_code (documented on `orders`, inherited across a lineage edge DataHub records) |
| `product_id` | `not_null` | product_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `product_id` | `relationships` | documentation declares product_id references products, and products.product_id exists in the catalog: "FK → products" — Order Items Table (documented on `order_items`, inherited across a lineage edge DataHub records) |
| `product_status` | `accepted_values` | Products Table enumerates 4 legal values for product_status (documented on `products`, inherited across a lineage edge DataHub records) |
| `promotion_id` | `relationships` | documentation declares promotion_id references promotions, and promotions.promotion_id exists in the catalog: "FK → promotions. NULL means no promotion applied (~65% of orders)" — Orders Table (documented on `orders`, inherited across a lineage edge DataHub records) |
| `wait_till_complete_yn` | `accepted_values` | Orders Table enumerates 2 legal values for wait_till_complete_yn (documented on `orders`, inherited across a lineage edge DataHub records) |
| `warehouse_id` | `not_null` | warehouse_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate (documented on `orders`, inherited across a lineage edge DataHub records) |
| `warehouse_id` | `relationships` | documentation declares warehouse_id references warehouses, and warehouses.warehouse_id exists in the catalog: "FK → warehouses. Fulfillment center assigned" — Orders Table (documented on `orders`, inherited across a lineage edge DataHub records) |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `billing_address_line1` | `not_null` | DataHub marks order_details.billing_address_line1 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `billing_address_line2` | `not_null` | DataHub marks order_details.billing_address_line2 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `billing_country` | `not_null` | DataHub marks order_details.billing_country NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `billing_region` | `not_null` | DataHub marks order_details.billing_region NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `billing_town_city` | `not_null` | DataHub marks order_details.billing_town_city NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `billing_zipcode` | `not_null` | DataHub marks order_details.billing_zipcode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `category_name` | `not_null` | DataHub marks order_details.category_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `condition` | `not_null` | DataHub marks order_details.condition NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cost_of_delivery` | `not_null` | DataHub marks order_details.cost_of_delivery NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_email` | `not_null` | DataHub marks order_details.cust_email NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_first_name` | `not_null` | DataHub marks order_details.cust_first_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_last_name` | `not_null` | DataHub marks order_details.cust_last_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `customer_class` | `not_null` | DataHub marks order_details.customer_class NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `delivery_status` | `not_null` | DataHub marks order_details.delivery_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `delivery_type` | `not_null` | DataHub marks order_details.delivery_type NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `discount_amount` | `not_null` | DataHub marks order_details.discount_amount NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `discount_percent` | `not_null` | DataHub marks order_details.discount_percent NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `dispatch_date` | `not_null` | DataHub's schema marks order_details.dispatch_date NOT NULL, but the catalog's own documentation says otherwise: "Date item left the warehouse. NULL = not yet shipped" — Order Items Table (documented on `order_items`, inherited across a lineage edge DataHub records). The documentation wins. |
| `estimated_delivery` | `not_null` | DataHub's schema marks order_details.estimated_delivery NOT NULL, but the catalog's own documentation says otherwise: "Promised delivery date. NULL if not yet assigned" — Order Items Table (documented on `order_items`, inherited across a lineage edge DataHub records). The documentation wins. |
| `gift_wrap` | `not_null` | DataHub marks order_details.gift_wrap NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `line_item_id` | `not_null` | DataHub marks order_details.line_item_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `line_total` | `not_null` | DataHub marks order_details.line_total NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `list_price` | `not_null` | DataHub marks order_details.list_price NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_date` | `not_null` | DataHub marks order_details.order_date NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_mode` | `not_null` | DataHub marks order_details.order_mode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_status` | `not_null` | DataHub marks order_details.order_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_total` | `not_null` | DataHub marks order_details.order_total NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `payment_method_code` | `not_null` | DataHub marks order_details.payment_method_code NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `phone_number` | `not_null` | DataHub marks order_details.phone_number NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_description` | `not_null` | DataHub marks order_details.product_description NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_name` | `not_null` | DataHub marks order_details.product_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_status` | `not_null` | DataHub marks order_details.product_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_description` | `not_null` | DataHub marks order_details.promotion_description NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_id` | `not_null` | DataHub's schema marks order_details.promotion_id NOT NULL, but the catalog's own documentation says otherwise: "FK → promotions. NULL means no promotion applied (~65% of orders)" — Orders Table (documented on `orders`, inherited across a lineage edge DataHub records). The documentation wins. |
| `promotion_name` | `not_null` | DataHub marks order_details.promotion_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `quantity` | `not_null` | DataHub marks order_details.quantity NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `quantity_on_hand` | `not_null` | DataHub marks order_details.quantity_on_hand NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `return_date` | `not_null` | DataHub's schema marks order_details.return_date NOT NULL, but the catalog's own documentation says otherwise: "Date customer returned item. NULL = not returned" — Order Items Table (documented on `order_items`, inherited across a lineage edge DataHub records). The documentation wins. |
| `return_status` | `not_null` | DataHub marks order_details.return_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_address_line1` | `not_null` | DataHub marks order_details.shipping_address_line1 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_address_line2` | `not_null` | DataHub marks order_details.shipping_address_line2 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_country` | `not_null` | DataHub marks order_details.shipping_country NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_region` | `not_null` | DataHub marks order_details.shipping_region NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_town_city` | `not_null` | DataHub marks order_details.shipping_town_city NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `shipping_zipcode` | `not_null` | DataHub marks order_details.shipping_zipcode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `stock_status` | `not_null` | DataHub marks order_details.stock_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `unit_price` | `not_null` | DataHub marks order_details.unit_price NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `updated_at` | `not_null` | DataHub marks order_details.updated_at NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `wait_till_complete_yn` | `not_null` | DataHub marks order_details.wait_till_complete_yn NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `warehouse_name` | `not_null` | DataHub marks order_details.warehouse_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `orders`

Coverage: 73.3% of columns (11/15).

| Column | Test | Evidence |
| --- | --- | --- |
| `billing_address_id` | `not_null` | billing_address_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `customer_id` | `not_null` | customer_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `customer_id` | `relationships` | documentation declares customer_id references customers, and customers.customer_id exists in the catalog: "FK → customers. The buyer" — Orders Table |
| `delivery_address_id` | `not_null` | delivery_address_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `delivery_type` | `accepted_values` | Orders Table enumerates 4 legal values for delivery_type |
| `order_id` | `not_null` | order_id is documented as the primary key of orders; a key column cannot be null |
| `order_id` | `unique` | order_id is declared the primary key of orders: "Primary key" — Orders Table |
| `order_mode` | `accepted_values` | Orders Table enumerates 2 legal values for order_mode |
| `order_status` | `accepted_values` | Orders Table enumerates 6 legal values for order_status |
| `payment_method_code` | `accepted_values` | Orders Table enumerates 3 legal values for payment_method_code |
| `promotion_id` | `relationships` | documentation declares promotion_id references promotions, and promotions.promotion_id exists in the catalog: "FK → promotions. NULL means no promotion applied (~65% of orders)" — Orders Table |
| `wait_till_complete_yn` | `accepted_values` | Orders Table enumerates 2 legal values for wait_till_complete_yn |
| `warehouse_id` | `not_null` | warehouse_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `warehouse_id` | `relationships` | documentation declares warehouse_id references warehouses, and warehouses.warehouse_id exists in the catalog: "FK → warehouses. Fulfillment center assigned" — Orders Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `billing_address_id` | `relationships` | documentation points billing_address_id at `addresses`, but that model has no `billing_address_id` column to join on. |
| `cost_of_delivery` | `not_null` | DataHub marks orders.cost_of_delivery NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `delivery_address_id` | `relationships` | documentation points delivery_address_id at `addresses`, but that model has no `delivery_address_id` column to join on. |
| `delivery_type` | `not_null` | DataHub marks orders.delivery_type NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_date` | `not_null` | DataHub marks orders.order_date NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_mode` | `not_null` | DataHub marks orders.order_mode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_status` | `not_null` | DataHub marks orders.order_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_total` | `not_null` | DataHub marks orders.order_total NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `payment_method_code` | `not_null` | DataHub marks orders.payment_method_code NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_id` | `not_null` | DataHub's schema marks orders.promotion_id NOT NULL, but the catalog's own documentation says otherwise: "FK → promotions. NULL means no promotion applied (~65% of orders)" — Orders Table. The documentation wins. |
| `sales_rep_id` | `not_null` | DataHub's schema marks orders.sales_rep_id NOT NULL, but the catalog's own documentation says otherwise: "Non-NULL only for `direct` channel orders" — Orders Table. The documentation wins. |
| `wait_till_complete_yn` | `not_null` | DataHub marks orders.wait_till_complete_yn NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `customers`

Coverage: 27.3% of columns (6/22).

| Column | Test | Evidence |
| --- | --- | --- |
| `country_id` | `not_null` | country_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `country_id` | `relationships` | documentation declares country_id references countries, and countries.country_id exists in the catalog: "FK → countries. Billing country" — Customers Table |
| `customer_class` | `accepted_values` | Customers Table enumerates 2 legal values for customer_class |
| `customer_id` | `not_null` | customer_id is documented as the primary key of customers; a key column cannot be null |
| `customer_id` | `unique` | customer_id is declared the primary key of customers: "Primary key" — Customers Table |
| `mailshot` | `accepted_values` | Customers Table enumerates 2 legal values for mailshot |
| `partner_mailshot` | `accepted_values` | Customers Table enumerates 2 legal values for partner_mailshot |
| `region_id` | `not_null` | region_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `region_id` | `relationships` | documentation declares region_id references regions, and regions.region_id exists in the catalog: "FK → regions. Billing region" — Customers Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `account_mgr_id` | `not_null` | DataHub's schema marks customers.account_mgr_id NOT NULL, but the catalog's own documentation says otherwise: "FK → corpuser. Assigned sales rep (B2B accounts only). NULL for B2C" — Customers Table. The documentation wins. |
| `account_mgr_id` | `relationships` | documentation declares account_mgr_id points at `corpuser`, which is not a model in this catalog — "FK → corpuser. Assigned sales rep (B2B accounts only). NULL for B2C" — Customers Table. A name-matching generator would have pointed this at whatever table the column name resembles. |
| `address_line1` | `not_null` | DataHub marks customers.address_line1 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `address_line2` | `not_null` | DataHub marks customers.address_line2 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `address_line3` | `not_null` | DataHub marks customers.address_line3 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `credit_limit` | `not_null` | DataHub marks customers.credit_limit NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_email` | `not_null` | DataHub marks customers.cust_email NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_first_name` | `not_null` | DataHub marks customers.cust_first_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `cust_last_name` | `not_null` | DataHub marks customers.cust_last_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `customer_class` | `not_null` | DataHub marks customers.customer_class NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `customer_since` | `not_null` | DataHub marks customers.customer_since NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `dob` | `not_null` | DataHub marks customers.dob NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `mailshot` | `not_null` | DataHub marks customers.mailshot NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `nls_language` | `not_null` | DataHub marks customers.nls_language NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `nls_territory` | `not_null` | DataHub marks customers.nls_territory NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `partner_mailshot` | `not_null` | DataHub marks customers.partner_mailshot NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `phone_number` | `not_null` | DataHub marks customers.phone_number NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `suggestions` | `not_null` | DataHub marks customers.suggestions NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `town_city` | `not_null` | DataHub marks customers.town_city NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `zipcode` | `not_null` | DataHub marks customers.zipcode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

- **warn** — Tagged PII in the schema but not marked PII in the document that lists this table's personal data: address_line1, address_line2, address_line3, country_id, customer_id, region_id, town_city, zipcode. The document marks 5 column(s) — cust_email, cust_first_name, cust_last_name, dob, phone_number. Over-broad tagging devalues the label, which is how real PII ends up ignored.

## `order_items`

Coverage: 45.5% of columns (5/11).

| Column | Test | Evidence |
| --- | --- | --- |
| `condition` | `accepted_values` | Order Items Table enumerates 3 legal values for condition |
| `gift_wrap` | `accepted_values` | Order Items Table enumerates 2 legal values for gift_wrap |
| `line_item_id` | `not_null` | line_item_id is documented as the primary key of order_items; a key column cannot be null |
| `line_item_id` | `unique` | line_item_id is declared the primary key of order_items: "Primary key" — Order Items Table |
| `order_id` | `not_null` | order_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `order_id` | `relationships` | documentation declares order_id references orders, and orders.order_id exists in the catalog: "FK → orders" — Order Items Table |
| `product_id` | `not_null` | product_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `product_id` | `relationships` | documentation declares product_id references products, and products.product_id exists in the catalog: "FK → products" — Order Items Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `condition` | `not_null` | DataHub marks order_items.condition NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `dispatch_date` | `not_null` | DataHub's schema marks order_items.dispatch_date NOT NULL, but the catalog's own documentation says otherwise: "Date item left the warehouse. NULL = not yet shipped" — Order Items Table. The documentation wins. |
| `estimated_delivery` | `not_null` | DataHub's schema marks order_items.estimated_delivery NOT NULL, but the catalog's own documentation says otherwise: "Promised delivery date. NULL if not yet assigned" — Order Items Table. The documentation wins. |
| `gift_wrap` | `not_null` | DataHub marks order_items.gift_wrap NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `quantity` | `not_null` | DataHub marks order_items.quantity NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `return_date` | `not_null` | DataHub's schema marks order_items.return_date NOT NULL, but the catalog's own documentation says otherwise: "Date customer returned item. NULL = not returned" — Order Items Table. The documentation wins. |
| `supplier_id` | `not_null` | DataHub marks order_items.supplier_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `unit_price` | `not_null` | DataHub marks order_items.unit_price NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `products`

Coverage: 33.3% of columns (4/12).

| Column | Test | Evidence |
| --- | --- | --- |
| `category_id` | `not_null` | category_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |
| `category_id` | `relationships` | documentation declares category_id references product_categories, and product_categories.category_id exists in the catalog: "FK → product_categories. Primary category assignment" — Products Table |
| `product_id` | `not_null` | product_id is documented as the primary key of products; a key column cannot be null |
| `product_id` | `unique` | product_id is declared the primary key of products: "Primary key" — Products Table |
| `product_status` | `accepted_values` | Products Table enumerates 4 legal values for product_status |
| `supplier_id` | `not_null` | supplier_id is documented as a foreign key with no nullability caveat, in a document that annotates other columns as nullable — the omission is deliberate |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `catalog_url` | `not_null` | DataHub marks products.catalog_url NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `date_added` | `not_null` | DataHub marks products.date_added NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `list_price` | `not_null` | DataHub marks products.list_price NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `min_price` | `not_null` | DataHub marks products.min_price NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_description` | `not_null` | DataHub marks products.product_description NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_name` | `not_null` | DataHub marks products.product_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_status` | `not_null` | DataHub marks products.product_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `supplier_id` | `relationships` | documentation declares supplier_id points at `internal supplier`, which is not a model in this catalog — "FK → internal supplier. The vendor providing the product" — Products Table. A name-matching generator would have pointed this at whatever table the column name resembles. |
| `warranty_period` | `not_null` | DataHub's schema marks products.warranty_period NOT NULL, but the catalog's own documentation says otherwise: "Months of warranty coverage. NULL = no warranty" — Products Table. The documentation wins. |
| `weight_class` | `not_null` | DataHub marks products.weight_class NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `addresses`

Coverage: 44.4% of columns (4/9).

| Column | Test | Evidence |
| --- | --- | --- |
| `address_id` | `not_null` | address_id is documented as the primary key of addresses; a key column cannot be null |
| `address_id` | `unique` | address_id is declared the primary key of addresses: "Primary key" — Addresses Table |
| `country_id` | `relationships` | documentation declares country_id references countries, and countries.country_id exists in the catalog: "FK → countries" — Addresses Table |
| `customer_id` | `relationships` | documentation declares customer_id references customers, and customers.customer_id exists in the catalog: "FK → customers. The owning customer" — Addresses Table |
| `region_id` | `relationships` | documentation declares region_id references regions, and regions.region_id exists in the catalog: "FK → regions" — Addresses Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `address_line1` | `not_null` | DataHub marks addresses.address_line1 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `address_line2` | `not_null` | DataHub marks addresses.address_line2 NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `country_id` | `not_null` | DataHub marks addresses.country_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `customer_id` | `not_null` | DataHub marks addresses.customer_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `date_created` | `not_null` | DataHub marks addresses.date_created NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `region_id` | `not_null` | DataHub marks addresses.region_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `town_city` | `not_null` | DataHub marks addresses.town_city NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `zipcode` | `not_null` | DataHub marks addresses.zipcode NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

- **warn** — Tagged PII in the schema but not marked PII in the document that lists this table's personal data: address_id, customer_id, town_city, zipcode. The document marks 2 column(s) — address_line1, address_line2. Over-broad tagging devalues the label, which is how real PII ends up ignored.

## `inventories`

Coverage: 33.3% of columns (2/6).

| Column | Test | Evidence |
| --- | --- | --- |
| `product_id` | `not_null` | product_id is documented as part of the composite primary key of inventories; a key column cannot be null |
| `product_id` | `relationships` | documentation declares product_id references products, and products.product_id exists in the catalog: "FK → products. Composite PK part 1" — Inventories Table |
| `warehouse_id` | `not_null` | warehouse_id is documented as part of the composite primary key of inventories; a key column cannot be null |
| `warehouse_id` | `relationships` | documentation declares warehouse_id references warehouses, and warehouses.warehouse_id exists in the catalog: "FK → warehouses. Composite PK part 2" — Inventories Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `max_stock_level` | `not_null` | DataHub marks inventories.max_stock_level NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `product_id` | `unique` | product_id is only part 1 of a documented composite key (product_id, warehouse_id) — unique on it alone would fail on correct data. |
| `quantity_on_hand` | `not_null` | DataHub marks inventories.quantity_on_hand NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `reorder_quantity` | `not_null` | DataHub marks inventories.reorder_quantity NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `restock_level` | `not_null` | DataHub marks inventories.restock_level NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `warehouse_id` | `unique` | warehouse_id is only part 2 of a documented composite key (product_id, warehouse_id) — unique on it alone would fail on correct data. |

</details>

- info — Documented composite primary key (product_id, warehouse_id). dbt's built-in `unique` test takes a single column, so no uniqueness test is emitted — enforcing this needs `dbt_utils.unique_combination_of_columns`.

## `product_categories`

Coverage: 50.0% of columns (2/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `category_id` | `not_null` | category_id is documented as the primary key of product_categories; a key column cannot be null |
| `category_id` | `unique` | category_id is declared the primary key of product_categories: "Primary key" — Fulfillment & Reference Data |
| `parent_category_id` | `relationships` | documentation declares parent_category_id references product_categories, and product_categories.parent_category_id exists in the catalog: "FK → product_categories. NULL for top-level categories" — Fulfillment & Reference Data |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `category_description` | `not_null` | DataHub marks product_categories.category_description NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `category_name` | `not_null` | DataHub marks product_categories.category_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `parent_category_id` | `not_null` | DataHub's schema marks product_categories.parent_category_id NOT NULL, but the catalog's own documentation says otherwise: "FK → product_categories. NULL for top-level categories" — Fulfillment & Reference Data. The documentation wins. |

</details>

## `order_history`

Coverage: 40.0% of columns (2/5).

| Column | Test | Evidence |
| --- | --- | --- |
| `customer_id` | `relationships` | documentation declares customer_id references customers, and customers.customer_id exists in the catalog: "FK → customers" — Order History View |
| `order_id` | `relationships` | documentation declares order_id references orders, and orders.order_id exists in the catalog: "FK → orders" — Order History View |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `as_of_date` | `not_null` | DataHub marks order_history.as_of_date NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `customer_id` | `not_null` | DataHub marks order_history.customer_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_id` | `not_null` | DataHub marks order_history.order_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_status` | `not_null` | DataHub marks order_history.order_status NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `order_total` | `not_null` | DataHub marks order_history.order_total NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `promotions`

Coverage: 16.7% of columns (1/6).

| Column | Test | Evidence |
| --- | --- | --- |
| `promotion_id` | `not_null` | promotion_id is documented as the primary key of promotions; a key column cannot be null |
| `promotion_id` | `unique` | promotion_id is declared the primary key of promotions: "Primary key" — Promotions Table |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `promotion_cost` | `not_null` | DataHub marks promotions.promotion_cost NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_description` | `not_null` | DataHub marks promotions.promotion_description NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_end_date` | `not_null` | DataHub's schema marks promotions.promotion_end_date NOT NULL, but the catalog's own documentation says otherwise: "Date promotion expired. NULL = still active" — Promotions Table. The documentation wins. |
| `promotion_name` | `not_null` | DataHub marks promotions.promotion_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `promotion_start_date` | `not_null` | DataHub marks promotions.promotion_start_date NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `warehouses`

Coverage: 25.0% of columns (1/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `warehouse_id` | `not_null` | warehouse_id is documented as the primary key of warehouses; a key column cannot be null |
| `warehouse_id` | `unique` | warehouse_id is declared the primary key of warehouses: "Primary key. Referenced by `orders.warehouse_id` and `inventories.warehouse_id`" — Fulfillment & Reference Data |

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `location_id` | `not_null` | DataHub marks warehouses.location_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `warehouse_name` | `not_null` | DataHub marks warehouses.warehouse_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `wh_geo_location` | `not_null` | DataHub marks warehouses.wh_geo_location NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `countries`

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `country_code` | `not_null` | DataHub marks countries.country_code NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `country_id` | `not_null` | DataHub marks countries.country_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `country_name` | `not_null` | DataHub marks countries.country_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `nls_territory` | `not_null` | DataHub marks countries.nls_territory NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>

## `regions`

<details><summary>Refused here</summary>

| Column | Not emitted | Why |
| --- | --- | --- |
| `country_id` | `not_null` | DataHub marks regions.country_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `country_id` | `relationships` | the name country_id resembles a key into `countries`, but nothing in the catalog declares that relationship. Resemblance is not evidence. |
| `nls_language` | `not_null` | DataHub marks regions.nls_language NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `region_id` | `not_null` | DataHub marks regions.region_id NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |
| `region_name` | `not_null` | DataHub marks regions.region_name NOT NULL, but every dbt column in this catalog carries that flag — it identifies the connector, not the column. |

</details>
