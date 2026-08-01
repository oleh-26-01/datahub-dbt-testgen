"""Read the hand-written half of the catalog.

Schema metadata says what a column *is*. Documents say what a human *knows*
about it — that `promotion_id` is null on about 65% of orders, that
`inventories` has a composite key, that `account_mgr_id` points at a user
rather than a table. None of that is inferable from a column name or a type.

Where the two halves disagree, this package believes the human. That is the
whole reason this module exists: DataHub's nullability flags turn out to be a
per-platform constant (see `nullability_is_constant` in `inference.py`), so the
documentation is the only source in the catalog that actually varies per column.

Content is read through `grep_documents`, one call for the whole corpus. Note
that `get_entities` returns a bare URN for a Document and no body at all, even
though `search_documents` tells you to call it for exactly that — so grep is the
only way to see the text. Reported upstream; see README, "Feedback to DataHub".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping

# Headings, and markdown table rows whose first cell is a single backticked
# token. One pattern for both so a single grep call returns them interleaved,
# and `position` puts them back in document order.
CORPUS_PATTERN = r"(?m)^#{2,3} [^\n]+|^\| `[^`|]+` \| [^|\n]+"

_HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
_ROW = re.compile(r"^\|\s*`([^`|]+)`\s*\|\s*(.*?)\s*$")

_FK = re.compile(r"FK\s*(?:→|->)\s*([^.,|]+)")
_PK = re.compile(r"(?i)\bprimary key\b")
_COMPOSITE = re.compile(r"(?i)\bcomposite pk part\s*(\d+)")
_PII = re.compile(r"\*\*PII\*\*")

# A human saying, in prose, that the column is not always populated.
_NULLABLE = re.compile(
    r"(?i)\b(NULL\s*(?:for|means|if|when|=)[^.|]*"
    r"|(?:may|can|will)\s+be\s+NULL[^.|]*"
    r"|Non-NULL only[^.|]*)"
)

_BACKTICKED = re.compile(r"`([^`]+)`")
# "`1`–`5`" is a range, not an enumeration. Emitting accepted_values for it
# would reject every value in between.
_RANGE = re.compile(r"`\s*[–—-]\s*`")
# "e.g." means the list is illustrative. Treating it as exhaustive is how
# generated accepted_values tests end up rejecting valid data.
_ILLUSTRATIVE = re.compile(r"(?i)\b(?:e\.g\.?|for example|such as|including)\b")
# Anything that makes a backticked span a code fragment rather than a literal.
_NOT_A_LITERAL = re.compile(r"[.<>=×*/\\+()]")

# Trailing words in a section heading that name the section, not the column:
# "Customer Class Values" documents `customer_class`.
_HEADING_NOISE = {
    "values", "value", "lifecycle", "reference", "codes", "code",
    "classification", "states", "state", "tiers", "tier", "levels", "types",
}
_COLUMN_SECTIONS = {"key columns", "columns", "key computed columns"}


@dataclass(frozen=True)
class ColumnDoc:
    """One row of a documented column table, plus where it came from."""

    table: str
    column: str
    text: str
    doc_urn: str
    doc_title: str

    def cite(self) -> str:
        return f'"{self.text.rstrip(" .")}" — {self.doc_title}'

    @property
    def declares_pk(self) -> bool:
        return bool(_PK.search(self.text))

    @property
    def composite_pk_part(self) -> int | None:
        m = _COMPOSITE.search(self.text)
        return int(m.group(1)) if m else None

    @property
    def declares_pii(self) -> bool:
        return bool(_PII.search(self.text))

    @property
    def fk_target(self) -> str | None:
        """The table name a human wrote down, verbatim and un-normalised.

        May not be a table at all — `FK -> corpuser` and `FK -> internal
        supplier` both appear in DataHub's own sample. Resolving that is the
        caller's job; recording it faithfully is this one's.
        """
        m = _FK.search(self.text)
        return m.group(1).strip().lower() if m else None

    @property
    def declares_nullable(self) -> str | None:
        """The phrase in which a human said this column is sometimes empty."""
        m = _NULLABLE.search(self.text)
        return m.group(1).strip().rstrip(".") if m else None

    @property
    def inline_values(self) -> list[str] | None:
        """Backtick-delimited literals that read as a closed set."""
        return _literal_set(self.text)


def _literal_set(text: str) -> list[str] | None:
    """Extract an exhaustive enumeration, or nothing.

    Every rejection here is deliberate. A generated `accepted_values` test that
    is missing one legal value is worse than no test: it fails on correct data,
    and the reflex is to delete the test rather than trust it.
    """
    if _RANGE.search(text):
        return None
    spans = _BACKTICKED.findall(text)
    if len(spans) < 2:
        return None
    # "e.g." before the first literal makes the list illustrative.
    head = text[: text.index("`")] if "`" in text else text
    if _ILLUSTRATIVE.search(head):
        return None
    out: list[str] = []
    for s in spans:
        s = s.strip()
        if not s or len(s) > 30 or _NOT_A_LITERAL.search(s):
            # One code fragment in the cell means the backticks are being used
            # for markup, not enumeration. Reject the whole list.
            return None
        if s not in out:
            out.append(s)
    return out if len(out) >= 2 else None


def _section_column(heading: str, columns: Iterable[str]) -> str | None:
    """Map "Order Status Lifecycle" onto the `order_status` column."""
    words = [w for w in re.split(r"[^A-Za-z0-9]+", heading.lower()) if w]
    while words and words[-1] in _HEADING_NOISE:
        words.pop()
    if not words:
        return None
    known = set(columns)
    # Longest contiguous run of heading words that names a real column.
    for size in range(len(words), 0, -1):
        for start in range(0, len(words) - size + 1):
            cand = "_".join(words[start:start + size])
            if cand in known:
                return cand
    return None


@dataclass
class DocumentFacts:
    """Everything the organisation's own prose declares about its columns."""

    columns: dict[tuple[str, str], ColumnDoc] = dc_field(default_factory=dict)
    value_tables: dict[tuple[str, str], tuple[list[str], str]] = dc_field(default_factory=dict)
    documents_read: int = 0
    documents_with_columns: int = 0
    rows_parsed: int = 0

    def get(self, table: str, column: str) -> ColumnDoc | None:
        return self.columns.get((table.lower(), column.lower()))

    def declared_values(self, table: str, column: str) -> tuple[list[str], str] | None:
        """A dedicated "## X Values" table beats an inline list."""
        hit = self.value_tables.get((table.lower(), column.lower()))
        if hit:
            return hit
        doc = self.get(table, column)
        if doc:
            vals = doc.inline_values
            if vals:
                return vals, doc.doc_title
        return None

    def composite_pk(self, table: str) -> list[str]:
        parts = [
            (d.composite_pk_part, d.column)
            for (t, _), d in self.columns.items()
            if t == table.lower() and d.composite_pk_part
        ]
        return [c for _, c in sorted(parts)]

    def primary_key(self, table: str) -> ColumnDoc | None:
        for (t, _), d in self.columns.items():
            if t == table.lower() and d.declares_pk and not d.composite_pk_part:
                return d
        return None


def parse_corpus(
    grep_results: Any,
    titles: Mapping[str, str],
    default_tables: Mapping[str, str],
    known_columns: Mapping[str, set[str]],
) -> DocumentFacts:
    """Turn interleaved headings and table rows back into per-column facts.

    `grep_documents` returns excerpts with positions rather than whole files, so
    document order is recovered by sorting on position. A row belongs to the
    table named by the nearest preceding `###` heading, falling back to the table
    the document itself is about.
    """
    facts = DocumentFacts()
    results = (grep_results or {}).get("results") or []
    facts.documents_read = len(results)

    for doc in results:
        urn = doc.get("urn", "")
        title = titles.get(urn) or doc.get("title") or urn
        table = default_tables.get(urn)
        section = ""
        found_here = False

        matches = sorted(doc.get("matches") or [], key=lambda m: m.get("position", 0))
        for m in matches:
            line = (m.get("excerpt") or "").strip()
            # context_chars=0 still brackets the match with ellipses.
            line = line.strip(". ") if line.startswith("...") else line
            line = line.lstrip(".").strip()

            head = _HEADING.match(line)
            if head:
                level, text = head.group(1), head.group(2)
                if level == "###":
                    # "### regions / countries" documents two tables at once.
                    named = [
                        p.strip().lower()
                        for p in re.split(r"[/,]| and ", text)
                        if p.strip().lower() in known_columns
                    ]
                    table = named[0] if len(named) == 1 else (named[0] if named else table)
                    if len(named) > 1:
                        # Ambiguous scope — a row could belong to either table.
                        # Refuse rather than attribute it to the wrong one.
                        table = None
                section = text.lower()
                continue

            row = _ROW.match(line)
            if not row or not table:
                continue
            first, rest = row.group(1).strip(), row.group(2).strip().rstrip("|").strip()
            cols = known_columns.get(table, set())

            if first.lower() in cols and (
                section in _COLUMN_SECTIONS or not section or first.lower() in cols
            ):
                facts.columns[(table, first.lower())] = ColumnDoc(
                    table=table, column=first.lower(), text=rest,
                    doc_urn=urn, doc_title=title,
                )
                facts.rows_parsed += 1
                found_here = True
                continue

            # Not a column of this table — it may be a row of a value table,
            # e.g. "## Order Status Lifecycle" listing the legal statuses.
            target = _section_column(section, cols)
            if target:
                vals, _ = facts.value_tables.get((table, target), ([], title))
                if first not in vals:
                    vals = vals + [first]
                facts.value_tables[(table, target)] = (vals, title)
                facts.rows_parsed += 1
                found_here = True

        if found_here:
            facts.documents_with_columns += 1

    # A one-row "value table" is a formatting accident, not an enumeration.
    facts.value_tables = {k: v for k, v in facts.value_tables.items() if len(v[0]) >= 2}
    return facts
