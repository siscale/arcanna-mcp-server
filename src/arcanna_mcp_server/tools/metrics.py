from typing import Callable, List
from arcanna_mcp_server.constants import METRICS_JOB_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
import requests
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        metrics_job
    ]


@handle_exceptions
async def metrics_job(job_id: int, start_date: str=None, end_date: str=None) -> dict:
    """
        Fetches the metrics associated with a specific Arcanna job.
        No date range means all time metrics are fetched.
    Parameters:
    --------
    job_id: Unique identifier of the job
    start_date : str or None
        Start date to filter events newer than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
    end_date : str or None
        Start date to filter events newer than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
    Returns:
    --------
    dict
        A dictionary containing the metrics associated with the job.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    formatted_url = METRICS_JOB_URL + f'?job_id={job_id}'
    if start_date:
        formatted_url += f'&start_datetime={start_date}'
    if end_date:
        formatted_url += f'&end_datetime={end_date}'

    response = requests.get(formatted_url.format(job_id), headers=headers)
    return response.json()
