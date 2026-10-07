# Arcanna MCP Server

The Arcanna MCP server allows user to interact with Arcanna's AI use cases through the Model Context Protocol (MCP).

## Usage with Claude Desktop or other MCP Clients

#### Configuration
Add the following entry to the `mcpServers` section in your MCP client config file (`claude_desktop_config.json` for Claude
Desktop).

### Use docker image (https://hub.docker.com/r/arcanna/arcanna-mcp-server) or PyPi package (https://pypi.org/project/arcanna-mcp-server/)

### Building local image from this repository
#### Prerequisites
- Docker - https://docs.docker.com/engine/install/

#### Configuration
1. Change directory to the directory where the Dockerfile is.
2. Run ```docker build -t arcanna/arcanna-mcp-server . --progress=plain --no-cache```
3. Add the configuration bellow to your claude desktop/mcp client config.

```json
{
  "mcpServers": {
    "arcanna-mcp-server": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "ARCANNA_MANAGEMENT_API_KEY",
        "-e",
        "ARCANNA_HOST",
        "arcanna/arcanna-mcp-server"
      ],
      "env": {
        "ARCANNA_MANAGEMENT_API_KEY": "<ARCANNA_MANAGEMENT_API_KEY>",
        "ARCANNA_HOST": "<YOUR_ARCANNA_HOST_HERE>"
      }
    }
  }
}
```

## Servers

One package, three MCP servers. Install once; each executable is a separate server, so a client attaches only
what it needs. All three use the same environment (`ARCANNA_HOST`, `ARCANNA_MANAGEMENT_API_KEY`, optional
`ARCANNA_AGENTS_HOST`, `TRANSPORT_MODE=stdio|sse`, `PORT` for sse). Tools are filtered by the API key's scopes.

| Executable | MCP name | Covers |
|---|---|---|
| `arcanna-mcp-server` | `arcanna` | Jobs, integrations, events, feedback, buckets, metrics, IaC, roles, platform, code blocks |
| `arcanna-agents-mcp` | `arcanna-agents` | Agentic workflows: create, update, run, human-in-the-loop sessions |
| `arcanna-rag-mcp` | `arcanna-rag` | RAG documents, collections and tags |

Docker: the image's entrypoint is `arcanna-mcp-server`; run another server with e.g.
`docker run -i --rm --entrypoint arcanna-agents-mcp -e ARCANNA_HOST -e ARCANNA_MANAGEMENT_API_KEY arcanna/arcanna-mcp-server`.

## Tools

### arcanna-mcp-server
- **jobs**: `start_job`, `stop_job`, `train_job`, `get_job_status`, `get_job_input_state`, `reset_job_input_state`, `submit_training_config_validation`, `get_training_config_validation`, `list_training_config_validations`, `cancel_training_config_validation`
- **resources**: `search_integrations`, `get_integration_details`, `search_jobs`, `get_job_details`, `list_integration_types`, `get_integration_type_metadata`, `get_job_category_metadata`, `create_integration`, `update_integration`, `delete_integration`, `create_job`, `update_job`, `delete_job`, `check_integration_health`, `list_llm_models`, `get_job_decision_points`, `apply_iac`, `export_iac`, `get_roles`, `upsert_roles`, `delete_roles`
- **events**: `query_arcanna_events`, `count_events`, `get_field_stats`, `get_field_groups`, `get_filter_fields`, `get_fields_mapping`, `get_event_explanation`, `get_similar_events`, `get_event_agentic_workflows`, `get_job_outliers`, `add_feedback_to_event`, `clear_event_feedback`, `add_agentic_notes`, `reprocess_events`, `reprocess_event_by_id`, `delete_events`, `ingest_event`, `export_event_by_id`, `transfer_event`
- **buckets**: `query_buckets`, `get_bucket`, `get_similar_buckets`, `reprocess_buckets`, `request_bucket_model_update`, `request_bucket_model_update_by_filters`, `approve_bucket_feedback`, `update_bucket_feedback_state`, `delete_buckets`
- **metrics**: `get_job_metrics`, `get_job_and_model_metrics`, `get_model_metrics`, `request_model_metrics_recompute`, `get_platform_metrics`, `get_internal_metrics`, `get_field_metrics`, `export_feedback`, `set_production_date`
- **platform**: `health_check`, `get_platform_info`, `get_system_timestamp`, `delete_storage_data`
- **code_blocks**: `generate_code_instructions`, `execute_code`, `execute_code_async`, `save_code`

### arcanna-agents-mcp
- **workflows**: `list_agentic_workflows`, `get_agentic_workflow_by_id`, `create_agentic_workflow`, `update_agentic_workflow`, `run_agentic_workflow`, `test_agentic_workflow`, `list_agent_tools`, `list_llm_providers`, `get_workflow_session`, `answer_workflow_decision`, `continue_workflow_session`, `stop_workflow_sessions`

### arcanna-rag-mcp
- **documents**: `query_rag_documents`, `get_rag_document`, `upload_rag_documents`, `update_rag_document`, `delete_rag_document`, `approve_rag_document`, `reject_rag_document`, `retry_rag_document`, `get_rag_pipeline_status`
- **collections**: `query_rag_collections`, `create_rag_collection`, `update_rag_collection`, `delete_rag_collection`, `create_rag_subcollection`, `update_rag_subcollection`, `delete_rag_subcollection`, `list_rag_tags`

## Breaking changes in 0.2.0

The single server was split into three and tools were renamed or replaced. Tool names referenced in roles,
assistant tool settings or agentic workflows must be updated by hand:

| Removed / renamed | Use instead |
|---|---|
| `upsert_resources` | `create_integration / update_integration / create_job / update_job` |
| `get_resources` | `search_integrations / search_jobs / get_integration_details / get_job_details` |
| `delete_resources` | `delete_integration / delete_job` |
| `integration_parameters_schema` | `get_integration_type_metadata` |
| `setup_integration` | `create_integration` |
| `setup_job` | `create_job` |
| `metrics_job` | `get_job_metrics` |
| `metrics_job_and_latest_model` | `get_job_and_model_metrics` |
| `metrics_model` | `get_model_metrics` |
| `metrics_model_request_recompute_metrics` | `request_model_metrics_recompute` |
| `agents_tool_discovery` | `list_agent_tools` |
| `get_llm_integrations` | `list_llm_providers` |

Agentic tools moved from the `arcanna` server to `arcanna-agents`. `execute_code` now runs a saved code
block integration on a stored event (the inline test endpoint no longer exists); `save_code` saves through IaC.

## Development

```
venv/bin/uv sync
.venv/bin/python -m pytest -q tests
.venv/bin/python -m pyright src
```

Tools are generated from the Arcanna OpenAPI specs, then trimmed by hand:

1. Refresh the specs from a modular-framework checkout (see `scripts/dump_specs.py`).
2. Map the tool in `scripts/tool_map.py` (server, module, operationId, scopes).
3. `.venv/bin/python scripts/gen_tools.py` appends a stub to the module; add it to `export_tools()` and trim
   the docstring to: what it does, when to use it vs its neighbour, response shape, cost, and what not to use
   it for. `tests/test_tools.py` checks mapping, scopes, descriptions, docstring length and the called endpoint.
