from datetime import datetime
from typing import Callable, List
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        get_system_timestamp,
    ]


@handle_exceptions
async def get_system_timestamp() -> str:
    """
        Get current system timestamp.
        Use it when every time the time is needed.

    Returns:
    --------
    str
        A string representing the current system timestamp.
    """
    utc_timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    return utc_timestamp
