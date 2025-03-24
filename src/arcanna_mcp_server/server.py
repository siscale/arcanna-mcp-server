from mcp.server import FastMCP

from arcanna_mcp_server.environment import TRANSPORT_MODE
from arcanna_mcp_server.tools import attach_tools

mcp = FastMCP("arcanna_mcp-server")

attach_tools(mcp)


def main():
    # Initialize and run the server
    mcp.run(transport=TRANSPORT_MODE)


if __name__ == '__main__':
    main()
