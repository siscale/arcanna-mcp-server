from arcanna_mcp_server.common.runner import run
from arcanna_mcp_server.rag.tools import MODULES

NAME = "arcanna-rag"


def main():
    run(NAME, MODULES)
