"""Read DataHub through the MCP server.

Everything this package knows about the warehouse comes through here, so the
grounding claim is auditable: no test is emitted from a guess about a schema,
only from metadata DataHub actually holds.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Iterable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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
    owners: tuple[str, ...] = ()
    domain: str | None = None
    description: str = ""
    upstreams: tuple[str, ...] = ()
    downstreams: tuple[str, ...] = ()

    @property
    def table(self) -> str:
        """Bare table name, e.g. `customers` from a fully qualified URN path."""
        return self.name.split(".")[-1]

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

    async def write_coverage(self, urn: str, prop: str, value: str) -> bool:
        """Push a computed value back onto the entity as a structured property.

        This is the 'contribute back to the graph' half — the catalog told us
        what to test, so the test outcome belongs back in the catalog.
        """
        try:
            await self._s.call_tool(
                "add_structured_properties",
                {"urns": [urn], "structured_properties": {prop: [value]}},
            )
            return True
        except Exception:
            return False


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
