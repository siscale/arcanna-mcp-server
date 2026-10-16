from dotenv import load_dotenv

load_dotenv()


def main_core():
    from arcanna_mcp_server.core import server
    server.main()


def main_agents():
    from arcanna_mcp_server.agents import server
    server.main()


def main_rag():
    from arcanna_mcp_server.rag import server
    server.main()


main = main_core
