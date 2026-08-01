# Generated test evidence

**195 tests** across **13 models** — mean column coverage **100.0%**.

Each test cites the DataHub metadata that justified it. Where the catalog was ambiguous, no test was emitted and the ambiguity is recorded as a finding.

## Catalog-wide findings

These require comparing every model against every other, which is what a
metadata catalog makes possible and a single dbt project does not.

- **warn** — Column `customer_class` is documented with conflicting value sets across 2 models — `customers` = Platinum, Gold, Silver; `order_details` = Retail, Enterprise, Online. Either these models disagree about the same concept, or the documentation has drifted. The generated accepted_values tests will enforce whichever set each model declares, so a mismatch will surface as a test failure rather than silent skew.
- **warn** — Column `delivery_type` is documented with conflicting value sets across 2 models — `order_details` = Standard, Curbside, Overnight; `orders` = Standard, Express, Overnight. Either these models disagree about the same concept, or the documentation has drifted. The generated accepted_values tests will enforce whichever set each model declares, so a mismatch will surface as a test failure rather than silent skew.
- **warn** — Column `order_mode` is documented with conflicting value sets across 2 models — `order_details` = online, phone, instore; `orders` = online, phone, direct. Either these models disagree about the same concept, or the documentation has drifted. The generated accepted_values tests will enforce whichever set each model declares, so a mismatch will surface as a test failure rather than silent skew.
- **warn** — Column `product_status` is documented with conflicting value sets across 2 models — `order_details` = Active, Inactive, Backordered; `products` = Available, Discontinued, Planned. Either these models disagree about the same concept, or the documentation has drifted. The generated accepted_values tests will enforce whichever set each model declares, so a mismatch will surface as a test failure rather than silent skew.

## `order_details`

Coverage: 100.0% of columns (55/55).

| Column | Test | Evidence |
| --- | --- | --- |
| `billing_address_line1` | `not_null` | DataHub records order_details.billing_address_line1 as NOT NULL |
| `billing_address_line2` | `not_null` | DataHub records order_details.billing_address_line2 as NOT NULL |
| `billing_country` | `not_null` | DataHub records order_details.billing_country as NOT NULL |
| `billing_region` | `not_null` | DataHub records order_details.billing_region as NOT NULL |
| `billing_town_city` | `not_null` | DataHub records order_details.billing_town_city as NOT NULL |
| `billing_zipcode` | `not_null` | DataHub records order_details.billing_zipcode as NOT NULL |
| `category_id` | `not_null` | DataHub records order_details.category_id as NOT NULL |
| `category_name` | `not_null` | DataHub records order_details.category_name as NOT NULL |
| `condition` | `not_null` | DataHub records order_details.condition as NOT NULL |
| `cost_of_delivery` | `not_null` | DataHub records order_details.cost_of_delivery as NOT NULL |
| `cust_email` | `not_null` | DataHub records order_details.cust_email as NOT NULL |
| `cust_first_name` | `not_null` | DataHub records order_details.cust_first_name as NOT NULL |
| `cust_last_name` | `not_null` | DataHub records order_details.cust_last_name as NOT NULL |
| `customer_class` | `not_null` | DataHub records order_details.customer_class as NOT NULL |
| `customer_class` | `accepted_values` | description of customer_class enumerates 3 values |
| `customer_id` | `not_null` | DataHub records order_details.customer_id as NOT NULL |
| `customer_id` | `relationships` | customer_id references customers.customer_id, which exists in the catalog |
| `delivery_status` | `not_null` | DataHub records order_details.delivery_status as NOT NULL |
| `delivery_type` | `not_null` | DataHub records order_details.delivery_type as NOT NULL |
| `delivery_type` | `accepted_values` | description of delivery_type enumerates 3 values |
| `discount_amount` | `not_null` | DataHub records order_details.discount_amount as NOT NULL |
| `discount_percent` | `not_null` | DataHub records order_details.discount_percent as NOT NULL |
| `dispatch_date` | `not_null` | DataHub records order_details.dispatch_date as NOT NULL |
| `estimated_delivery` | `not_null` | DataHub records order_details.estimated_delivery as NOT NULL |
| `gift_wrap` | `not_null` | DataHub records order_details.gift_wrap as NOT NULL |
| `line_item_id` | `not_null` | DataHub records order_details.line_item_id as NOT NULL |
| `line_total` | `not_null` | DataHub records order_details.line_total as NOT NULL |
| `list_price` | `not_null` | DataHub records order_details.list_price as NOT NULL |
| `order_date` | `not_null` | DataHub records order_details.order_date as NOT NULL |
| `order_id` | `not_null` | DataHub records order_details.order_id as NOT NULL |
| `order_id` | `relationships` | order_id references orders.order_id, which exists in the catalog |
| `order_mode` | `not_null` | DataHub records order_details.order_mode as NOT NULL |
| `order_mode` | `accepted_values` | description of order_mode enumerates 3 values |
| `order_status` | `not_null` | DataHub records order_details.order_status as NOT NULL |
| `order_total` | `not_null` | DataHub records order_details.order_total as NOT NULL |
| `payment_method_code` | `not_null` | DataHub records order_details.payment_method_code as NOT NULL |
| `phone_number` | `not_null` | DataHub records order_details.phone_number as NOT NULL |
| `product_description` | `not_null` | DataHub records order_details.product_description as NOT NULL |
| `product_id` | `not_null` | DataHub records order_details.product_id as NOT NULL |
| `product_id` | `relationships` | product_id references products.product_id, which exists in the catalog |
| `product_name` | `not_null` | DataHub records order_details.product_name as NOT NULL |
| `product_status` | `not_null` | DataHub records order_details.product_status as NOT NULL |
| `product_status` | `accepted_values` | description of product_status enumerates 3 values |
| `promotion_description` | `not_null` | DataHub records order_details.promotion_description as NOT NULL |
| `promotion_id` | `not_null` | DataHub records order_details.promotion_id as NOT NULL |
| `promotion_id` | `relationships` | promotion_id references promotions.promotion_id, which exists in the catalog |
| `promotion_name` | `not_null` | DataHub records order_details.promotion_name as NOT NULL |
| `quantity` | `not_null` | DataHub records order_details.quantity as NOT NULL |
| `quantity_on_hand` | `not_null` | DataHub records order_details.quantity_on_hand as NOT NULL |
| `return_date` | `not_null` | DataHub records order_details.return_date as NOT NULL |
| `return_status` | `not_null` | DataHub records order_details.return_status as NOT NULL |
| `shipping_address_line1` | `not_null` | DataHub records order_details.shipping_address_line1 as NOT NULL |
| `shipping_address_line2` | `not_null` | DataHub records order_details.shipping_address_line2 as NOT NULL |
| `shipping_country` | `not_null` | DataHub records order_details.shipping_country as NOT NULL |
| `shipping_region` | `not_null` | DataHub records order_details.shipping_region as NOT NULL |
| `shipping_town_city` | `not_null` | DataHub records order_details.shipping_town_city as NOT NULL |
| `shipping_zipcode` | `not_null` | DataHub records order_details.shipping_zipcode as NOT NULL |
| `stock_status` | `not_null` | DataHub records order_details.stock_status as NOT NULL |
| `unit_price` | `not_null` | DataHub records order_details.unit_price as NOT NULL |
| `updated_at` | `not_null` | DataHub records order_details.updated_at as NOT NULL |
| `wait_till_complete_yn` | `not_null` | DataHub records order_details.wait_till_complete_yn as NOT NULL |
| `warehouse_id` | `not_null` | DataHub records order_details.warehouse_id as NOT NULL |
| `warehouse_id` | `relationships` | warehouse_id references warehouses.warehouse_id, which exists in the catalog |
| `warehouse_name` | `not_null` | DataHub records order_details.warehouse_name as NOT NULL |

- **warn** — Numeric surrogate keys tagged PII: customer_id. These are internal identifiers carrying no personal data — review the tagging, since over-broad PII marking devalues the label.
- info — 17 PII column(s) present (billing_address_line1, billing_address_line2, billing_country, billing_region…). Emitted with meta.contains_pii so downstream tooling can enforce masking.

## `customers`

Coverage: 100.0% of columns (22/22).

| Column | Test | Evidence |
| --- | --- | --- |
| `account_mgr_id` | `not_null` | DataHub records customers.account_mgr_id as NOT NULL |
| `address_line1` | `not_null` | DataHub records customers.address_line1 as NOT NULL |
| `address_line2` | `not_null` | DataHub records customers.address_line2 as NOT NULL |
| `address_line3` | `not_null` | DataHub records customers.address_line3 as NOT NULL |
| `country_id` | `not_null` | DataHub records customers.country_id as NOT NULL |
| `country_id` | `relationships` | country_id references countries.country_id, which exists in the catalog |
| `credit_limit` | `not_null` | DataHub records customers.credit_limit as NOT NULL |
| `cust_email` | `not_null` | DataHub records customers.cust_email as NOT NULL |
| `cust_first_name` | `not_null` | DataHub records customers.cust_first_name as NOT NULL |
| `cust_last_name` | `not_null` | DataHub records customers.cust_last_name as NOT NULL |
| `customer_class` | `not_null` | DataHub records customers.customer_class as NOT NULL |
| `customer_class` | `accepted_values` | description of customer_class enumerates 3 values |
| `customer_id` | `not_null` | DataHub records customers.customer_id as NOT NULL |
| `customer_id` | `unique` | customer_id is the primary-key column for customers |
| `customer_since` | `not_null` | DataHub records customers.customer_since as NOT NULL |
| `dob` | `not_null` | DataHub records customers.dob as NOT NULL |
| `mailshot` | `not_null` | DataHub records customers.mailshot as NOT NULL |
| `nls_language` | `not_null` | DataHub records customers.nls_language as NOT NULL |
| `nls_territory` | `not_null` | DataHub records customers.nls_territory as NOT NULL |
| `partner_mailshot` | `not_null` | DataHub records customers.partner_mailshot as NOT NULL |
| `phone_number` | `not_null` | DataHub records customers.phone_number as NOT NULL |
| `region_id` | `not_null` | DataHub records customers.region_id as NOT NULL |
| `region_id` | `relationships` | region_id references regions.region_id, which exists in the catalog |
| `suggestions` | `not_null` | DataHub records customers.suggestions as NOT NULL |
| `town_city` | `not_null` | DataHub records customers.town_city as NOT NULL |
| `zipcode` | `not_null` | DataHub records customers.zipcode as NOT NULL |

- **warn** — Numeric surrogate keys tagged PII: country_id, customer_id, region_id. These are internal identifiers carrying no personal data — review the tagging, since over-broad PII marking devalues the label.
- info — 10 PII column(s) present (address_line1, address_line2, address_line3, cust_email…). Emitted with meta.contains_pii so downstream tooling can enforce masking.

## `orders`

Coverage: 100.0% of columns (15/15).

| Column | Test | Evidence |
| --- | --- | --- |
| `billing_address_id` | `not_null` | DataHub records orders.billing_address_id as NOT NULL |
| `billing_address_id` | `relationships` | billing_address_id references addresses.address_id, which exists in the catalog |
| `cost_of_delivery` | `not_null` | DataHub records orders.cost_of_delivery as NOT NULL |
| `customer_id` | `not_null` | DataHub records orders.customer_id as NOT NULL |
| `customer_id` | `relationships` | customer_id references customers.customer_id, which exists in the catalog |
| `delivery_address_id` | `not_null` | DataHub records orders.delivery_address_id as NOT NULL |
| `delivery_address_id` | `relationships` | delivery_address_id references addresses.address_id, which exists in the catalog |
| `delivery_type` | `not_null` | DataHub records orders.delivery_type as NOT NULL |
| `delivery_type` | `accepted_values` | description of delivery_type enumerates 3 values |
| `order_date` | `not_null` | DataHub records orders.order_date as NOT NULL |
| `order_id` | `not_null` | DataHub records orders.order_id as NOT NULL |
| `order_id` | `unique` | order_id is the primary-key column for orders |
| `order_mode` | `not_null` | DataHub records orders.order_mode as NOT NULL |
| `order_mode` | `accepted_values` | description of order_mode enumerates 3 values |
| `order_status` | `not_null` | DataHub records orders.order_status as NOT NULL |
| `order_total` | `not_null` | DataHub records orders.order_total as NOT NULL |
| `payment_method_code` | `not_null` | DataHub records orders.payment_method_code as NOT NULL |
| `promotion_id` | `not_null` | DataHub records orders.promotion_id as NOT NULL |
| `promotion_id` | `relationships` | promotion_id references promotions.promotion_id, which exists in the catalog |
| `sales_rep_id` | `not_null` | DataHub records orders.sales_rep_id as NOT NULL |
| `wait_till_complete_yn` | `not_null` | DataHub records orders.wait_till_complete_yn as NOT NULL |
| `warehouse_id` | `not_null` | DataHub records orders.warehouse_id as NOT NULL |
| `warehouse_id` | `relationships` | warehouse_id references warehouses.warehouse_id, which exists in the catalog |

- **warn** — Numeric surrogate keys tagged PII: billing_address_id, customer_id, delivery_address_id. These are internal identifiers carrying no personal data — review the tagging, since over-broad PII marking devalues the label.

## `products`

Coverage: 100.0% of columns (12/12).

| Column | Test | Evidence |
| --- | --- | --- |
| `catalog_url` | `not_null` | DataHub records products.catalog_url as NOT NULL |
| `category_id` | `not_null` | DataHub records products.category_id as NOT NULL |
| `date_added` | `not_null` | DataHub records products.date_added as NOT NULL |
| `list_price` | `not_null` | DataHub records products.list_price as NOT NULL |
| `min_price` | `not_null` | DataHub records products.min_price as NOT NULL |
| `product_description` | `not_null` | DataHub records products.product_description as NOT NULL |
| `product_id` | `not_null` | DataHub records products.product_id as NOT NULL |
| `product_id` | `unique` | product_id is the primary-key column for products |
| `product_name` | `not_null` | DataHub records products.product_name as NOT NULL |
| `product_status` | `not_null` | DataHub records products.product_status as NOT NULL |
| `product_status` | `accepted_values` | description of product_status enumerates 3 values |
| `supplier_id` | `not_null` | DataHub records products.supplier_id as NOT NULL |
| `warranty_period` | `not_null` | DataHub records products.warranty_period as NOT NULL |
| `weight_class` | `not_null` | DataHub records products.weight_class as NOT NULL |

## `addresses`

Coverage: 100.0% of columns (9/9).

| Column | Test | Evidence |
| --- | --- | --- |
| `address_id` | `not_null` | DataHub records addresses.address_id as NOT NULL |
| `address_id` | `unique` | address_id is the primary-key column for addresses |
| `address_line1` | `not_null` | DataHub records addresses.address_line1 as NOT NULL |
| `address_line2` | `not_null` | DataHub records addresses.address_line2 as NOT NULL |
| `country_id` | `not_null` | DataHub records addresses.country_id as NOT NULL |
| `country_id` | `relationships` | country_id references countries.country_id, which exists in the catalog |
| `customer_id` | `not_null` | DataHub records addresses.customer_id as NOT NULL |
| `customer_id` | `relationships` | customer_id references customers.customer_id, which exists in the catalog |
| `date_created` | `not_null` | DataHub records addresses.date_created as NOT NULL |
| `region_id` | `not_null` | DataHub records addresses.region_id as NOT NULL |
| `region_id` | `relationships` | region_id references regions.region_id, which exists in the catalog |
| `town_city` | `not_null` | DataHub records addresses.town_city as NOT NULL |
| `zipcode` | `not_null` | DataHub records addresses.zipcode as NOT NULL |

- **warn** — Numeric surrogate keys tagged PII: address_id, customer_id. These are internal identifiers carrying no personal data — review the tagging, since over-broad PII marking devalues the label.
- info — 4 PII column(s) present (address_line1, address_line2, town_city, zipcode). Emitted with meta.contains_pii so downstream tooling can enforce masking.

## `order_items`

Coverage: 100.0% of columns (11/11).

| Column | Test | Evidence |
| --- | --- | --- |
| `condition` | `not_null` | DataHub records order_items.condition as NOT NULL |
| `dispatch_date` | `not_null` | DataHub records order_items.dispatch_date as NOT NULL |
| `estimated_delivery` | `not_null` | DataHub records order_items.estimated_delivery as NOT NULL |
| `gift_wrap` | `not_null` | DataHub records order_items.gift_wrap as NOT NULL |
| `line_item_id` | `not_null` | DataHub records order_items.line_item_id as NOT NULL |
| `order_id` | `not_null` | DataHub records order_items.order_id as NOT NULL |
| `order_id` | `relationships` | order_id references orders.order_id, which exists in the catalog |
| `product_id` | `not_null` | DataHub records order_items.product_id as NOT NULL |
| `product_id` | `relationships` | product_id references products.product_id, which exists in the catalog |
| `quantity` | `not_null` | DataHub records order_items.quantity as NOT NULL |
| `return_date` | `not_null` | DataHub records order_items.return_date as NOT NULL |
| `supplier_id` | `not_null` | DataHub records order_items.supplier_id as NOT NULL |
| `unit_price` | `not_null` | DataHub records order_items.unit_price as NOT NULL |

## `inventories`

Coverage: 100.0% of columns (6/6).

| Column | Test | Evidence |
| --- | --- | --- |
| `max_stock_level` | `not_null` | DataHub records inventories.max_stock_level as NOT NULL |
| `product_id` | `not_null` | DataHub records inventories.product_id as NOT NULL |
| `product_id` | `relationships` | product_id references products.product_id, which exists in the catalog |
| `quantity_on_hand` | `not_null` | DataHub records inventories.quantity_on_hand as NOT NULL |
| `reorder_quantity` | `not_null` | DataHub records inventories.reorder_quantity as NOT NULL |
| `restock_level` | `not_null` | DataHub records inventories.restock_level as NOT NULL |
| `warehouse_id` | `not_null` | DataHub records inventories.warehouse_id as NOT NULL |
| `warehouse_id` | `relationships` | warehouse_id references warehouses.warehouse_id, which exists in the catalog |

## `promotions`

Coverage: 100.0% of columns (6/6).

| Column | Test | Evidence |
| --- | --- | --- |
| `promotion_cost` | `not_null` | DataHub records promotions.promotion_cost as NOT NULL |
| `promotion_description` | `not_null` | DataHub records promotions.promotion_description as NOT NULL |
| `promotion_end_date` | `not_null` | DataHub records promotions.promotion_end_date as NOT NULL |
| `promotion_id` | `not_null` | DataHub records promotions.promotion_id as NOT NULL |
| `promotion_id` | `unique` | promotion_id is the primary-key column for promotions |
| `promotion_name` | `not_null` | DataHub records promotions.promotion_name as NOT NULL |
| `promotion_start_date` | `not_null` | DataHub records promotions.promotion_start_date as NOT NULL |

## `order_history`

Coverage: 100.0% of columns (5/5).

| Column | Test | Evidence |
| --- | --- | --- |
| `as_of_date` | `not_null` | DataHub records order_history.as_of_date as NOT NULL |
| `customer_id` | `not_null` | DataHub records order_history.customer_id as NOT NULL |
| `customer_id` | `relationships` | customer_id references customers.customer_id, which exists in the catalog |
| `order_id` | `not_null` | DataHub records order_history.order_id as NOT NULL |
| `order_id` | `relationships` | order_id references orders.order_id, which exists in the catalog |
| `order_status` | `not_null` | DataHub records order_history.order_status as NOT NULL |
| `order_total` | `not_null` | DataHub records order_history.order_total as NOT NULL |

- **warn** — Numeric surrogate keys tagged PII: customer_id. These are internal identifiers carrying no personal data — review the tagging, since over-broad PII marking devalues the label.

## `regions`

Coverage: 100.0% of columns (4/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `country_id` | `not_null` | DataHub records regions.country_id as NOT NULL |
| `country_id` | `relationships` | country_id references countries.country_id, which exists in the catalog |
| `nls_language` | `not_null` | DataHub records regions.nls_language as NOT NULL |
| `region_id` | `not_null` | DataHub records regions.region_id as NOT NULL |
| `region_id` | `unique` | region_id is the primary-key column for regions |
| `region_name` | `not_null` | DataHub records regions.region_name as NOT NULL |

## `countries`

Coverage: 100.0% of columns (4/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `country_code` | `not_null` | DataHub records countries.country_code as NOT NULL |
| `country_id` | `not_null` | DataHub records countries.country_id as NOT NULL |
| `country_id` | `unique` | country_id is the primary-key column for countries |
| `country_name` | `not_null` | DataHub records countries.country_name as NOT NULL |
| `nls_territory` | `not_null` | DataHub records countries.nls_territory as NOT NULL |

## `warehouses`

Coverage: 100.0% of columns (4/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `location_id` | `not_null` | DataHub records warehouses.location_id as NOT NULL |
| `warehouse_id` | `not_null` | DataHub records warehouses.warehouse_id as NOT NULL |
| `warehouse_id` | `unique` | warehouse_id is the primary-key column for warehouses |
| `warehouse_name` | `not_null` | DataHub records warehouses.warehouse_name as NOT NULL |
| `wh_geo_location` | `not_null` | DataHub records warehouses.wh_geo_location as NOT NULL |

## `product_categories`

Coverage: 100.0% of columns (4/4).

| Column | Test | Evidence |
| --- | --- | --- |
| `category_description` | `not_null` | DataHub records product_categories.category_description as NOT NULL |
| `category_id` | `not_null` | DataHub records product_categories.category_id as NOT NULL |
| `category_name` | `not_null` | DataHub records product_categories.category_name as NOT NULL |
| `parent_category_id` | `not_null` | DataHub records product_categories.parent_category_id as NOT NULL |
