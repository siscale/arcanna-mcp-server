from typing import Callable, List

import requests

from arcanna_mcp_server.constants import SEND_EVENT_URL, SEND_EVENT_WITH_ID_URL, EVENT_FEEDBACK_URL, RETRIEVE_EVENT_BY_ID_URL
from arcanna_mcp_server.environment import API_KEY, ARCANNA_USER
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions


def export_tools() -> List[Callable]:
    return [
        send_event,
        send_event_with_id,
        send_feedback_for_event,
        get_event_by_id
    ]


@handle_exceptions
async def send_event(job_id: int, event: dict) -> dict:
    """
    Send a JSON event payload for Arcanna to provide a decision on. Arcanna will generate a new internal ID for the event.
    In case of an internal server error, do not use any other tool, ask the user how he would like to continue,
    Parameters:
    -----------
    job_id : int
        Unique identifier for the job.
    event : dict
        A raw dictionary containing event/alert/incident data.

    Returns:
    --------
    dict
        A dictionary containing event tracking details with the following keys:

        - event_id (str): Unique identifier for the event.
        - job_id (int): Unique identifier of the job where the event has been sent to.
        - ingest_timestamp (str): Timestamp when the data was ingested.
        - status (str): Status that tells if the event has been sent to ingestion successfully
        - error_message (str): Error details in case of failure; empty if successful.
    """
    body = {
        "job_id": job_id,
        "raw_body": event
    }
    headers = {
        "x-arcanna-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(SEND_EVENT_URL, json=body, headers=headers)
    return response.json()


@handle_exceptions
async def send_event_with_id(job_id: int, event: dict, event_id: str) -> dict:
    """
    Send a JSON security alert/incident/event to Arcanna for ingestion.

    Parameters:
    -----------
    job_id : int
        Unique identifier for the job.
    event : dict
        A raw dictionary containing event/alert/incident data.
    event_id: str
        Unique identifier for the event.

    Returns:
    --------
    dict
        A dictionary containing event tracking details with the following keys:

        - event_id (str): Unique identifier for the event.
        - job_id (int): Unique identifier of the job where the event has been sent to.
        - ingest_timestamp (str): Timestamp when the data was ingested.
        - status (str): Status that tells if the event has been sent to ingestion successfully
        - error_message (str): Error details in case of failure; empty if successful.
    """
    body = {
        "job_id": job_id,
        "raw_body": event
    }
    headers = {
        "x-arcanna-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    if event_id is None:
        raise Exception("Event ID is required.")

    response = requests.post(SEND_EVENT_WITH_ID_URL.format(event_id), json=body, headers=headers)
    return response.json()


@handle_exceptions
async def send_feedback_for_event(job_id: int, event_id: str, label: str) -> dict:
    """
    Provide feedback on a previously ingested event by Arcanna job. The provided feedback will be used to train future AI models
    and make better decisions on new and similar events.

    Parameters:
    -----------
    job_id : int
        Unique identifier for the job.
    event_id : dict
        Unique identifier of the event you want to provide feedback for.
    label: str
        Decision label to be applied for the event. Can be for example Escalate or Drop. Escalate means that the user considers
        the event should be investigated and escalated. Drop means that the event is a false positive and should not
        be investigated.
    Returns:
    --------
    dict
        A dictionary containing feedback details with the following keys:

        - status (str): Specifies if the feedback was successfully sent or not.
    """
    headers = {
        "x-arcanna-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "cortex_user": "MCP-" + ARCANNA_USER,
        "feedback": label
    }
    if event_id is None:
        raise Exception("Event ID is required.")

    response = requests.put(EVENT_FEEDBACK_URL.format(job_id, event_id), json=body, headers=headers)
    return response.json()


@handle_exceptions
async def get_event_by_id(job_id: int, event_id: str) -> dict:
    """
    Retrieve event by id.

    Parameters:
    -----------
    job_id : int
        Unique identifier for the job id.
    event_id: str
        Unique identifier for the event.

    Returns:
    --------
    dict
        A dictionary containing event tracking details with the following keys:

        - event_id (str): Unique identifier for the event.
        - ingest_timestamp (str): Timestamp when the data was ingested.
        - status (str): Status that tells if the event has been sent to ingestion successfully
        - result (str): Label id of Arcanna's decision on the retrieved event.
        - result_label (str): Friendly name of the decision of Arcanna.
        - error_message (str): Error details in case of failure; empty if successful.
        - knowledge_base_state (str): State that specifies if the event was previously used in a model train. "Pending" means
        feedback was given but the job was not trained yet. "In model" means the event is incorporated in the model knowledge
        base. "Retrain" state means that the model was previously trained with the event but the feedback decision was changed
        and you need to retrain in order to update the model.
        - outlier (bool): Flag that specifies if the event is an outlier. Outlier if true.
        - confidence_score (float): percentage measuring the model's confidence on its decision.
    """
    headers = {
        "x-arcanna-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    if event_id is None:
        raise Exception("Event ID is required.")

    response = requests.get(RETRIEVE_EVENT_BY_ID_URL.format(job_id, event_id), headers=headers)
    return response.json()
