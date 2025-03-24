from typing import Callable, List

import requests

from arcanna_mcp_server.environment import API_KEY
from arcanna_mcp_server.constants import HEALTH_CHECK_URL
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        health_check
    ]


@handle_exceptions
async def health_check() -> dict:
    """
        Health check of Arcanna API Server.
        Returns:
        --------
        dict
            - status (bool): If false, the server is up an running but API key is invalid. If true, api key is also
            authorized
    """
    headers = {
        "x-arcanna-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(HEALTH_CHECK_URL, headers=headers)
    return response.json()
