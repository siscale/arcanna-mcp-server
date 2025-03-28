from typing import Callable, List
from arcanna_mcp_server.constants import START_JOB_URL, STOP_JOB_URL, TRAIN_JOB_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
import requests
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        start_job,
        stop_job,
        train_job
    ]


@handle_exceptions
async def start_job(job_id: int) -> dict:
    """
        Start a job to start ingesting events.
    Parameters:
    --------
    job_id: Unique identifier of the job

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

    response = requests.post(START_JOB_URL.format(job_id), headers=headers)
    return response.json()


@handle_exceptions
async def stop_job(job_id: int) -> dict:
    """
        Stop a job to stop ingesting events.

    Parameters:
    --------
    job_id: Unique identifier of the job

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

    response = requests.post(STOP_JOB_URL.format(job_id), headers=headers)
    return response.json()


@handle_exceptions
async def train_job(job_id: int) -> dict:
    """
        Train a job in Arcanna so that the job can learn from the provided feedback.

    Parameters:
    --------
    job_id: Id of the job

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

    response = requests.post(TRAIN_JOB_URL.format(job_id), headers=headers)
    return response.json()
