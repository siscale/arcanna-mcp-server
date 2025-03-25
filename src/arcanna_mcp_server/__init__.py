from arcanna_mcp_server.environment import validate_environment_variables
from . import server


def main():
    validate_environment_variables()
    server.main()
