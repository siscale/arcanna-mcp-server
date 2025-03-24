import arcanna_mcp.tools.resources
from mcp.server import FastMCP
import arcanna_mcp.tools.jobs
import arcanna_mcp.tools.events
import arcanna_mcp.tools.health_check
import arcanna_mcp.tools.custom_code_block
import arcanna_mcp.tools.generic_events
import arcanna_mcp.tools.system


def attach_tools(mcp_server: FastMCP):
    modules = [
        arcanna_mcp.tools.jobs,
        arcanna_mcp.tools.events,
        arcanna_mcp.tools.health_check,
        arcanna_mcp.tools.custom_code_block,
        arcanna_mcp.tools.resources,
        arcanna_mcp.tools.generic_events,
        arcanna_mcp.tools.system
    ]
    for module in modules:
        for tool_fn in module.export_tools():
            mcp_server.add_tool(tool_fn)
