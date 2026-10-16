import asyncio
import inspect
import json
import os
import re
import typing
from unittest.mock import AsyncMock, patch

import pytest
from mcp.server.fastmcp.tools.base import Tool

from arcanna_mcp_server.agents.tools import MODULES as AGENT_MODULES
from arcanna_mcp_server.common.runner import all_tools
from arcanna_mcp_server.core.tools import MODULES as CORE_MODULES
from arcanna_mcp_server.rag.tools import MODULES as RAG_MODULES
from tool_map import DEPRECATED, TOOLS

SERVERS = {"core": CORE_MODULES, "agents": AGENT_MODULES, "rag": RAG_MODULES}
DOCSTRING_BUDGET = 700
SPECS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "specs")


def _load_spec(service):
    with open(os.path.join(SPECS_DIR, f"{service}.json")) as spec_file:
        return json.load(spec_file)


SPECS = {"exposer": _load_spec("exposer"), "agents": _load_spec("agents")}


def _operations(service):
    return {op["operationId"]: (method.upper(), path, op)
            for path, ops in SPECS[service]["paths"].items() for method, op in ops.items()}


OPERATIONS = {service: _operations(service) for service in SPECS}
EXPORTED = [(server, module, tool) for server, modules in SERVERS.items()
            for module in modules for tool in module.export_tools()]
BY_NAME = {tool.__name__: (server, module, tool) for server, module, tool in EXPORTED}


def test_every_exported_tool_is_in_the_tool_map_under_its_server_and_module():
    # given / when
    misplaced = [f"{server}/{module.__name__}.{tool.__name__}" for server, module, tool in EXPORTED
                 if TOOLS.get(tool.__name__, {}).get("server") != server
                 or not module.__name__.endswith("." + TOOLS[tool.__name__]["module"])]

    # then
    assert misplaced == []


def test_every_mapped_tool_is_exported():
    # given / when
    missing = sorted(set(TOOLS) - set(BY_NAME))

    # then
    assert missing == []


def test_tool_names_are_unique_across_servers():
    # given
    names = [tool.__name__ for _, _, tool in EXPORTED]

    # when / then
    assert len(names) == len(set(names))


def test_deprecated_tools_are_not_exported():
    # given / when / then
    assert sorted(set(DEPRECATED) & set(BY_NAME)) == []


@pytest.mark.parametrize("name", sorted(BY_NAME))
def test_tool_is_async_and_scoped(name):
    # given
    _, _, tool = BY_NAME[name]

    # when / then
    assert inspect.iscoroutinefunction(tool)
    assert getattr(tool, "required_scope", None), "every tool needs @requires_scope"


@pytest.mark.parametrize("name", sorted(BY_NAME))
def test_docstring_is_present_and_within_budget(name):
    # given
    _, _, tool = BY_NAME[name]

    # when
    doc = inspect.getdoc(tool) or ""

    # then
    assert doc, "tool needs a docstring"
    assert len(doc) <= DOCSTRING_BUDGET, f"{len(doc)} chars, trim to the template"


@pytest.mark.parametrize("name", sorted(BY_NAME))
def test_every_parameter_has_a_description(name):
    # given
    _, _, tool = BY_NAME[name]

    # when
    properties = Tool.from_function(tool).parameters.get("properties", {})

    # then
    assert [param for param, schema in properties.items() if not schema.get("description")] == []


@pytest.mark.parametrize("name", sorted(TOOLS))
def test_mapped_operations_exist_in_the_spec(name):
    # given
    entry = TOOLS[name]

    # when
    operation_ids = ([entry["op"]] if entry["op"] else []) + (entry["ops"] or [])

    # then
    assert [op for op in operation_ids if op not in OPERATIONS[entry["service"]]] == []


@pytest.mark.parametrize("name", sorted(n for n, e in TOOLS.items() if e["op"] and not e["scopes"]))
def test_scopes_match_the_endpoint(name):
    # given
    entry = TOOLS[name]
    _, _, operation = OPERATIONS[entry["service"]][entry["op"]]

    # when
    _, _, tool = BY_NAME[name]

    # then
    assert set(tool.required_scope) == set(operation.get("x-arcanna-scopes") or ["public"])


def _dummy(annotation):
    origin = typing.get_origin(annotation)
    if origin is typing.Annotated:
        return _dummy(typing.get_args(annotation)[0])
    if origin is typing.Union:
        return _dummy([a for a in typing.get_args(annotation) if a is not type(None)][0])
    if origin is typing.Literal:
        return typing.get_args(annotation)[0]
    if origin in (list, typing.List):
        return []
    if origin in (dict, typing.Dict) or annotation is dict:
        return {}
    return {int: 1, float: 1.0, bool: True, str: "x"}.get(annotation, "x")


def _required_kwargs(tool):
    hints = typing.get_type_hints(tool, include_extras=True)
    return {name: _dummy(hints[name]) for name, param in inspect.signature(tool).parameters.items()
            if param.default is inspect.Parameter.empty}


@pytest.mark.parametrize("name", sorted(n for n, e in TOOLS.items() if e["op"]))
def test_single_operation_tool_calls_its_endpoint(name):
    # given
    entry = TOOLS[name]
    _, module, tool = BY_NAME[name]
    method, path, _ = OPERATIONS[entry["service"]][entry["op"]]
    pattern = "^" + re.sub(r"{\w+}", "[^/]+", path) + "$"

    # when
    with patch.object(module, "call", AsyncMock(return_value={})) as mocked:
        result = asyncio.run(tool(**_required_kwargs(tool)))

    # then
    assert "error_message" not in (result or {}), result
    called_method, called_path = mocked.call_args[0][:2]
    assert called_method == method
    assert re.match(pattern, called_path), f"{called_path} does not match {path}"
    expected_service = {"service": "agents"} if entry["service"] == "agents" else {}
    assert {k: v for k, v in mocked.call_args[1].items() if k == "service"} == expected_service


@pytest.mark.parametrize("server", sorted(SERVERS))
def test_each_server_builds_with_its_scoped_tools(server):
    # given
    from arcanna_mcp_server.common import runner
    scopes = {scope for tool in all_tools(SERVERS[server]) for scope in tool.required_scope}

    # when
    with patch.object(runner, "get_api_key_scope", return_value=scopes):
        mcp_server = runner.build_server(server, SERVERS[server])

    # then
    listed = asyncio.run(mcp_server.list_tools())
    assert {t.name for t in listed} == {tool.__name__ for tool in all_tools(SERVERS[server])}


def test_a_key_without_a_scope_does_not_see_its_tools():
    # given
    from arcanna_mcp_server.common import runner

    # when
    with patch.object(runner, "get_api_key_scope", return_value=set()):
        mcp_server = runner.build_server("core", CORE_MODULES)

    # then
    listed = {t.name for t in asyncio.run(mcp_server.list_tools())}
    assert "delete_events" not in listed
    assert listed == {tool.__name__ for tool in all_tools(CORE_MODULES) if tool.required_scope[0] == "public"}


def test_update_agentic_workflow_keeps_the_stored_flags():
    # given
    from arcanna_mcp_server.agents.tools import workflows
    stored = {"is_shared": True, "use_in_assistant": True, "tags": ["soc"], "settings": {"a": 1}}
    mocked = AsyncMock(side_effect=[stored, {"workflow_id": "w1"}])

    # when
    with patch.object(workflows, "call", mocked):
        asyncio.run(workflows.update_agentic_workflow(workflow_id="w1", source_code="code"))

    # then
    body = mocked.call_args_list[1][1]["json"]
    assert body["is_shared"] is True and body["use_in_assistant"] is True and body["tags"] == ["soc"]
    assert body["settings"] == {"a": 1} and body["source_code"] == "code" and body["id"] == "w1"


@pytest.mark.parametrize("workflow_id", ["12", 12, "a1b2"])
def test_string_ids_survive_mcp_argument_decoding(workflow_id):
    # given
    from arcanna_mcp_server.common import runner
    from arcanna_mcp_server.agents.tools import workflows
    with patch.object(runner, "get_api_key_scope", return_value={"read:agents"}):
        mcp_server = runner.build_server("agents", AGENT_MODULES)

    # when
    with patch.object(workflows, "call", AsyncMock(return_value={"id": "x"})) as mocked:
        asyncio.run(mcp_server.call_tool("get_agentic_workflow_by_id", {"workflow_id": workflow_id}))

    # then
    assert mocked.call_args[0][1].endswith(f"/{workflow_id}")


def test_nested_string_fields_take_numbers():
    # given
    from arcanna_mcp_server.common import runner
    from arcanna_mcp_server.agents.tools import workflows
    with patch.object(runner, "get_api_key_scope", return_value={"write:agents"}):
        mcp_server = runner.build_server("agents", AGENT_MODULES)

    # when
    with patch.object(workflows, "call", AsyncMock(return_value={})) as mocked:
        asyncio.run(mcp_server.call_tool("create_agentic_workflow", {
            "source_code": "x", "env_variables": [{"name": "PORT", "value": 8080}]}))

    # then
    assert mocked.call_args[1]["json"]["env_variables"][0]["value"] == "8080"
