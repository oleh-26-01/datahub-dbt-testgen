"""Unit tests for parsing the hand-written half of the catalog.

Weighted heavily toward the things that must *not* be read as an enumeration.
A generated `accepted_values` test that is missing one legal value fails on
correct data, and the reflex is to delete the test rather than trust it — so a
false enum is worse than no enum, and these cases are pinned down hardest.
"""

from __future__ import annotations

import pytest

from dbt_testgen.documents import ColumnDoc, _literal_set, _section_column, parse_corpus


def doc(text, table="orders", column="col"):
    return ColumnDoc(table=table, column=column, text=text,
                     doc_urn="urn:li:document:d", doc_title="Orders Table")


class TestLiteralSets:
    @pytest.mark.parametrize("text,expected", [
        ("`CreditCard`, `PurchaseOrder`, or `AccountBalance`.",
         ["CreditCard", "PurchaseOrder", "AccountBalance"]),
        ("`ground`, `express`, `overnight`, `pickup`.",
         ["ground", "express", "overnight", "pickup"]),
        ("Item condition: `new`, `refurbished`, `used`. Filter to `new` for primary sales.",
         ["new", "refurbished", "used"]),
        ("Channel: `online` (web/app) or `direct` (phone/sales rep).", ["online", "direct"]),
        ("`Y`/`N` — Consented to email marketing.", ["Y", "N"]),
        ("`Y` = hold shipment until all items available. `N` = partial ship OK.", ["Y", "N"]),
        # Multi-word values are legal — the backticks delimit them.
        ("Current availability: `orderable`, `planned`, `under development`, `obsolete`.",
         ["orderable", "planned", "under development", "obsolete"]),
    ])
    def test_reads_closed_sets(self, text, expected):
        assert _literal_set(text) == expected

    def test_deduplicates_repeated_values(self):
        assert _literal_set("`new`, `used`. Prefer `new`.") == ["new", "used"]

    @pytest.mark.parametrize("text,why", [
        ("Shipping weight tier: `1`–`5` (light to heavy).", "a range, not an enumeration"),
        ("Maximum spend on `AccountBalance` payment method.", "a single literal is not a set"),
        ("Shipping cost. Zero for `pickup` orders.", "one literal in prose"),
        ("Referenced by `orders.warehouse_id` and `inventories.warehouse_id`.",
         "column references, not values"),
        ("`unit_price × quantity`", "an expression"),
        ("When `quantity_on_hand < restock_level`, raise a purchase order.", "a predicate"),
        ("Use this for revenue, not `products.list_price`.", "a qualified name"),
        ("Display name (e.g., `Electronics`, `Apparel`).", "e.g. makes it illustrative"),
        ("Status such as `Pending`, `Open`.", "'such as' makes it illustrative"),
        ("Derived from `quantity_on_hand`", "a single reference"),
    ])
    def test_refuses(self, text, why):
        assert _literal_set(text) is None, why


class TestDeclarations:
    def test_primary_key(self):
        assert doc("Primary key.").declares_pk

    def test_primary_category_is_not_a_primary_key(self):
        assert not doc("FK → product_categories. Primary category assignment.").declares_pk

    def test_composite_part(self):
        assert doc("FK → products. Composite PK part 1.").composite_pk_part == 1
        assert doc("FK → warehouses. Composite PK part 2.").composite_pk_part == 2

    @pytest.mark.parametrize("text,target", [
        ("FK → customers. The owning customer.", "customers"),
        ("FK → product_categories. NULL for top-level categories.", "product_categories"),
        ("FK → corpuser. Assigned sales rep (B2B accounts only).", "corpuser"),
        ("FK → internal supplier. The vendor providing the product.", "internal supplier"),
    ])
    def test_foreign_key_recorded_verbatim(self, text, target):
        assert doc(text).fk_target == target

    def test_no_foreign_key(self):
        assert doc("Date the order was placed.").fk_target is None

    @pytest.mark.parametrize("text", [
        "FK → corpuser. Assigned sales rep (B2B accounts only). NULL for B2C.",
        "FK → promotions. NULL means no promotion applied (~65% of orders).",
        "Date item left the warehouse. NULL = not yet shipped.",
        "Promised delivery date. NULL if not yet assigned.",
        "Non-NULL only for `direct` channel orders.",
        "Months of warranty coverage. NULL = no warranty.",
        "Contact phone. May be NULL for legacy accounts.",
    ])
    def test_detects_nullability_prose(self, text):
        assert doc(text).declares_nullable

    @pytest.mark.parametrize("text", [
        "Primary key.",
        "**Gross order value** — sum of all line items at time of order.",
        "Units purchased.",
    ])
    def test_silence_is_not_a_nullability_claim(self, text):
        assert doc(text).declares_nullable is None

    def test_pii_marker(self):
        assert doc("**PII** — Street address.").declares_pii
        assert not doc("Postal code.").declares_pii

    def test_citation_quotes_the_source(self):
        c = doc("FK → customers. The owning customer.")
        assert c.cite() == '"FK → customers. The owning customer" — Orders Table'


class TestSectionHeadings:
    @pytest.mark.parametrize("heading,expected", [
        ("Customer Class Values", "customer_class"),
        ("Order Status Lifecycle", "order_status"),
        ("Product Status Values", "product_status"),
    ])
    def test_maps_heading_to_column(self, heading, expected):
        cols = {"customer_class", "order_status", "product_status", "order_id"}
        assert _section_column(heading, cols) == expected

    def test_unrelated_heading_maps_to_nothing(self):
        assert _section_column("Stock Health Classification", {"order_id"}) is None
        assert _section_column("Common Query Patterns", {"order_id"}) is None


def _grep(urn, matches):
    return {"results": [{"urn": urn, "title": "T",
                         "matches": [{"excerpt": e, "position": p}
                                     for p, e in enumerate(matches)]}]}


class TestCorpusParsing:
    def test_attributes_rows_to_the_document_subject(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-orders",
                  ["## Key Columns", "| `order_id` | Primary key. |"]),
            {"urn:li:document:ecomm-orders": "Orders Table"},
            {"urn:li:document:ecomm-orders": "orders"},
            {"orders": {"order_id"}},
        )
        assert facts.get("orders", "order_id").declares_pk

    def test_section_heading_reassigns_the_table(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-fulfillment",
                  ["## Tables in this section", "### warehouses",
                   "| `warehouse_id` | Primary key. |"]),
            {}, {}, {"warehouses": {"warehouse_id"}},
        )
        assert facts.get("warehouses", "warehouse_id") is not None

    def test_refuses_rows_under_an_ambiguous_heading(self):
        """"### regions / countries" documents two tables; a row could be either."""
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-fulfillment",
                  ["### regions / countries", "| `region_id` | Primary key. |"]),
            {}, {}, {"regions": {"region_id"}, "countries": {"country_id"}},
        )
        assert facts.get("regions", "region_id") is None

    def test_ignores_tables_of_table_names(self):
        """A grain summary lists tables in the first cell, not columns."""
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-source-tables",
                  ["## Table Grain Summary", "| `orders` | One row per order |"]),
            {}, {}, {"orders": {"order_id"}},
        )
        assert facts.columns == {}

    def test_collects_a_value_table(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-orders",
                  ["## Key Columns", "| `order_status` | Lifecycle state. |",
                   "## Order Status Lifecycle", "| `Pending` | Placed. |",
                   "| `Shipped` | Dispatched. |"]),
            {}, {"urn:li:document:ecomm-orders": "orders"},
            {"orders": {"order_status"}},
        )
        values, _ = facts.declared_values("orders", "order_status")
        assert values == ["Pending", "Shipped"]

    def test_single_row_value_table_is_discarded(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-orders",
                  ["## Order Status Lifecycle", "| `Pending` | Placed. |"]),
            {}, {"urn:li:document:ecomm-orders": "orders"},
            {"orders": {"order_status"}},
        )
        assert facts.declared_values("orders", "order_status") is None

    def test_composite_key_is_ordered_by_declared_part(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-inventories",
                  ["## Key Columns",
                   "| `warehouse_id` | FK → warehouses. Composite PK part 2. |",
                   "| `product_id` | FK → products. Composite PK part 1. |"]),
            {}, {"urn:li:document:ecomm-inventories": "inventories"},
            {"inventories": {"product_id", "warehouse_id"}},
        )
        assert facts.composite_pk("inventories") == ["product_id", "warehouse_id"]

    def test_composite_parts_are_not_reported_as_the_primary_key(self):
        facts = parse_corpus(
            _grep("urn:li:document:ecomm-inventories",
                  ["| `product_id` | FK → products. Composite PK part 1. |"]),
            {}, {"urn:li:document:ecomm-inventories": "inventories"},
            {"inventories": {"product_id"}},
        )
        assert facts.primary_key("inventories") is None
