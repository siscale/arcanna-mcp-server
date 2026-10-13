from arcanna_mcp_server.common.runner import run
from arcanna_mcp_server.core.tools import MODULES

NAME = "arcanna"


def main():
    run(NAME, MODULES)
