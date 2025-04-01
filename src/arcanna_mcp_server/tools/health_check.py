from typing import Callable, List
import requests
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.constants import HEALTH_CHECK_URL
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        health_check
    ]


@handle_exceptions
async def health_check() -> dict:
    """
        Health check of Arcanna Management API Server.
        Returns:
        --------
        dict
            A dictionary with the following keys:
            - status (str): The current status of the operation
            - reason (str): Short description of the error if one occurred; empty if successful.
            - reason_details:  (str): A message describing the error if one occurred; empty if successful.
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(HEALTH_CHECK_URL, headers=headers)
    return response.json()
