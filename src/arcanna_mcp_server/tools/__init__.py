import arcanna_mcp_server.tools.resources
from mcp.server import FastMCP
import arcanna_mcp_server.tools.jobs
import arcanna_mcp_server.tools.health_check
import arcanna_mcp_server.tools.custom_code_block
import arcanna_mcp_server.tools.generic_events
import arcanna_mcp_server.tools.metrics
import arcanna_mcp_server.tools.agentic
from arcanna_mcp_server.utils.tool_scopes import filter_by_scope


def attach_tools(mcp_server: FastMCP):
    modules = [
        arcanna_mcp_server.tools.jobs,
        arcanna_mcp_server.tools.health_check,
        arcanna_mcp_server.tools.custom_code_block,
        arcanna_mcp_server.tools.resources,
        arcanna_mcp_server.tools.generic_events,
        arcanna_mcp_server.tools.metrics,
        arcanna_mcp_server.tools.agentic
    ]
    for module in modules:
        filtered_modules_tools = filter_by_scope(module.export_tools())
        for tool_fn in filtered_modules_tools:
            mcp_server.add_tool(tool_fn)
