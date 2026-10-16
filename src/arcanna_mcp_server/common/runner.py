import os
import sys
from types import ModuleType
import typing
from typing import Callable, List, Literal, Sequence, Set, Type, cast

from mcp.server import FastMCP
from mcp.server.fastmcp.prompts.base import Prompt
from pydantic import BaseModel

from arcanna_mcp_server.common import environment
from arcanna_mcp_server.common.scopes import filter_by_scope, get_api_key_scope


def all_tools(modules: Sequence[ModuleType]) -> List[Callable]:
    return [tool for module in modules for tool in module.export_tools()]


def _nested_models(annotation, found: Set[Type[BaseModel]]) -> Set[Type[BaseModel]]:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if annotation not in found:
            found.add(annotation)
            for field in annotation.model_fields.values():
                _nested_models(field.annotation, found)
        return found
    for argument in typing.get_args(annotation):
        _nested_models(argument, found)
    return found


def coerce_numbers_to_str(server: FastMCP) -> None:
    """FastMCP json-decodes string arguments, so "12" arrives as 12; let str fields take numbers back."""
    for tool in server._tool_manager.list_tools():
        for model in _nested_models(tool.fn_metadata.arg_model, set()):
            model.model_config["coerce_numbers_to_str"] = True
            model.model_rebuild(force=True)


def build_server(name: str, modules: Sequence[ModuleType], prompts: Sequence[Callable] = ()) -> FastMCP:
    server = FastMCP(name, port=int(os.getenv("PORT") or 8000))
    for tool_fn in filter_by_scope(all_tools(modules), get_api_key_scope()):
        server.add_tool(tool_fn)
    coerce_numbers_to_str(server)
    for prompt_fn in prompts:
        server.add_prompt(Prompt.from_function(prompt_fn))
    return server


def run(name: str, modules: Sequence[ModuleType], prompts: Sequence[Callable] = ()) -> None:
    environment.validate_environment_variables()
    print(f"Started {name} with transport mode {environment.TRANSPORT_MODE}", file=sys.stderr)
    build_server(name, modules, prompts).run(transport=cast(Literal["stdio", "sse"], environment.TRANSPORT_MODE))
