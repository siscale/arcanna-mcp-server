from mcp.server import FastMCP
from mcp.server.fastmcp.prompts.base import Prompt

from arcanna_mcp_server.prompts.agentic_code_instructions import agentic_code_instructions, workflow_creation_flow


def attach_prompts(mcp_server: FastMCP):
    prompts = [
        agentic_code_instructions,
        workflow_creation_flow
    ]
    for prompt_fn in prompts:
        mcp_server.add_prompt(Prompt.from_function(prompt_fn))
