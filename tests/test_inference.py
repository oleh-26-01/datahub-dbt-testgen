"""Unit tests for the inference rules.

These run without DataHub — they exercise the rules against hand-built metadata,
so the refusal behaviour is pinned down as tightly as the emission behaviour.
What a generator declines to emit matters more than what it emits.
"""

from __future__ import annotations

import pytest

from dbt_testgen.catalog import Dataset, Field
from dbt_testgen.documents import ColumnDoc, DocumentFacts
from dbt_testgen.inference import (
    census_finding,
    cross_model_findings,
    plan_all,
    plan_model,
    refusal_summary,
)


def col(path, dtype="TEXT", nullable=False, desc="", terms=()):
    """Columns default to NOT NULL — that is what dbt reports for every column."""
    return Field(path=path, native_type=dtype, nullable=nullable,
                 description=desc, glossary_terms=tuple(terms))


def ds(table, fields, urn=None, upstreams=()):
    return Dataset(urn=urn or f"urn:li:dataset:(urn:li:dataPlatform:dbt,db.{table},PROD)",
                   name=f"db.{table}", platform="dbt", fields=fields,
                   upstreams=tuple(upstreams))


def facts(*rows, values=None):
    """Build DocumentFacts from (table, column, text) triples."""
    f = DocumentFacts(documents_read=1)
    for table, column, text in rows:
        f.columns[(table, column)] = ColumnDoc(
            table=table, column=column, text=text,
            doc_urn=f"urn:li:document:{table}", doc_title=f"{table.title()} Table",
        )
    for (table, column), vals in (values or {}).items():
        f.value_tables[(table, column)] = (vals, f"{table.title()} Table")
    return f


def plan_one(d, docs=None, others=None):
    tables = {d.table: d}
    tables.update({o.table: o for o in (others or [])})
    by_urn = {x.urn: x for x in tables.values()}
    return plan_model(d, tables, docs or DocumentFacts(), by_urn)


def emitted_for(plan, column):
    return {t.name for t in plan.tests if t.column == column}


def refused_for(plan, column):
    return {r.kind for r in plan.refusals if r.column == column}


class TestNotNull:
    def test_not_emitted_from_the_schema_flag(self):
        """The flag is a per-platform constant, so it justifies nothing."""
        d = ds("orders", [col("order_total", "NUMBER")])
        plan = plan_one(d)
        assert emitted_for(plan, "order_total") == set()
        assert refused_for(plan, "order_total") == {"nullability-flag"}

    def test_emitted_for_a_documented_primary_key(self):
        d = ds("orders", [col("order_id", "NUMBER")])
        plan = plan_one(d, facts(("orders", "order_id", "Primary key.")))
        assert "not_null" in emitted_for(plan, "order_id")

    def test_emitted_for_each_part_of_a_composite_key(self):
        d = ds("inventories", [col("product_id", "NUMBER"), col("warehouse_id", "NUMBER")])
        plan = plan_one(d, facts(
            ("inventories", "product_id", "FK → products. Composite PK part 1."),
            ("inventories", "warehouse_id", "FK → warehouses. Composite PK part 2."),
        ))
        assert "not_null" in emitted_for(plan, "product_id")
        assert "not_null" in emitted_for(plan, "warehouse_id")

    def test_retracted_when_documentation_contradicts_the_flag(self):
        d = ds("orders", [col("promotion_id", "NUMBER")])
        plan = plan_one(d, facts(
            ("orders", "promotion_id",
             "FK → promotions. NULL means no promotion applied (~65% of orders)."),
        ))
        assert "not_null" not in emitted_for(plan, "promotion_id")
        assert "contradicted" in refused_for(plan, "promotion_id")

    def test_inferred_from_a_documented_fk_when_the_author_tracks_nulls(self):
        d = ds("orders", [col("customer_id", "NUMBER"), col("promotion_id", "NUMBER")])
        plan = plan_one(d, facts(
            ("orders", "customer_id", "FK → customers. The buyer."),
            ("orders", "promotion_id", "FK → promotions. NULL means no promotion applied."),
        ))
        assert "not_null" in emitted_for(plan, "customer_id")

    def test_not_inferred_when_the_author_never_mentions_nulls(self):
        """Silence only means something from an author who speaks about nulls."""
        d = ds("orders", [col("customer_id", "NUMBER")])
        plan = plan_one(d, facts(("orders", "customer_id", "FK → customers. The buyer.")))
        assert "not_null" not in emitted_for(plan, "customer_id")


class TestUnique:
    def test_emitted_for_a_documented_primary_key(self):
        d = ds("customers", [col("customer_id", "NUMBER")])
        plan = plan_one(d, facts(("customers", "customer_id", "Primary key.")))
        assert "unique" in emitted_for(plan, "customer_id")

    def test_refused_without_documentation(self):
        """`customer_id` on `customers` looks like a key. Looking like one is not evidence."""
        d = ds("customers", [col("customer_id", "NUMBER")])
        plan = plan_one(d)
        assert "unique" not in emitted_for(plan, "customer_id")

    def test_refused_for_part_of_a_composite_key(self):
        d = ds("inventories", [col("product_id", "NUMBER"), col("warehouse_id", "NUMBER")])
        plan = plan_one(d, facts(
            ("inventories", "product_id", "FK → products. Composite PK part 1."),
            ("inventories", "warehouse_id", "FK → warehouses. Composite PK part 2."),
        ))
        assert "unique" not in emitted_for(plan, "product_id")
        assert "composite-pk" in refused_for(plan, "product_id")


class TestRelationships:
    def test_emitted_when_the_documented_target_exists(self):
        customers = ds("customers", [col("customer_id", "NUMBER")])
        orders = ds("orders", [col("customer_id", "NUMBER")])
        plan = plan_one(orders, facts(("orders", "customer_id", "FK → customers. The buyer.")),
                        others=[customers])
        rel = next(t for t in plan.tests if t.name == "relationships")
        assert rel.config == {"to": "ref('customers')", "field": "customer_id"}

    def test_refused_when_the_documented_target_is_not_a_table(self):
        d = ds("customers", [col("account_mgr_id", "NUMBER")])
        plan = plan_one(d, facts(
            ("customers", "account_mgr_id", "FK → corpuser. Assigned sales rep."),
        ))
        assert "relationships" not in emitted_for(plan, "account_mgr_id")
        assert "non-table-fk" in refused_for(plan, "account_mgr_id")

    def test_refused_when_the_target_lacks_the_join_column(self):
        countries = ds("countries", [col("iso_code")])
        addresses = ds("addresses", [col("country_id", "NUMBER")])
        plan = plan_one(addresses, facts(("addresses", "country_id", "FK → countries.")),
                        others=[countries])
        assert "unresolved-fk" in refused_for(plan, "country_id")

    def test_refused_when_only_the_name_suggests_a_target(self):
        countries = ds("countries", [col("country_id", "NUMBER")])
        addresses = ds("addresses", [col("country_id", "NUMBER")])
        plan = plan_one(addresses, others=[countries])
        assert "relationships" not in emitted_for(plan, "country_id")
        assert "unresolved-fk" in refused_for(plan, "country_id")

    def test_does_not_self_reference(self):
        d = ds("customers", [col("customer_id", "NUMBER")])
        plan = plan_one(d, facts(("customers", "customer_id", "Primary key.")))
        assert "relationships" not in emitted_for(plan, "customer_id")

    def test_ignores_identifiers_that_are_not_foreign_keys(self):
        d = ds("events", [col("request_id"), col("trace_id"), col("uuid")])
        plan = plan_one(d)
        assert not any(r.kind == "unresolved-fk" for r in plan.refusals)


class TestAcceptedValues:
    def test_emitted_from_a_documented_value_table(self):
        d = ds("orders", [col("order_status")])
        plan = plan_one(d, facts(("orders", "order_status", "Lifecycle state."),
                                 values={("orders", "order_status"): ["Pending", "Shipped"]}))
        test = next(t for t in plan.tests if t.name == "accepted_values")
        assert test.config == {"values": ["Pending", "Shipped"]}

    def test_refused_for_an_illustrative_description(self):
        d = ds("customers", [col("customer_class",
                                 desc="Classification of the customer "
                                      "(e.g., Platinum, Gold, Silver)")])
        plan = plan_one(d)
        assert "accepted_values" not in emitted_for(plan, "customer_class")
        assert "illustrative-enum" in refused_for(plan, "customer_class")

    def test_documentation_beats_the_description(self):
        d = ds("customers", [col("customer_class", desc="(e.g., Platinum, Gold, Silver)")])
        plan = plan_one(d, facts(("customers", "customer_class", "Segmentation tier."),
                                 values={("customers", "customer_class"):
                                         ["Premium", "Standard"]}))
        test = next(t for t in plan.tests if t.name == "accepted_values")
        assert test.config == {"values": ["Premium", "Standard"]}


class TestLineageInheritance:
    def _view(self):
        items = ds("order_items", [col("order_id", "NUMBER"), col("return_date", "DATE")])
        orders = ds("orders", [col("order_id", "NUMBER")])
        view = ds("order_details", [col("order_id", "NUMBER"), col("return_date", "DATE")],
                  upstreams=[items.urn, orders.urn])
        return view, items, orders

    def test_documentation_travels_along_a_lineage_edge(self):
        view, items, orders = self._view()
        plan = plan_one(view, facts(
            ("order_items", "order_id", "FK → orders."),
            ("order_items", "return_date", "Date returned. NULL = not returned."),
        ), others=[items, orders])
        rel = next(t for t in plan.tests if t.name == "relationships")
        assert rel.config["to"] == "ref('orders')"
        assert rel.source == "document+lineage"

    def test_a_nullability_caveat_travels_too(self):
        view, items, orders = self._view()
        plan = plan_one(view, facts(
            ("order_items", "return_date", "Date returned. NULL = not returned."),
        ), others=[items, orders])
        assert "not_null" not in emitted_for(plan, "return_date")
        assert "contradicted" in refused_for(plan, "return_date")

    def test_refuses_when_upstreams_disagree(self):
        a = ds("addresses", [col("owner_id", "NUMBER")])
        b = ds("orders", [col("owner_id", "NUMBER")])
        view = ds("report", [col("owner_id", "NUMBER")], upstreams=[a.urn, b.urn])
        plan = plan_one(view, facts(
            ("addresses", "owner_id", "FK → customers."),
            ("orders", "owner_id", "FK → warehouses."),
        ), others=[a, b])
        assert "conflicting-upstreams" in refused_for(plan, "owner_id")

    def test_own_documentation_wins_over_inherited(self):
        view, items, orders = self._view()
        plan = plan_one(view, facts(
            ("order_items", "order_id", "FK → orders."),
            ("order_details", "order_id", "Primary key."),
        ), others=[items, orders])
        assert "unique" in emitted_for(plan, "order_id")


class TestCensus:
    def test_reports_a_constant_flag_as_carrying_no_information(self):
        f = census_finding({
            "dbt": {"not_null": 157, "nullable": 0},
            "snowflake": {"not_null": 0, "nullable": 212},
        })
        assert f.severity == "warn"
        assert "no information" in f.message

    def test_reports_variance_as_ordinary_information(self):
        f = census_finding({"dbt": {"not_null": 100, "nullable": 57}})
        assert f.severity == "info"

    def test_empty_census_says_nothing(self):
        assert census_finding({}) is None


class TestCrossModel:
    def test_reports_descriptions_that_contradict_the_documentation(self):
        a = ds("customers", [col("customer_class", desc="(e.g., Platinum, Gold, Silver)")])
        b = ds("order_details", [col("customer_class", desc="(e.g., Retail, Enterprise)")])
        docs = facts(("customers", "customer_class", "Segmentation tier."),
                     values={("customers", "customer_class"): ["Premium", "Standard"]})
        found = cross_model_findings(plan_all([a, b], docs), docs)
        assert any("customer_class" in f.message and "Premium" in f.message for f in found)

    def test_silent_when_everything_agrees(self):
        a = ds("orders", [col("order_total", "NUMBER")])
        b = ds("order_history", [col("order_total", "NUMBER")])
        assert cross_model_findings(plan_all([a, b])) == []


class TestSummary:
    def test_counts_refusals_by_kind(self):
        d = ds("orders", [col("a"), col("b")])
        counts = refusal_summary(plan_all([d]))
        assert counts["nullability-flag"] == 2

    def test_coverage_varies_with_evidence(self):
        d = ds("orders", [col("order_id", "NUMBER"), col("note"), col("memo")])
        bare = plan_one(d)
        documented = plan_one(d, facts(("orders", "order_id", "Primary key.")))
        assert bare.coverage == 0.0
        assert documented.coverage == pytest.approx(33.3)
