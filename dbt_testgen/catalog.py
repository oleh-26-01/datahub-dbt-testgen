"""Read DataHub through the MCP server.

Everything this package knows about the warehouse comes through here, so the
grounding claim is auditable: no test is emitted from a guess about a schema,
only from metadata DataHub actually holds.

Reads and writes both go through the MCP server. The single exception is
`ensure_property_definition`, which uses the Python SDK because the MCP server
exposes no tool for creating a structured-property *definition* — only for
setting values against one that already exists.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .documents import CORPUS_PATTERN, DocumentFacts, parse_corpus

DEFAULT_SERVER = os.environ.get("DBT_TESTGEN_MCP_COMMAND", "mcp-server-datahub")


@dataclass(frozen=True)
class Field:
    """One column, as DataHub describes it."""

    path: str
    native_type: str
    nullable: bool
    description: str = ""
    glossary_terms: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    @property
    def is_pii(self) -> bool:
        marks = {t.upper() for t in self.glossary_terms} | {t.upper() for t in self.tags}
        return bool(marks & {"PII", "SENSITIVE", "PERSONAL_DATA"})

    @property
    def is_numeric(self) -> bool:
        return self.native_type.upper() in {
            "NUMBER", "INT", "INTEGER", "BIGINT", "SMALLINT",
            "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC",
        }


@dataclass
class Dataset:
    """A dbt model as DataHub sees it."""

    urn: str
    name: str
    platform: str
    fields: list[Field] = field(default_factory=list)
    description: str = ""
    upstreams: tuple[str, ...] = ()
    downstreams: tuple[str, ...] = ()

    @property
    def table(self) -> str:
        """Bare table name, e.g. `customers` from a fully qualified URN path."""
        return self.name.split(".")[-1]

    @property
    def column_names(self) -> set[str]:
        return {f.path.lower() for f in self.fields}

    def field_by_path(self, path: str) -> Field | None:
        for f in self.fields:
            if f.path == path:
                return f
        return None


def _text(result: Any) -> str:
    return "\n".join(c.text for c in result.content if getattr(c, "text", None))


def _json(result: Any) -> Any:
    body = _text(result).strip()
    if not body:
        return {}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {}


class Catalog:
    """Thin async wrapper over the DataHub MCP server."""

    def __init__(self, session: ClientSession) -> None:
        self._s = session

    async def dbt_datasets(self, limit: int = 50) -> list[Dataset]:
        """Every dbt-platform dataset in the catalog."""
        out: list[Dataset] = []
        offset = 0
        while len(out) < limit:
            page = _json(
                await self._s.call_tool(
                    "search",
                    {
                        "query": "*",
                        "filter": "entity_type = dataset AND platform = dbt",
                        "num_results": min(50, limit - len(out)),
                        "offset": offset,
                    },
                )
            )
            results = page.get("searchResults") or []
            if not results:
                break
            for r in results:
                ent = r.get("entity") or {}
                urn = ent.get("urn")
                if not urn:
                    continue
                out.append(
                    Dataset(
                        urn=urn,
                        name=(ent.get("properties") or {}).get("name") or urn,
                        platform="dbt",
                        description=(ent.get("properties") or {}).get("description") or "",
                    )
                )
            offset += len(results)
            if offset >= (page.get("total") or 0):
                break
        return out

    async def hydrate(self, ds: Dataset) -> Dataset:
        """Attach schema fields and lineage to a dataset."""
        schema = _json(await self._s.call_tool("list_schema_fields", {"urn": ds.urn}))
        ds.fields = [
            Field(
                path=f.get("fieldPath", ""),
                native_type=f.get("nativeDataType", "") or "",
                nullable=bool(f.get("nullable", True)),
                description=f.get("description", "") or "",
                glossary_terms=tuple(
                    (f.get("editedGlossaryTerms") or []) + (f.get("glossaryTerms") or [])
                ),
                tags=tuple(f.get("tags") or []),
            )
            for f in (schema.get("fields") or [])
            if f.get("fieldPath")
        ]
        ds.upstreams = tuple(await self._lineage(ds.urn, upstream=True))
        ds.downstreams = tuple(await self._lineage(ds.urn, upstream=False))
        return ds

    async def _lineage(self, urn: str, *, upstream: bool) -> list[str]:
        data = _json(await self._s.call_tool("get_lineage", {"urn": urn, "upstream": upstream}))
        block = data.get("upstreams" if upstream else "downstreams") or {}
        urns: list[str] = []
        for r in block.get("searchResults") or block.get("results") or []:
            ent = r.get("entity") or {}
            if ent.get("urn"):
                urns.append(ent["urn"])
        return urns

    async def nullability_census(
        self, platforms: Iterable[str] = ("dbt", "snowflake", "postgres", "s3")
    ) -> dict[str, Counter]:
        """Count NULL / NOT NULL column records per platform.

        Not decoration. `not_null` is the test a schema-driven generator emits
        most, and this is the measurement that decides whether the flag behind
        it means anything. On DataHub's own sample it does not: every platform
        reports a single constant value for every column it holds.
        """
        census: dict[str, Counter] = {}
        for platform in platforms:
            page = _json(
                await self._s.call_tool(
                    "search",
                    {
                        "query": "*",
                        "filter": f"entity_type = dataset AND platform = {platform}",
                        "num_results": 50,
                    },
                )
            )
            counts: Counter = Counter()
            for r in page.get("searchResults") or []:
                urn = (r.get("entity") or {}).get("urn")
                if not urn:
                    continue
                schema = _json(await self._s.call_tool("list_schema_fields", {"urn": urn}))
                for f in schema.get("fields") or []:
                    counts["nullable" if f.get("nullable", True) else "not_null"] += 1
            if counts:
                census[platform] = counts
        return census

    async def documents(self, datasets: Iterable[Dataset]) -> DocumentFacts:
        """Read every document in the deployment and parse out column facts.

        One `search_documents` call to enumerate, one `grep_documents` call to
        pull headings and table rows from all of them at once.
        """
        listing = _json(
            await self._s.call_tool("search_documents", {"query": "*", "num_results": 100})
        )
        urns: list[str] = []
        titles: dict[str, str] = {}
        for r in listing.get("searchResults") or []:
            ent = r.get("entity") or {}
            urn = ent.get("urn")
            if not urn:
                continue
            urns.append(urn)
            titles[urn] = ((ent.get("info") or {}).get("title")) or urn
        if not urns:
            return DocumentFacts()

        known_columns = {d.table.lower(): d.column_names for d in datasets}
        # `urn:li:document:ecomm-order-items` is the document about `order_items`.
        default_tables = {}
        for urn in urns:
            slug = urn.rsplit(":", 1)[-1].split("-", 1)[-1].replace("-", "_").lower()
            if slug in known_columns:
                default_tables[urn] = slug

        grep = _json(
            await self._s.call_tool(
                "grep_documents",
                {
                    "urns": urns,
                    "pattern": CORPUS_PATTERN,
                    "context_chars": 0,
                    "max_matches_per_doc": 300,
                },
            )
        )
        return parse_corpus(grep, titles, default_tables, known_columns)

    async def find_document(self, title: str) -> str | None:
        """The URN of an existing document with this exact title, if any."""
        listing = _json(
            await self._s.call_tool("search_documents", {"query": title, "num_results": 25})
        )
        for r in listing.get("searchResults") or []:
            ent = r.get("entity") or {}
            if ((ent.get("info") or {}).get("title") or "").strip() == title.strip():
                return ent.get("urn")
        return None

    async def save_report(
        self, title: str, content: str, related: Iterable[str] = ()
    ) -> tuple[bool, str]:
        """Publish a report back into the catalog as a Document.

        This package reads what humans documented in order to decide what to
        test. The refusals are the inverse: a ranked list of the columns nobody
        has written down yet. That belongs next to the documentation it is
        asking for, not in a file on somebody's laptop.

        Two things to know about `save_document`. Passing a `urn` only works for
        a document that already exists — creating one lets DataHub mint the URN
        — so re-running looks the title up first. And a failed save comes back
        with `isError` unset and `"success": false` in the body, so the payload
        has to be read rather than trusted.
        """
        args: dict[str, Any] = {
            "document_type": "Analysis",
            "title": title,
            "content": content,
            "topics": ["data quality", "dbt", "testing"],
        }
        related = list(related)
        if related:
            args["related_assets"] = related
        existing = await self.find_document(title)
        if existing:
            args["urn"] = existing

        res = await self._s.call_tool("save_document", args)
        if getattr(res, "isError", False):
            return False, _text(res).strip()[:300]
        body = _json(res)
        if not body.get("success"):
            return False, str(body.get("message") or _text(res))[:300]
        return True, body.get("urn") or ""

    async def write_coverage(self, urn: str, property_urn: str, value: str) -> tuple[bool, str]:
        """Push a computed value back onto the entity as a structured property.

        This is the 'contribute back to the graph' half — the catalog told us
        what to test, so what got tested belongs back in the catalog.

        Returns the error text alongside the flag rather than swallowing it:
        `call_tool` reports tool-level failures by setting `isError` on the
        result, not by raising, so a bare try/except here would report success
        for every failed write.
        """
        res = await self._s.call_tool(
            "add_structured_properties",
            {"entity_urns": [urn], "property_values": {property_urn: [value]}},
        )
        if getattr(res, "isError", False):
            return False, _text(res).strip()[:300]
        return True, ""


def ensure_property_definition(
    gms_url: str,
    qualified_name: str,
    display_name: str,
    description: str,
) -> None:
    """Create the structured-property definition the write-back needs.

    The MCP server can set a property's *value* but has no tool to declare the
    property itself, so this one call goes through the Python SDK. Emitting the
    same definition twice is a no-op, so this is safe to run on every write.
    """
    from datahub.emitter.mcp import MetadataChangeProposalWrapper
    from datahub.emitter.rest_emitter import DatahubRestEmitter
    from datahub.metadata.schema_classes import StructuredPropertyDefinitionClass

    emitter = DatahubRestEmitter(gms_server=gms_url)
    emitter.emit_mcp(
        MetadataChangeProposalWrapper(
            entityUrn=f"urn:li:structuredProperty:{qualified_name}",
            aspect=StructuredPropertyDefinitionClass(
                qualifiedName=qualified_name,
                displayName=display_name,
                description=description,
                valueType="urn:li:dataType:datahub.number",
                cardinality="SINGLE",
                entityTypes=["urn:li:entityType:datahub.dataset"],
            ),
        )
    )


@asynccontextmanager
async def connect(gms_url: str | None = None, *, allow_writes: bool = False):
    """Open a Catalog against a DataHub MCP server."""
    env = dict(os.environ)
    env["DATAHUB_GMS_URL"] = gms_url or env.get("DATAHUB_GMS_URL", "http://localhost:8080")
    if allow_writes:
        env["TOOLS_IS_MUTATION_ENABLED"] = "true"
    params = StdioServerParameters(command=DEFAULT_SERVER, env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            yield Catalog(session)
