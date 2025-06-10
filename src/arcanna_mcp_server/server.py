from dotenv import load_dotenv
load_dotenv(verbose=True)

from mcp.server import FastMCP

from arcanna_mcp_server.environment import TRANSPORT_MODE, validate_environment_variables
from arcanna_mcp_server.tools import attach_tools
import os


mcp = FastMCP("arcanna_mcp-server", port=os.getenv("PORT", 8000))

attach_tools(mcp)


def main():
    # Initialize and run the server
    print(f"Started server with transport mode {TRANSPORT_MODE}")
    validate_environment_variables()
    mcp.run(transport=TRANSPORT_MODE)


if __name__ == '__main__':
    main()
