import requests
from typing import List, Callable, Literal, Optional, Union
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.models.generic_events import EventsModelResponse, TransferEventResponse
from arcanna_mcp_server.models.filters import FilterFieldsObject
from arcanna_mcp_server.constants import (
    EXPORT_EVENT_URL, INGEST_EVENT_URL, QUERY_EVENTS_URL, FILTER_FIELDS_URL, EVENT_FEEDBACK_URL_V2, \
    ADD_AGENTIC_NOTES_URL, REPROCESS_EVENTS_URL, REPROCESS_EVENT_URL
)


def export_tools() -> List[Callable]:
    return [
        add_agentic_notes,
        query_arcanna_events,
        add_feedback_to_event,
        reprocess_events,
        reprocess_event_by_id,
        export_event_by_id,
        transfer_event
    ]


@handle_exceptions
async def add_agentic_notes(job_id: int, event_id: Union[str, int], workflow_name: Optional[str] = None,
                            workflow_id: Optional[Union[str, int]] = None,
                            session_id: Optional[Union[str, int]] = None, agent_notes: str = "",
                            agent_saved_objects: dict = None) -> dict:
    """
    Add agentic information to an event.

    This endpoint allows adding agent-generated information to an existing event,
    including agent name, notes, and saved objects.

    Parameters:
    --------
    job_id: int
        Unique identifier of the job
    event_id: str or int
        Unique identifier of the event
    workflow_name: str, optional
        Name of the agentic workflow
    workflow_id: str, optional
        ID of the workflow
    session_id: str, optional
        Session ID of the agentic workflow
    agent_notes: str
        Notes from the agent (required)
    agent_saved_objects: dict, optional
        Objects saved by the agent (defaults to empty dict if not provided)

    Returns:
    --------
    dict
        A dictionary with the following keys:
        - status (str): The current status of the operation
        - reason (str): Short description of the error if one occurred; empty if successful.
        - reason_details (list): A list of error details if one occurred; empty if successful.
    """

    if agent_saved_objects is None:
        agent_saved_objects = {}

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "agent_notes": agent_notes,
        "agent_saved_objects": agent_saved_objects
    }

    # Add optional fields only if they are provided
    if workflow_name is not None:
        payload["workflow_name"] = workflow_name
    if workflow_id is not None:
        payload["workflow_id"] = workflow_id
    if session_id is not None:
        payload["session_id"] = session_id

    response = requests.post(
        ADD_AGENTIC_NOTES_URL.format(job_id=str(job_id), event_id=str(event_id)),
        headers=headers,
        json=payload
    )
    return response.json()


@handle_exceptions
async def get_filter_fields(job_ids: Optional[Union[List[int], int]] = None,
                            job_titles: Optional[Union[List[str], str]] = None
                            ) -> List[FilterFieldsObject]:
    """
    Used to get available fields with available operators and the jobs where the fields are available.
    If neither job_ids nor job_titles are provided, the search will include fields across all jobs.
    To be used within query_arcanna_events tool to get a list of available fields to filter on.

    Parameters:
    -----------
    job_ids : int or list of int or None
        Job IDs to filter on.
    job_titles : str or list of str or None
        Job titles to filter on.
    Returns:
    --------
    list of dictionary
    A dictionary containing job details with the following keys:
        - field_name (str): The field name.
        - available_operators (list of str): A list of available operators for the specified field.
        - available_in_jobs (list of int): A list of jobs where the field is available.
    """
    body = {}

    if job_ids:
        body["job_ids"] = job_ids

    if job_titles:
        body["job_titles"] = job_titles

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(FILTER_FIELDS_URL, json=body, headers=headers)
    return response.json()


@handle_exceptions
async def add_feedback_to_event(job_id: int, event_id: Union[str, int], label: str, storage_name: Optional[str] = None) -> dict:
    """
    Provide feedback on a previously ingested event by Arcanna job. The provided feedback will be used to train future AI models
    and make better decisions on new and similar events.

    Parameters:
    -----------
    job_id : int
        Unique identifier for the job.
    event_id : str or int
        Unique identifier of the event you want to provide feedback for.
    label: str
        Decision label to be applied for the event. Can be for example Escalate or Drop. Escalate means that the user considers
        the event should be investigated and escalated. Drop means that the event is a false positive and should not
        be investigated.
    storage_name: str or None
        Storage name to be used for feedback. Use only if the job have multiple storages defined.
        If none (default) the feedback will be applied to the latest event with event_id ingested.

    Returns:
    --------
    dict
        A dictionary containing feedback details with the following keys:

        - status (str): Specifies if the feedback was successfully sent or not.
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    if job_id is None:
        raise Exception("Job ID is required.")

    if event_id is None:
        raise Exception("Event ID is required.")

    if label is None:
        raise Exception("Label is required.")

    formatted_url = EVENT_FEEDBACK_URL_V2.format(job_id, event_id) + f'?feedback_label={label}'
    if storage_name:
        formatted_url += f'&storage_name={storage_name}'

    response = requests.put(formatted_url, headers=headers)
    return response.json()


@handle_exceptions
async def query_arcanna_events(job_ids: Optional[Union[List[int], int]] = None,
                               job_titles: Optional[Union[List[str], str]] = None,
                               event_ids: Optional[Union[List[str], str]] = None,
                               decision_points_only: Optional[bool] = False,
                               count_results_only: Optional[bool] = False,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               date_field: Optional[str] = "@timestamp",
                               size: Optional[int] = 5,
                               page: Optional[int] = 0,
                               sort_by_column: Optional[str] = "@timestamp",
                               sort_order: Optional[Literal['desc', 'asc']] = "desc",
                               filters: Optional[List[dict]] = None
                               ) -> EventsModelResponse:
    """
    Query events filtered by job IDs, job titles, event IDs, or specific filtering criteria (size, start_date, end_date, filters).
    At least one of 'job_ids', 'job_titles', 'event_ids', 'size', 'filters', 'start_date', or 'end_date' must be provided.
    Both the job_ids and job_title fields may be missing.
    If neither job_ids nor job_titles are provided, the search will include events across all jobs.
    When working with timestamps: the '@timestamp' field represents the original alert/event timestamp, while the 'timestamp_inference' field represents the time it was ingested into Arcanna.
    In case of an internal server error, show the error to the user and do not use any other tool, ask the user how he would like to continue.

    Parameters:
    -----------
    job_ids : int or list of int or None
        Job IDs to filter on.
    job_titles : str or list of str or None
        Job titles to filter on.
    event_ids : str or list of str or None
        Events IDs to filter on.
    decision_points_only : bool or None
         If set to true, only decision points will be included in the events response, excluding the full event.
    count_results_only : bool or None
         If set to true, only the total count of events will be returned, and no events.
    start_date : str or None
        Start date to filter events newer than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
    end_date : str or None
        End date to filter events older than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
    date_field : str or None
        The field to be used for date range filtering. Defaults to the '@timestamp' field; use the default field unless the user specifies a different one.
    size : int or None
        Number of events to include in response. If job_ids or job_titles provided it is the number of events per job.
    page : int or None (page counting starts from 0, default: 0)
        Page number, used for pagination. Keep size parameter fixed and increase page size to get more results.
    sort_by_column : str or None
        The field used to sort events. Defaults to the '@timestamp' field; use the default field unless the user specifies a different one.
    sort_order : str or None
        The order in which to sort events by. Defaults to 'desc' order; use the default order unless the user specifies a different one.
    filters : list of dict or None
      Filters to apply to the events returned by the query. If multiple filters are provided, they function as an AND operator between the filters.
      Each filter in list is a dictionary with keys: "field", "operator" and "value"
      - field - the field to apply filters to
      - operator can be: "is", "is not", "is one of", "is not one of", "starts with", "not starts with", "contains", "not contains", "exists", "not exists", "lt", "lte", "gte", "gte"
      - value to filter by, value is omitted for operators "exists" and "not exists"

        Arcanna fields:
            1. Arcanna decision field = "arcanna.result_label"
            2. Arcanna consensus field = "arcanna.consensus"
            3. Arcanna outlier field flag = "arcanna.outlier_flag"
            4. Arcanna in model status field = "arcanna.knowledge_base_state" or "arcanna.bucket_state"
            5. Arcanna low confidence warning flag field = "attention.low_confidence_score.attention_required"
            6. Arcanna undecided warning flag field = "attention.undecided_consensus.attention_required"

        Predefined filters:
         1. Query outlier events:
            {{
                "filters": [{{
                    "field": "arcanna.outlier_flag",
                    "operator": "is",
                    "value": true
                    }}]
            }}
         2. Query events with low confidence score:
            {{
                "filters": [{{
                    "field": "arcanna.attention.low_confidence_score.attention_required",
                    "operator": "is",
                    "value": true
                    }}]
            }}
         3. Query events with undecided consensus:
            {{
                "filters": [{{
                    "field": "arcanna.attention.undecided_consensus.attention_required",
                    "operator": "is",
                    "value": true
                    }}]
            }}
         4. Query events with any feedback (Event Centric Decision Intelligence job):
            {{
                "filters": [{{
                    "field": "arcanna.knowledge_base_state",
                    "operator": "is",
                    "value": "new"
                    }}]
            }}
         5. Query events without any feedback (Event Centric Decision Intelligence job):
            {{
                "filters": [{{
                    "field": "arcanna.knowledge_base_state",
                    "operator": "is not",
                    "value": "new"
                    }}]
            }}
         6. Query events with any feedback (Decision Intelligence job):
            {{
                "filters": [{{
                    "field": "arcanna.bucket_state",
                    "operator": "is",
                    "value": "new"
                    }}]
            }}
         7. Query events without any feedback (Decision Intelligence job):
            {{
                "filters": [{{
                    "field": "arcanna.bucket_state",
                    "operator": "is not",
                    "value": "new"
                    }}]
            }}
         8. Query events marked as 'Escalate' or 'Investigate' by Arcanna:
            {{
                "filters": [{{
                    "field": "arcanna.result_label",
                    "operator": "is one of",
                    "value": ['Escalate', 'Investigate']
                    }}]
            }}
         9. Query events not marked as 'Drop' or 'Low priority' by Arcanna:
            {{
                "filters": [{{
                    "field": "arcanna.result_label",
                    "operator": "is not one of",
                    "value": ['Drop', 'Low priority']
                    }}]
            }}
         10. Query events with consensus 'Escalate' or 'Drop':
            {{
            "filters": [{{
                "field": "arcanna.consensus",
                "operator": "is one of",
                "value": ['Escalate', 'Drop']
                }}]
            }}

    Returns:
    --------
    list of dictionary
    A dictionary containing job details with the following keys:
        - event_id (str): Unique identifier for the event.
        - job_id (int): Unique identifier of the job where the event was pulled from.
        - job_title (str): Unique identifier for the job where the event was pulled from.
        - decision_points (dict): Dictionary of decision points. Each key in decision_points is a feature used in model training.
        - arcanna (dict or None): Dictionary containing fields added by Arcanna processing.
        - raw_event (dict or None): Dictionary containing the raw event data. Event timestamp field is '@timestamp' (use it every time when event/alert timestamp is requested).
    """

    body = {}

    if job_ids:
        body["job_ids"] = job_ids

    if job_titles:
        body["job_titles"] = job_titles

    if event_ids:
        body["event_ids"] = event_ids

    if decision_points_only:
        body["decision_points_only"] = decision_points_only

    if count_results_only:
        body["count_results_only"] = count_results_only

    if start_date:
        body["start_date"] = start_date

    if end_date:
        body["end_date"] = end_date

    if date_field:
        body["date_field"] = date_field

    if page:
        body["page"] = page

    if size:
        body["size"] = size

    if sort_by_column:
        body["sort_by_column"] = sort_by_column

    if sort_order:
        body["sort_order"] = sort_order

    if filters:
        body["filters"] = filters

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(QUERY_EVENTS_URL, json=body, headers=headers)
    return response.json()


@handle_exceptions
async def reprocess_events(job_id: Union[str, int], start_date: Optional[str] = None, end_date: Optional[str] = None,
                           date_field: Optional[str] = "@timestamp", filters: Optional[List[dict]] = None):
    """
    Reprocess events filtered by specific filtering criteria (start_date, end_date, filters) for a specific job_id.
    When working with timestamps: the '@timestamp' field represents the original alert/event timestamp, while the 'timestamp_inference' field represents the time it was ingested into Arcanna.
    Parameters:
    -----------
        job_id: str
            Unique identifier of the job
        start_date : str or None
            Start date to filter events newer than this date.
            Date format:
              - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
        end_date : str or None
            End date to filter events older than this date.
            Date format:
              - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
        date_field : str or None
            The field to be used for date range filtering. Defaults to the '@timestamp' field; use the default field unless the user specifies a different one.
        filters : list of dict or None
          Filters to apply to the events returned by the query. If multiple filters are provided, they function as an AND operator between the filters.
          Each filter in list is a dictionary with keys: "field", "operator" and "value"
          - field - the field to apply filters to
          - operator can be: "is", "is not", "is one of", "is not one of", "starts with", "not starts with", "contains", "not contains", "exists", "not exists", "lt", "lte", "gte", "gte"
          - value to filter by, value is omitted for operators "exists" and "not exists"

        Arcanna fields:
            1. Arcanna decision field = "arcanna.result_label"
            2. Arcanna consensus field = "arcanna.consensus"
            3. Arcanna outlier field flag = "arcanna.outlier_flag"
            4. Arcanna in model status field = "arcanna.knowledge_base_state" or "arcanna.bucket_state"
            5. Arcanna low confidence warning flag field = "attention.low_confidence_score.attention_required"
            6. Arcanna undecided warning flag field = "attention.undecided_consensus.attention_required"

        Predefined filters:
         1. Reprocess outlier events:
            {
                "filters": [{
                    "field": "arcanna.outlier_flag",
                    "operator": "is",
                    "value": true
                    }]
            }
         2. Reprocess events with low confidence score:
            {
                "filters": [{
                    "field": "arcanna.attention.low_confidence_score.attention_required",
                    "operator": "is",
                    "value": true
                    }]
            }
         3. Reprocess events with undecided consensus:
            {
                "filters": [{
                    "field": "arcanna.attention.undecided_consensus.attention_required",
                    "operator": "is",
                    "value": true
                    }]
            }
         4. Reprocess events with any feedback (Event Centric Decision Intelligence job):
            {
                "filters": [{
                    "field": "arcanna.knowledge_base_state",
                    "operator": "is",
                    "value": "new"
                    }]
            }
         5. Reprocess events without any feedback (Event Centric Decision Intelligence job):
            {
                "filters": [{
                    "field": "arcanna.knowledge_base_state",
                    "operator": "is not",
                    "value": "new"
                    }]
            }
         6. Reprocess events with any feedback (Decision Intelligence job):
            {
                "filters": [{
                    "field": "arcanna.bucket_state",
                    "operator": "is",
                    "value": "new"
                    }]
            }
         7. Reprocess events without any feedback (Decision Intelligence job):
            {
                "filters": [{
                    "field": "arcanna.bucket_state",
                    "operator": "is not",
                    "value": "new"
                    }]
            }
         8. Reprocess events marked as 'Escalate' or 'Investigate' by Arcanna:
            {
                "filters": [{
                    "field": "arcanna.result_label",
                    "operator": "is one of",
                    "value": ['Escalate', 'Investigate']
                    }]
            }
         9. Reprocess events not marked as 'Drop' or 'Low priority' by Arcanna:
            {
                "filters": [{
                    "field": "arcanna.result_label",
                    "operator": "is not one of",
                    "value": ['Drop', 'Low priority']
                    }]
            }
         10. Reprocess events with consensus 'Escalate' or 'Drop':
            {
            "filters": [{
                "field": "arcanna.consensus",
                "operator": "is one of",
                "value": ['Escalate', 'Drop']
                }]
            }

    Returns:
    --------
        Returns:
    --------
    A dictionary with the following keys:
        - request (dict): Contains information about the request
            - status: str - Status of the request. "OK" means the events were marked for reprocess successfully
            - reason: str - In case of an error, contains details about the error
            - reason_details: str - In case of an error, contains details about the error
        - events_updated (int): Number of events marked for reprocessing.
    """

    body = {}

    job_id = job_id

    if start_date:
        body["start_date"] = start_date

    if end_date:
        body["end_date"] = end_date

    if date_field:
        body["date_field"] = date_field

    if filters:
        body["filters"] = filters

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(REPROCESS_EVENTS_URL.format(str(job_id)), json=body, headers=headers)
    return response.json()


@handle_exceptions
async def reprocess_event_by_id(job_id: int, event_id: str):
    """
    Reprocess an event for a job.

    Parameters:
    -----------
    job_id: int
        Unique identifier of the job
    event_id : str or None
        Unique identifier of the event to be marked for reprocess.

    Returns:
    --------
    A dictionary with the following keys:
        - request (dict): Contains information about the request
            - status: str - Status of the request. "OK" means the event was marked for reprocess successfully
            - reason: str - In case of an error, contains details about the error
            - reason_details: str - In case of an error, contains details about the error
    """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(REPROCESS_EVENT_URL.format(job_id, event_id), headers=headers)
    return response.json()


@handle_exceptions
async def export_event_by_id(job_id: int, event_id: Union[int, str]) -> dict:
    """
    Export the full definition of an event from a job in JSON format.

    Parameters:
    -----------
    job_id: int
        Unique identifier of the job
    event_id: str or int
        Unique identifier of the event to be exported
    -----------

    Returns:
    -----------
    The event ingested by the job in JSON format.
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content_Type": "application/json"
    }

    response = requests.get(EXPORT_EVENT_URL.format(job_id, event_id), headers=headers)
    return response.json()


@handle_exceptions
async def transfer_event(source_job_id: int, event_id: Union[int, str],
                         destination_job_id: int, destination_storage_tag_name: Optional[str] = None) -> TransferEventResponse:
    """
    Transfer an event identified by its id from a source job to a new destination job.
    Event will still exist in the source job. It will be send as a copy to the destination job.

    Parameters:
    -----------
    source_job_id: int
        Unique identifier of the job where the event is stored initially.
    event_id: str or int
        Unique identifier of the event to be transfered. This is located in the source job.
    destination_job_id: int
        Unique identifier of the job where the event will be stored after transfer.
    destination_storage_tag_name: string or None
        In case the destination job is configured as a multi-input job the storage_tag will specify
        from wich input integration the event is sent.
    """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content_Type": "application/json"
    }

    response = requests.get(EXPORT_EVENT_URL.format(source_job_id, event_id), headers=headers)
    if response.status_code != 200:
        return TransferEventResponse(status="NOK", error_message=response.json())

    event_source = response.json().get("arcanna_event")
    if event_source is None:
        return TransferEventResponse(status=f"NOK", error_message=f"Event with id {event_id} not found in source job with id {source_job_id}")

    body = {
        "job_id": destination_job_id,
        "raw_body": event_source
    }
    if destination_storage_tag_name is not None:
        body["storage_tag"] = destination_storage_tag_name

    response = requests.post(INGEST_EVENT_URL, json=body, headers=headers)
    return response.json()
