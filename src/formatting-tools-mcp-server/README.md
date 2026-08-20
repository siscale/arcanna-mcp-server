# format-test-mcp-server

Dummy **SSE** MCP server with 40 tools that return every output shape the
SAI-7344 tool-result formatting feature can render. Zero external services, no
credentials, one file.

## Run

```bash
cd ~/arcanna/format-test-mcp-server
HOST=0.0.0.0 uv run server.py     # required: the mcp-client container must reach it
uv run server.py                  # 127.0.0.1 only -- host-side testing/curl
```

`HOST=0.0.0.0` is not optional in this setup. The `mcp-client` container is on the
default `bridge` network, so `127.0.0.1` in its config is *its own* loopback and the
URL check fails with `TypeError: fetch failed`.

`uv` resolves the inline PEP 723 dependencies (`mcp[cli]>=1.27,<2`, `openpyxl`) on
first run — no venv to manage. `mcp` is pinned to 1.x because 2.0 renamed `FastMCP`.

## Register it

The client auto-detects transport from the URL suffix, so the `/sse` ending matters.
Add to `aiops-mcp-client/mcp_config.json` (or the platform's MCP config UI):

```json
"format_test": {
  "url": "http://172.17.0.1:10500/sse",
  "options": { "timeout_ms": 120000 }
}
```

`172.17.0.1` is the docker bridge gateway — the host as seen from the container.
Confirm it for your setup with:

```bash
docker inspect mcp-client --format '{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}'
docker exec mcp-client curl -sS -m 3 -N http://172.17.0.1:10500/sse | head -2
```

The second command should print an `event: endpoint` line. **`host.docker.internal`
does not work here** — the container has no `extra_hosts` entry for it, which is the
usual Linux default, so the name simply does not resolve.

## How the format actually travels

1. Each tool returns a **string**. To declare a format it returns JSON of the shape
   `{"__arcanna_format": "csv"|"json"|"text", "content": "..."}`.
2. `aiops-rest-api` — `mcp_client_tool_call_service.unwrap_content_format` — turns
   that into a content item `{"type": "text", "text": "...", "format": "csv"}`.
3. The UI — `ToolResultContent.renderByFormat` — dispatches on `format`:
   - `csv` → `CsvTableRenderer`: splits on blank lines, each block that parses with
     ≥2 rows and ≥2 consistent columns becomes a `<table>`; the rest stays text.
   - `json` → `StructuredToolResult` → `StructuredDataRenderer`, **but only if
     "Structured Result Rendering" is ON for that tool**. Otherwise a raw JSON block.
   - anything else → text, with JSON then CSV auto-detection as fallbacks.
4. Tools with no marker still go through the UI's auto-detection.

**Per-tool settings** live in Settings → MCP Tools → *tool* → options:
*Structured Result Rendering* (toggle), *Ignored Keys* (comma-separated, stripped at
every depth), *Max Depth* (default 8, then it falls back to a raw JSON block).

## Tools by what they exercise

### JSON → `StructuredDataRenderer`
Turn *Structured Result Rendering* **on** for these, and compare against **off**.

| tool | exercises |
| --- | --- |
| `json_flat_object` | `KeyValueRows` grid; multi-line string with `pre-wrap` |
| `json_table_of_objects(rows=8)` | `StructuredTable` — the happy-path `<table>` |
| `json_large_table` | 200 rows → 360px `maxHeight` scroll + render cost |
| `json_table_with_nested_cells` | `NestedValue` collapsibles inside `<td>`, per-row expand sync across columns |
| `json_envelope_list` | `unwrapHomogeneousEnvelopes` strips the ES `_source` wrapper |
| `json_single_property_chain` | `flattenSinglePropertyPath` collapses `result.data.items` into one heading |
| `json_mixed_object` | primitives → grid, complex siblings → collapsibles, `expandPrimitiveObjectFields` |
| `json_mixed_array` | non-homogeneous array → `Item N` collapsibles, no table |
| `json_deeply_nested(depth=12)` | past *Max Depth* → raw JSON fallback. Change Max Depth and watch the cut move |
| `json_noisy_keys` | *Ignored Keys*. Try `raw_payload, _internal_id, embedding, debug_trace` — nested and in-array occurrences must go too |
| `json_edge_cases` | empty list/object, `null` → `—`, `false`, `0`, 220-char unbroken token, unicode, HTML-ish string |
| `json_array_of_primitives` | primitive array joined to one comma-separated line |
| `json_ragged_objects` | differing key sets → union columns, `—` for missing cells |
| `misc_huge_json(rows=1200)` | ~490 KB payload — perf and truncation |

### CSV → `CsvTableRenderer`
| tool | exercises |
| --- | --- |
| `csv_simple(rows=10)` | plain header + rows table |
| `csv_with_metadata` | the sts-mcp-server shape: metadata line, blank line, CSV → text block + table |
| `csv_multi_sheet` | three blank-line-separated blocks → stacked tables. This is the closest thing the pipeline has to a multi-sheet Excel export |
| `csv_quoted_messy` | quoted commas, embedded newlines, `""` escapes, empty cells — the papaparse path |
| `csv_ragged_invalid` | inconsistent column counts → rejected, degrades to preformatted text |
| `csv_single_column` | <2 columns → rejected as a table |
| `csv_header_only` | <2 rows → rejected as a table |
| `csv_wide(columns=24)` | horizontal scroll of the table wrapper |

### Text
| tool | exercises |
| --- | --- |
| `text_plain` | short `txt` code block |
| `text_long_report` | long multi-paragraph body → height/scroll clamping |
| `text_markdown` | markdown incl. a pipe table and fenced code, sent as `text` — is it rendered or literal? |
| `text_containing_csv` | `format=text` but the body is CSV → `renderText` CSV auto-detection should still table it |
| `text_containing_json` | `format=text` but the body is JSON → should route to the structured/JSON renderer |
| `text_empty` | empty string result |

### No marker — auto-detection only
| tool | exercises |
| --- | --- |
| `raw_json_unmarked` | `tryParseJsonValue` auto-detection with no `format` |
| `raw_csv_unmarked` | CSV auto-detection with no `format` |
| `raw_text_unmarked` | plain text, no `format` |
| `raw_dict_return` | tool returns a `dict`, so FastMCP serialises it (and attaches `structuredContent`) |
| `raw_list_return` | tool returns a `list` — FastMCP emits **one content item per element** (4 items), so the single-item `format` shortcut in the drawer does not apply |
| `raw_marker_malformed` | marker present but `content` is an object, not a string — both the unwrapper and the UI must survive it |
| `raw_marker_unknown_format` | `__arcanna_format: "xml"` → unrecognised value must fall through to text, not blow up |

### Misc
| tool | exercises |
| --- | --- |
| `misc_image` | `type === 'image'` branch (base64 PNG) |
| `misc_multi_content` | three content items with different formats in one result — note the drawer only honours `format` when there is exactly **one** item |
| `misc_xlsx_base64` | a real `.xlsx` as base64. Nothing in the pipeline renders spreadsheets, so this is the unsupported-binary case |
| `misc_slow(seconds=8)` | the "Tool is running" state |
| `misc_error` | the error branch of the result renderer |

## Known gap

There is **no `excel`/`xlsx` format in this feature** — `renderByFormat` only knows
`csv` and `json`, everything else is text. `csv_multi_sheet` is the spreadsheet-shaped
test case; `misc_xlsx_base64` shows what a real binary workbook currently degrades to.
