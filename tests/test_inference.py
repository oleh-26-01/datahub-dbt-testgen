"""Unit tests for the inference rules.

These run without DataHub — they exercise the rules against hand-built metadata,
so the refusal behaviour is pinned down as tightly as the emission behaviour.
What a generator declines to emit matters more than what it emits.
"""

from __future__ import annotations

import pytest

from dbt_testgen.catalog import Dataset, Field
from dbt_testgen.inference import cross_model_findings, plan_all, plan_model


def col(path, dtype="TEXT", nullable=True, desc="", terms=()):
    return Field(path=path, native_type=dtype, nullable=nullable,
                 description=desc, glossary_terms=tuple(terms))


def ds(table, fields, urn=None):
    return Dataset(urn=urn or f"urn:li:dataset:(urn:li:dataPlatform:dbt,db.{table},PROD)",
                   name=f"db.{table}", platform="dbt", fields=fields)


def emitted_for(plan, column):
    return {t.name for t in plan.tests if t.column == column}


class TestNotNull:
    def test_emitted_for_non_nullable(self):
        d = ds("orders", [col("total", "NUMBER", nullable=False)])
        assert "not_null" in emitted_for(plan_model(d, {"orders": d}), "total")

    def test_absent_for_nullable(self):
        d = ds("orders", [col("note", nullable=True)])
        assert "not_null" not in emitted_for(plan_model(d, {"orders": d}), "note")


class TestPrimaryKey:
    def test_singular_table_id_is_pk(self):
        d = ds("customers", [col("customer_id", "NUMBER", nullable=False)])
        assert "unique" in emitted_for(plan_model(d, {"customers": d}), "customer_id")

    def test_bare_id_is_pk(self):
        d = ds("events", [col("id", "NUMBER", nullable=False)])
        assert "unique" in emitted_for(plan_model(d, {"events": d}), "id")

    def test_nullable_column_is_never_a_pk(self):
        d = ds("customers", [col("customer_id", "NUMBER", nullable=True)])
        assert "unique" not in emitted_for(plan_model(d, {"customers": d}), "customer_id")

    def test_only_one_pk_per_model(self):
        d = ds("customers", [col("id", "NUMBER", nullable=False),
                             col("customer_id", "NUMBER", nullable=False)])
        plan = plan_model(d, {"customers": d})
        assert len([t for t in plan.tests if t.name == "unique"]) == 1


class TestRelationships:
    """The rule that must refuse rather than guess."""

    def test_resolves_plural_target(self):
        countries = ds("countries", [col("country_id", "NUMBER", nullable=False)])
        addresses = ds("addresses", [col("country_id", "NUMBER", nullable=False)])
        tables = {"countries": countries, "addresses": addresses}
        assert "relationships" in emitted_for(plan_model(addresses, tables), "country_id")

    def test_resolves_y_to_ies(self):
        """`category_id` -> `categories`, the case a naive pluraliser misses."""
        categories = ds("categories", [col("category_id", "NUMBER", nullable=False)])
        products = ds("products", [col("category_id", "NUMBER", nullable=False)])
        tables = {"categories": categories, "products": products}
        assert "relationships" in emitted_for(plan_model(products, tables), "category_id")

    def test_resolves_qualified_key_via_trailing_noun(self):
        """`billing_address_id` -> `addresses`."""
        addresses = ds("addresses", [col("address_id", "NUMBER", nullable=False)])
        orders = ds("orders", [col("billing_address_id", "NUMBER", nullable=False)])
        tables = {"addresses": addresses, "orders": orders}
        assert "relationships" in emitted_for(plan_model(orders, tables), "billing_address_id")

    def test_refuses_when_target_absent(self):
        """The central guarantee: no test pointing at a table we cannot see."""
        orders = ds("orders", [col("supplier_id", "NUMBER", nullable=False)])
        plan = plan_model(orders, {"orders": orders})
        assert "relationships" not in emitted_for(plan, "supplier_id")

    def test_refuses_when_target_has_no_pk(self):
        regions = ds("regions", [col("label", nullable=True)])   # no identifiable PK
        stores = ds("stores", [col("region_id", "NUMBER", nullable=False)])
        tables = {"regions": regions, "stores": stores}
        plan = plan_model(stores, tables)
        assert "relationships" not in emitted_for(plan, "region_id")
        assert any("no identifiable primary key" in f.message for f in plan.findings)

    def test_does_not_self_reference(self):
        customers = ds("customers", [col("customer_id", "NUMBER", nullable=False)])
        plan = plan_model(customers, {"customers": customers})
        assert "relationships" not in emitted_for(plan, "customer_id")

    @pytest.mark.parametrize("name", ["uuid", "guid", "trace_id", "request_id"])
    def test_ignores_non_foreign_key_identifiers(self, name):
        other = ds("traces", [col("trace_id", "NUMBER", nullable=False)])
        d = ds("events", [col(name, "TEXT", nullable=False)])
        assert "relationships" not in emitted_for(plan_model(d, {"events": d, "traces": other}), name)


class TestAcceptedValues:
    def test_recovers_enum_from_description(self):
        d = ds("orders", [col("status", desc="Order state (e.g., Pending, Shipped, Delivered)")])
        plan = plan_model(d, {"orders": d})
        vals = [t.config["values"] for t in plan.tests if t.name == "accepted_values"]
        assert vals and set(vals[0]) == {"Pending", "Shipped", "Delivered"}

    def test_ignores_two_value_prose(self):
        """Two items reads as prose, not an enumeration."""
        d = ds("orders", [col("note", desc="Free text, e.g. comments or remarks")])
        assert "accepted_values" not in emitted_for(plan_model(d, {"orders": d}), "note")

    def test_ignores_numeric_columns(self):
        d = ds("orders", [col("qty", "NUMBER", desc="Amount (e.g., 1, 2, 3)")])
        assert "accepted_values" not in emitted_for(plan_model(d, {"orders": d}), "qty")

    def test_no_description_no_test(self):
        d = ds("orders", [col("status")])
        assert "accepted_values" not in emitted_for(plan_model(d, {"orders": d}), "status")


class TestPiiFindings:
    def test_flags_numeric_surrogate_key_tagged_pii(self):
        d = ds("customers", [col("customer_id", "NUMBER", nullable=False, terms=["PII"])])
        plan = plan_model(d, {"customers": d})
        assert any("surrogate keys tagged PII" in f.message for f in plan.findings)

    def test_does_not_flag_genuine_pii(self):
        d = ds("customers", [col("cust_email", "TEXT", nullable=False, terms=["PII"])])
        plan = plan_model(d, {"customers": d})
        assert not any("surrogate keys" in f.message for f in plan.findings)


class TestCrossModel:
    def test_detects_conflicting_enums(self):
        a = ds("customers", [col("tier", desc="Level (e.g., Gold, Silver, Bronze)")])
        b = ds("orders", [col("tier", desc="Level (e.g., Retail, Direct, Partner)")])
        findings = cross_model_findings(plan_all([a, b]))
        assert any("conflicting value sets" in f.message for f in findings)

    def test_silent_when_enums_agree(self):
        a = ds("customers", [col("tier", desc="Level (e.g., Gold, Silver, Bronze)")])
        b = ds("orders", [col("tier", desc="Level (e.g., Gold, Silver, Bronze)")])
        findings = cross_model_findings(plan_all([a, b]))
        assert not any("conflicting value sets" in f.message for f in findings)

    def test_detects_nullability_disagreement(self):
        a = ds("customers", [col("email", nullable=False)])
        b = ds("leads", [col("email", nullable=True)])
        findings = cross_model_findings(plan_all([a, b]))
        assert any("NOT NULL in" in f.message for f in findings)


class TestCoverage:
    def test_coverage_is_fraction_of_columns_tested(self):
        d = ds("orders", [col("a", nullable=False), col("b"), col("c"), col("d")])
        assert plan_model(d, {"orders": d}).coverage == 25.0

    def test_empty_schema_reports_finding(self):
        d = ds("orders", [])
        plan = plan_model(d, {"orders": d})
        assert plan.coverage == 0.0
        assert any("No schema" in f.message for f in plan.findings)
