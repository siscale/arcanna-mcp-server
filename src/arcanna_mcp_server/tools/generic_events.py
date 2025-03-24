import requests
from typing import List, Callable
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.models.generic_events import QueryEventsRequest
from arcanna_mcp_server.models.generic_events import EventModel


def export_tools() -> List[Callable]:
    return [
        query_arcanna_events
     ]


@handle_exceptions
async def query_arcanna_events(request: QueryEventsRequest) -> List[EventModel]:
    from arcanna_mcp_server.constants import QUERY_EVENTS_URL

    f"""
    Query events filtered by job IDs, job titles, event IDs, or specific filtering criteria.
    If neither job_ids nor job_titles are provided, the search will include events across all jobs.

    Parameters:
    -----------
    job_ids : int or list of int or None
        Job IDs to filter on.
    job_titles : str or list of str or None
        Job titles to filter on.
    event_ids : str or list of str or None
        Events IDs to filter on.
    decision_points_only : bool or None
        If set to 'true', include only decision points in response and not the entire event.
    start_date : str or None
        Start date to filter events newer than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
          - Elasticsearch format pattern letters: 'now' for now, 'y' for year, 'M' for month, 'd' for day, 'h' for hour, 'm' for minute, 's' for second.
        Examples: 'now-1d' for last day, 'now-1h' for last hour, 'now-30m' for latest 30 minutes.
    end_date : str or None
        End date to filter events older than this date.
        Date format:
          - ISO 8601 date string (e.g., 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS')
          - Elasticsearch format pattern letters: 'now' for now, 'y' for year, 'M' for month, 'd' for day, 'h' for hour, 'm' for minute, 's' for second.
        Examples: 'now-1d' for last day, 'now-1h' for last hour, 'now-30m' for latest 30 minutes.
    size : int or None
        Number of events to include in response for each job.
    sort_by_column : str or None
        The field to sort events by. Defaults to 'timestamp_inference' field.
    sort_order : str or None
        The order in which to sort events by. Defaults to 'desc' order.
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
        - raw_event (dict or None): Dictionary containing the raw event data.
    """

    body = {}

    if request.job_ids:
        body["job_ids"] = request.job_ids

    if request.job_titles:
        body["job_titles"] = request.job_titles

    if request.event_ids:
        body["event_ids"] = request.event_ids

    if request.decision_points_only:
        body["decision_points_only"] = request.decision_points_only

    if request.start_date:
        body["start_date"] = request.start_date

    if request.end_date:
        body["end_date"] = request.end_date

    if request.size:
        body["size"] = request.size

    if request.sort_by_column:
        body["sort_by_column"] = request.sort_by_column

    if request.sort_order:
        body["sort_order"] = request.sort_order

    if request.filters:
        body["filters"] = request.filters

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.post(QUERY_EVENTS_URL, json=body, headers=headers)
    return response.json()
