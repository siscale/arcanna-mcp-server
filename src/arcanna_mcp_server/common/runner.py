import os
import sys
from types import ModuleType
from typing import Callable, List, Literal, Sequence, cast

from mcp.server import FastMCP
from mcp.server.fastmcp.prompts.base import Prompt

from arcanna_mcp_server.common import environment
from arcanna_mcp_server.common.scopes import filter_by_scope, get_api_key_scope


def all_tools(modules: Sequence[ModuleType]) -> List[Callable]:
    return [tool for module in modules for tool in module.export_tools()]


def build_server(name: str, modules: Sequence[ModuleType], prompts: Sequence[Callable] = ()) -> FastMCP:
    server = FastMCP(name, port=int(os.getenv("PORT") or 8000))
    for tool_fn in filter_by_scope(all_tools(modules), get_api_key_scope()):
        server.add_tool(tool_fn)
    for prompt_fn in prompts:
        server.add_prompt(Prompt.from_function(prompt_fn))
    return server


def run(name: str, modules: Sequence[ModuleType], prompts: Sequence[Callable] = ()) -> None:
    environment.validate_environment_variables()
    print(f"Started {name} with transport mode {environment.TRANSPORT_MODE}", file=sys.stderr)
    build_server(name, modules, prompts).run(transport=cast(Literal["stdio", "sse"], environment.TRANSPORT_MODE))
