# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "mcp[cli]>=1.27,<2",
#     "openpyxl>=3.1.0",
# ]
# ///
"""
Dummy SSE MCP server for testing Arcanna's tool-result formatting feature (SAI-7344).

How the pipeline works (so the tools below make sense):

  1. This server returns a *string* per tool. To declare a format, the string is
     JSON of the shape {"__arcanna_format": "<csv|json|text>", "content": "..."}.
  2. aiops-rest-api (mcp_client_tool_call_service.unwrap_content_format) unwraps
     that marker into a content item: {"type": "text", "text": "...", "format": "csv"}.
  3. The UI (ToolResultContent.renderByFormat) dispatches on `format`:
       csv  -> CsvTableRenderer (blank-line separated CSV blocks -> <table>)
       json -> StructuredToolResult -> StructuredDataRenderer, but ONLY if
               "Structured Result Rendering" is toggled ON for that tool in
               Settings > MCP Tools > <tool> > options. Otherwise raw JSON block.
       else -> plain text, with CSV auto-detection as a fallback.
  4. Tools returning an unmarked string still get auto-detected (JSON first, then CSV).

Tool naming: json_* / csv_* / text_* / raw_* / misc_* so you can find them fast.
"""

import asyncio
import base64
import io
import json
import os
import random
from typing import Any

from mcp.server import FastMCP
from mcp.server.fastmcp import Image

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "10500"))
TRANSPORT = os.getenv("TRANSPORT_MODE", "sse")

mcp = FastMCP("format-test-mcp-server", host=HOST, port=PORT)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #

def marked(content: str, fmt: str) -> str:
    """Wrap content with the __arcanna_format marker the REST API unwraps."""
    return json.dumps({"__arcanna_format": fmt, "content": content}, ensure_ascii=False)


def as_json(data: Any) -> str:
    return marked(json.dumps(data, ensure_ascii=False, indent=2, default=str), "json")


def as_csv(content: str) -> str:
    return marked(content, "csv")


def as_text(content: str) -> str:
    return marked(content, "text")


def csv_rows(header: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        if value is None:
            text = ""
        elif isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        if any(ch in text for ch in ',"\n'):
            return '"' + text.replace('"', '""') + '"'
        return text

    lines = [",".join(cell(c) for c in header)]
    lines += [",".join(cell(c) for c in row) for row in rows]
    return "\n".join(lines)


SEVERITIES = ["critical", "high", "medium", "low"]
HOSTS = ["srv-web-01", "srv-db-02", "srv-cache-03", "fw-edge-01", "k8s-node-07"]


def alert(index: int) -> dict[str, Any]:
    random.seed(index)
    return {
        "alert_id": f"ALR-{1000 + index}",
        "title": f"Suspicious authentication burst on {HOSTS[index % len(HOSTS)]}",
        "severity": SEVERITIES[index % len(SEVERITIES)],
        "score": round(random.uniform(0.1, 0.99), 3),
        "host": HOSTS[index % len(HOSTS)],
        "source_ip": f"10.20.{index % 255}.{(index * 7) % 255}",
        "detected_at": f"2026-08-{(index % 28) + 1:02d}T{index % 24:02d}:15:00Z",
        "acknowledged": index % 3 == 0,
        "assignee": None if index % 4 == 0 else f"analyst{index % 5}@siscale.com",
        "tags": ["auth", "brute-force", f"wave-{index % 3}"],
    }


# --------------------------------------------------------------------------- #
# JSON  ->  StructuredDataRenderer paths
# --------------------------------------------------------------------------- #

@mcp.tool()
async def json_flat_object() -> str:
    """Flat JSON object of primitives only. Renders as a KeyValueRows grid."""
    return as_json(
        {
            "alert_id": "ALR-1042",
            "title": "Suspicious authentication burst on srv-web-01",
            "severity": "critical",
            "score": 0.973,
            "acknowledged": False,
            "assignee": None,
            "detected_at": "2026-08-19T11:15:00Z",
            "description": "Multi-line value.\nSecond line, to check whitespace: pre-wrap.\nThird line.",
        }
    )


@mcp.tool()
async def json_table_of_objects(rows: int = 8) -> str:
    """Homogeneous list of objects -> StructuredTable (a real <table>)."""
    return as_json([alert(i) for i in range(max(1, min(rows, 500)))])


@mcp.tool()
async def json_large_table() -> str:
    """200-row table. Checks the 360px maxHeight scroll container and perf."""
    return as_json([alert(i) for i in range(200)])


@mcp.tool()
async def json_table_with_nested_cells() -> str:
    """Table whose cells hold objects/arrays -> NestedValue collapsibles inside <td>,
    with per-row expand syncing across columns."""
    return as_json(
        [
            {
                "alert_id": f"ALR-{2000 + i}",
                "severity": SEVERITIES[i % len(SEVERITIES)],
                "enrichment": {
                    "geo": {"country": "RO", "city": "Bucharest", "asn": 8708 + i},
                    "reputation": {"score": 12 + i, "vendor": "acme-ti", "malicious": i % 2 == 0},
                },
                "observables": [
                    {"type": "ip", "value": f"10.20.30.{i}"},
                    {"type": "user", "value": f"svc_account_{i}"},
                ],
                "tags": ["auth", "lateral-movement"],
            }
            for i in range(5)
        ]
    )


@mcp.tool()
async def json_envelope_list() -> str:
    """Elasticsearch-style [{"_source": {...}}, ...] -> exercises
    unwrapHomogeneousEnvelopes, which should strip the _source wrapper."""
    return as_json([{"_source": alert(i)} for i in range(6)])


@mcp.tool()
async def json_single_property_chain() -> str:
    """{"result": {"data": {"items": [...]}}} -> exercises flattenSinglePropertyPath,
    which should collapse the chain into one 'result.data.items' heading."""
    return as_json({"result": {"data": {"items": [alert(i) for i in range(4)]}}})


@mcp.tool()
async def json_mixed_object() -> str:
    """Primitives + nested object + list of objects + list of primitives in one object.
    The primitives go to a KeyValueRows grid, the rest to sibling collapsibles."""
    return as_json(
        {
            "job_title": "Phishing Triage",
            "job_id": 42,
            "enabled": True,
            "last_run": "2026-08-19T09:00:00Z",
            "processed_events": 128934,
            "labels": ["escalate", "dismiss", "monitor"],
            "config": {
                "retrain_interval_minutes": 60,
                "consensus": {"required_votes": 2, "auto_close": False},
            },
            "recent_alerts": [alert(i) for i in range(3)],
            "metrics": {
                "accuracy": 0.912,
                "buckets": [
                    {"label": "escalate", "count": 412},
                    {"label": "dismiss", "count": 8801},
                ],
            },
        }
    )


@mcp.tool()
async def json_mixed_array() -> str:
    """Array with mixed member types (not all objects) -> 'Item N' collapsibles
    instead of a table."""
    return as_json(
        [
            "a bare string member",
            42,
            True,
            None,
            {"kind": "object", "nested": {"a": 1}},
            [1, 2, 3],
        ]
    )


@mcp.tool()
async def json_deeply_nested(depth: int = 12) -> str:
    """Nesting deeper than Max Depth (default 8) -> the tail should fall back to a raw
    JSON code block. Set Max Depth in the tool options to see the cut move."""
    depth = max(1, min(depth, 40))
    node: Any = {"leaf": "bottom reached", "depth": depth}
    for level in range(depth, 0, -1):
        node = {f"level_{level}": node, "note": f"payload at level {level}"}
    return as_json(node)


@mcp.tool()
async def json_noisy_keys() -> str:
    """Contains raw_payload / _internal_id / embedding / debug_trace so you can test
    the 'Ignored Keys' setting. Try: raw_payload, _internal_id, embedding, debug_trace"""
    return as_json(
        {
            "alert_id": "ALR-9001",
            "severity": "high",
            "_internal_id": "d3f1c0de-0000-4000-8000-000000000001",
            "raw_payload": "<27>Aug 19 11:15:00 srv-web-01 sshd[2311]: Failed password for invalid user root",
            "embedding": [round(random.Random(i).uniform(-1, 1), 4) for i in range(16)],
            "debug_trace": {"stage": "enrich", "took_ms": 143, "cache_hit": False},
            "enrichment": {
                "geo": {"country": "RO", "city": "Bucharest"},
                "_internal_id": "nested-one-should-vanish-too",
                "raw_payload": "nested raw payload",
            },
            "observables": [
                {"type": "ip", "value": "10.20.30.40", "_internal_id": "obs-1"},
                {"type": "user", "value": "root", "_internal_id": "obs-2"},
            ],
        }
    )


@mcp.tool()
async def json_edge_cases() -> str:
    """Empty list, empty object, nulls, booleans, zero, negative, huge number,
    long unbroken string, unicode, and a nested empty structure."""
    return as_json(
        {
            "empty_list": [],
            "empty_object": {},
            "null_value": None,
            "false_value": False,
            "zero": 0,
            "negative": -273.15,
            "huge_number": 9007199254740993,
            "long_token": "A" * 220,
            "unicode": "diacritice: ăîâșț — emoji: 🚨🔥 — cjk: 監視",
            "quotes_and_html": '<b>bold</b> & "quoted" \'single\' <script>alert(1)</script>',
            "list_of_empty_objects": [{}, {}, {}],
            "nested_empty": {"a": {"b": {"c": []}}},
        }
    )


@mcp.tool()
async def json_array_of_primitives() -> str:
    """Top-level array of primitives -> joined into a single comma-separated line."""
    return as_json(["escalate", "dismiss", "monitor", "investigate", None, 7, True])


@mcp.tool()
async def json_ragged_objects() -> str:
    """Objects with differing key sets -> table columns are the union, missing cells
    should show the em-dash placeholder."""
    return as_json(
        [
            {"id": 1, "name": "first", "only_here": "yes"},
            {"id": 2, "extra_field": 99},
            {"id": 3, "name": "third", "another": {"deep": True}},
        ]
    )


# --------------------------------------------------------------------------- #
# CSV  ->  CsvTableRenderer paths
# --------------------------------------------------------------------------- #

@mcp.tool()
async def csv_simple(rows: int = 10) -> str:
    """Plain CSV, header + rows. Renders as a single markdown-styled table."""
    rows = max(1, min(rows, 500))
    data = [alert(i) for i in range(rows)]
    header = ["alert_id", "title", "severity", "score", "host", "detected_at"]
    return as_csv(csv_rows(header, [[a[k] for k in header] for a in data]))


@mcp.tool()
async def csv_with_metadata() -> str:
    """sts-mcp-server shape: a 'key: value | key: value' metadata line, blank line,
    then the CSV. The metadata block renders as text, the CSV as a table."""
    data = [alert(i) for i in range(6)]
    header = ["alert_id", "severity", "host", "source_ip", "acknowledged"]
    meta = "total: 6 | took_ms: 42 | index: arcanna-alerts-2026.08 | truncated: false"
    return as_csv(f"{meta}\n\n{csv_rows(header, [[a[k] for k in header] for a in data])}")


@mcp.tool()
async def csv_multi_sheet() -> str:
    """Several blank-line-separated CSV blocks — the closest thing this pipeline has to
    a multi-sheet Excel export. Should render as several stacked tables."""
    sheet1 = csv_rows(
        ["host", "status", "cpu_pct", "mem_pct"],
        [[h, "up" if i % 3 else "down", 12 + i * 7, 40 + i * 3] for i, h in enumerate(HOSTS)],
    )
    sheet2 = csv_rows(
        ["severity", "count", "pct"],
        [["critical", 12, "4.1%"], ["high", 63, "21.4%"], ["medium", 140, "47.6%"], ["low", 79, "26.9%"]],
    )
    sheet3 = csv_rows(
        ["analyst", "assigned", "closed", "avg_minutes"],
        [[f"analyst{i}@siscale.com", 20 + i, 15 + i, round(11.5 + i, 1)] for i in range(4)],
    )
    return as_csv(
        "sheet: hosts\n\n" + sheet1 + "\n\nsheet: severity_breakdown\n\n" + sheet2 + "\n\nsheet: analyst_load\n\n" + sheet3
    )


@mcp.tool()
async def csv_quoted_messy() -> str:
    """CSV with quoted fields containing commas, embedded newlines, escaped quotes and
    empty cells — checks the papaparse path rather than a naive split."""
    return as_csv(
        'alert_id,message,tags,note\n'
        'ALR-1,"Failed password for user ""root"", 5 times","auth,brute-force",\n'
        'ALR-2,"Multi-line\nmessage body\nthird line",recon,"trailing, comma"\n'
        'ALR-3,,,"only note"\n'
    )


@mcp.tool()
async def csv_ragged_invalid() -> str:
    """Inconsistent column counts -> parseCSVBlock rejects it and it should degrade to
    plain preformatted text instead of a broken table."""
    return as_csv("a,b,c\n1,2,3\n4,5\n6,7,8,9\n")


@mcp.tool()
async def csv_single_column() -> str:
    """Single-column CSV -> rejected as a table (needs >= 2 columns), renders as text."""
    return as_csv("hostname\nsrv-web-01\nsrv-db-02\nsrv-cache-03\n")


@mcp.tool()
async def csv_header_only() -> str:
    """Header with no data rows -> rejected as a table (needs >= 2 lines)."""
    return as_csv("alert_id,severity,host\n")


@mcp.tool()
async def csv_wide(columns: int = 24) -> str:
    """Many columns -> checks horizontal scrolling of the table wrapper."""
    columns = max(2, min(columns, 100))
    header = [f"col_{i:02d}" for i in range(columns)]
    rows = [[f"r{r}c{c}" for c in range(columns)] for r in range(8)]
    return as_csv(csv_rows(header, rows))


# --------------------------------------------------------------------------- #
# TEXT
# --------------------------------------------------------------------------- #

@mcp.tool()
async def text_plain() -> str:
    """Short plain text. Should render in a txt code block, no table, no JSON."""
    return as_text(
        "Triage complete. 6 alerts reviewed, 2 escalated, 4 dismissed.\n"
        "No action required from the analyst at this point."
    )


@mcp.tool()
async def text_long_report() -> str:
    """Long multi-paragraph text with a bulleted list — checks height/scroll clamping."""
    para = (
        "The detection pipeline correlated the authentication failures with a prior "
        "reconnaissance burst originating from the same autonomous system. Confidence "
        "is high but the source has no history in the threat intel feeds."
    )
    bullets = "\n".join(f"  - finding {i}: {para[:60]}..." for i in range(1, 9))
    return as_text("\n\n".join([f"Incident report INC-4471\n{'=' * 40}", para, bullets, para, para]))


@mcp.tool()
async def text_markdown() -> str:
    """Markdown-flavoured text, including a pipe table and a fenced code block, sent
    with format=text — checks whether markdown is rendered or shown literally."""
    return as_text(
        "# Incident INC-4471\n\n"
        "**Severity:** critical  \n"
        "**Status:** _open_\n\n"
        "| host | status | score |\n"
        "| --- | --- | --- |\n"
        "| srv-web-01 | down | 0.97 |\n"
        "| srv-db-02 | up | 0.41 |\n\n"
        "```bash\ngrep 'Failed password' /var/log/auth.log | tail -20\n```\n\n"
        "See [the runbook](https://example.invalid/runbook) or mail soc@example.invalid.\n"
    )


@mcp.tool()
async def text_containing_csv() -> str:
    """format=text but the body is really CSV -> exercises renderText's CSV
    auto-detection fallback (it should still become a table)."""
    return as_text(csv_rows(["host", "status", "cpu_pct"], [[h, "up", 20 + i] for i, h in enumerate(HOSTS)]))


@mcp.tool()
async def text_containing_json() -> str:
    """format=text but the body is really JSON -> renderText should notice and route it
    to the structured/JSON renderer."""
    return as_text(json.dumps({"alerts": [alert(i) for i in range(3)]}, indent=2))


@mcp.tool()
async def text_empty() -> str:
    """Empty string result — checks the 'no content' / blank-render edge case."""
    return as_text("")


# --------------------------------------------------------------------------- #
# UNMARKED  ->  auto-detection only, no __arcanna_format
# --------------------------------------------------------------------------- #

@mcp.tool()
async def raw_json_unmarked() -> str:
    """Bare JSON string with NO format marker. Only the UI's tryParseJsonValue
    auto-detection applies."""
    return json.dumps({"alerts": [alert(i) for i in range(4)], "total": 4}, indent=2)


@mcp.tool()
async def raw_csv_unmarked() -> str:
    """Bare CSV with NO format marker -> must be caught by CSV auto-detection."""
    return csv_rows(["alert_id", "severity", "host"], [[alert(i)[k] for k in ("alert_id", "severity", "host")] for i in range(5)])


@mcp.tool()
async def raw_text_unmarked() -> str:
    """Bare plain text with NO format marker -> plain txt code block."""
    return "Nothing structured here. Just a sentence the model has to read."


@mcp.tool()
async def raw_dict_return() -> dict:
    """Returns a dict rather than a string, so FastMCP serialises it itself (and may
    also attach structuredContent). Checks the un-marked object path end to end."""
    return {"alerts": [alert(i) for i in range(3)], "total": 3, "took_ms": 17}


@mcp.tool()
async def raw_list_return() -> list:
    """Returns a list rather than a string — same idea as raw_dict_return."""
    return [alert(i) for i in range(4)]


@mcp.tool()
async def raw_marker_malformed() -> str:
    """Marker present but `content` is an object instead of a string — checks that the
    REST API unwrapper and the UI both survive a malformed marker."""
    return json.dumps({"__arcanna_format": "json", "content": {"not": "a string"}})


@mcp.tool()
async def raw_marker_unknown_format() -> str:
    """Marker with an unrecognised format value ('xml') -> should fall through to the
    text renderer rather than blow up."""
    return marked("<alerts><alert id='1' severity='high'/></alerts>", "xml")


# --------------------------------------------------------------------------- #
# MISC  ->  images, multi-part content, binary, errors, slow calls
# --------------------------------------------------------------------------- #

@mcp.tool()
async def misc_image() -> Image:
    """Returns an image content item -> the UI's `type === 'image'` branch."""
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAV0lEQVR4nO3OsQ3AIAxA0e9U2Z"
        "T9M0AmYAOyAdmAbEA2IBuQDcgGZAOyAdmAbEA2IBuQDcgGZAOyAdmAbEA2IBuQDcgGZAOyAdmA"
        "bEA2IBuQDfgAvS8B0QAAAABJRU5ErkJggg=="
    )
    return Image(data=png, format="png")


@mcp.tool()
async def misc_multi_content():
    """Three content items in one result (text + csv + json), each with its own marker.
    Note: the drawer only honours `format` when there is exactly ONE item, so this also
    shows the single-item shortcut vs. the map-over-content path."""
    from mcp.types import TextContent

    return [
        TextContent(type="text", text=as_text("Summary: 5 hosts checked, 2 degraded.")),
        TextContent(type="text", text=as_csv(csv_rows(["host", "status"], [[h, "up" if i % 2 else "degraded"] for i, h in enumerate(HOSTS)]))),
        TextContent(type="text", text=as_json({"degraded": ["srv-web-01", "srv-cache-03"], "checked": 5})),
    ]


@mcp.tool()
async def misc_xlsx_base64() -> str:
    """A real .xlsx returned as base64 text. Nothing in the pipeline renders spreadsheets,
    so this is the 'unsupported binary payload' case — expect base64 in a text block."""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "alerts"
    sheet.append(["alert_id", "severity", "host", "score"])
    for i in range(10):
        row = alert(i)
        sheet.append([row["alert_id"], row["severity"], row["host"], row["score"]])
    second = workbook.create_sheet("summary")
    second.append(["severity", "count"])
    for severity in SEVERITIES:
        second.append([severity, sum(1 for i in range(10) if alert(i)["severity"] == severity)])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return as_text(base64.b64encode(buffer.getvalue()).decode())


@mcp.tool()
async def misc_slow(seconds: int = 8) -> str:
    """Sleeps before answering, so you can watch the 'Tool is running' state."""
    await asyncio.sleep(max(0, min(seconds, 60)))
    return as_text(f"Finished after {seconds}s.")


@mcp.tool()
async def misc_error() -> str:
    """Always raises, to exercise the error branch of the result renderer."""
    raise RuntimeError("Simulated tool failure: upstream returned HTTP 503 after 3 retries.")


@mcp.tool()
async def misc_huge_json(rows: int = 1200) -> str:
    """A deliberately big JSON payload, to check rendering cost and truncation."""
    return as_json({"total": rows, "alerts": [alert(i) for i in range(max(1, min(rows, 5000)))]})


if __name__ == "__main__":
    print(f"format-test-mcp-server on http://{HOST}:{PORT}/sse (transport={TRANSPORT})")
    mcp.run(transport=TRANSPORT)
