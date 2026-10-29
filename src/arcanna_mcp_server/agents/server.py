from arcanna_mcp_server.agents.prompts import PROMPTS
from arcanna_mcp_server.common.runner import run
from arcanna_mcp_server.agents.tools import MODULES

NAME = "arcanna-agents"


def main():
    run(NAME, MODULES, PROMPTS)
