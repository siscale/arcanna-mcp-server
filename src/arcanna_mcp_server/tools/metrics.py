import requests
from typing import Callable, List
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.models.metrics import GetJobMetricsResponse, GetJobAndLatestModelMetricsResponse, GetModelMetricsResponse
from arcanna_mcp_server.constants import METRICS_JOB_URL, METRICS_JOB_AND_LATEST_MODEL_URL, METRICS_MODEL_URL, METRICS_MODEL_URL_REQUEST_RECOMPUTE_METRICS
from arcanna_mcp_server.utils.tool_scopes import requires_scope


def export_tools() -> List[Callable]:
    return [
        metrics_job,
        metrics_job_and_latest_model,
        metrics_model,
        metrics_model_request_recompute_metrics
    ]


@handle_exceptions
@requires_scope('read:job_metrics')
async def metrics_job(job_id: int, start_date: str=None, end_date: str=None, filters:list=None) -> GetJobMetricsResponse:
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
    dict - A dictionary containing the metrics associated with the job:
        - overall_accuracy (float or none) : The mean accuracy across decisions
        - overall_f1_score (float or none) : The mean F1 score across decisions
        - overall_recall (float or none) : The mean recall across decisions
        - overall_precision (float or none) : The mean precision across decisions
        - time_saved_minutes (float or none) : The time saved by the job in minutes. Calculated as: Average Time spent on investigating an alert * Alerts with correct Arcanna decisions.
        - confusion_matrix (list or none) : The confusion matrix of the model decisions, plot it is as a confusion matrix
        - metrics_per_decision (dict) : Metrics per decision type for the job
        - active_model_id (str or none) : The unique identifier of the active model
        - all_model_ids (list or none) : List of all model identifiers
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

    payload = {}
    if filters:
        payload = {"filters": filters}

    response = requests.post(formatted_url.format(job_id), headers=headers, json=payload)
    return response.json()


@handle_exceptions
@requires_scope('read:job_metrics')
async def metrics_job_and_latest_model(job_id: int, start_date: str=None, end_date: str=None, filters:list=None) -> GetJobAndLatestModelMetricsResponse:
    """
        Fetches the metrics associated with a specific Arcanna job and its active model.
        As part of the request, the metrics of the model will be also recomputed and updated.
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
    dict - A dictionary containing the metrics associated with the job:
        - overall_accuracy (float or none) : The mean accuracy across decisions
        - overall_f1_score (float or none) : The mean F1 score across decisions
        - overall_recall (float or none) : The mean recall across decisions
        - overall_precision (float or none) : The mean precision across decisions
        - time_saved_minutes (float or none) : The time saved by the job in minutes. Calculated as: Average Time spent on investigating an alert * Alerts with correct Arcanna decisions.
        - confusion_matrix (list or none) : The confusion matrix of the model decisions
        - metrics_per_decision (dict) : Metrics per decision type for the job
        - active_model_id (str or none) : The unique identifier of the active model
        - all_model_ids (list or none) : List of all model identifiers
        - active_model_metrics (dict) : The metrics associated with the current model:
            - model_id (str or None): The unique identifier of the model
            - is_recomputing_metrics (bool or None): Indicates if the metrics are being recomputed
            - last_recomputed_timestamp (str or None): The timestamp of the last metrics recomputation
            - overall_accuracy (float or None): The mean accuracy across decisions
            - overall_f1_score (float or None): The mean F1 score across decisions
            - overall_recall (float or None): The mean recall across decisions
            - overall_precision (float or None): The mean precision across decisions
            - confusion_matrix (List[List[int]] or None): The confusion matrix of the model decisions, plot it is as a confusion matrix
            - metrics_per_decision (Dict[str, MetricsPerDecision]): Metrics per decision type
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    formatted_url = METRICS_JOB_AND_LATEST_MODEL_URL + f'?job_id={job_id}&timeout_s=120'

    if start_date:
        formatted_url += f'&start_datetime={start_date}'

    if end_date:
        formatted_url += f'&end_datetime={end_date}'

    payload = {}
    if filters:
        payload = {"filters": filters}

    response = requests.post(formatted_url.format(job_id), headers=headers, json=payload)
    return response.json()


@handle_exceptions
@requires_scope('read:job_metrics')
async def metrics_model(job_id: int, model_id: str) -> GetModelMetricsResponse:
    """
        Fetches the metrics associated with a specific Arcanna model.
    Parameters:
    --------
    job_id (int) : Unique identifier of the job
    model_id (str) : Unique identifier of the model

    Returns:
    --------
    dict - A dictionary containing the metrics associated with the job:
        - model_id (str or None): The unique identifier of the model
        - is_recomputing_metrics (bool or None): Indicates if the metrics are being recomputed
        - last_recomputed_timestamp (str or None): The timestamp of the last metrics recomputation
        - overall_accuracy (float or None): The mean accuracy across decisions
        - overall_f1_score (float or None): The mean F1 score across decisions
        - overall_recall (float or None): The mean recall across decisions
        - overall_precision (float or None): The mean precision across decisions
        - confusion_matrix (List[List[int]] or None): The confusion matrix of the model decisions, plot it is as a confusion matrix
        - metrics_per_decision (Dict[str, MetricsPerDecision]): Metrics per decision type
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    formatted_url = METRICS_MODEL_URL + f'?job_id={job_id}'
    if model_id:
        formatted_url += f'&model_id={model_id}'

    response = requests.get(formatted_url.format(job_id), headers=headers)
    return response.json()


@handle_exceptions
@requires_scope('read:job_metrics', 'execute:recompute_model_metrics')
async def metrics_model_request_recompute_metrics(job_id: int, model_id: str) -> str:
    """
        Initiates the re-computation of metrics for a specific Arcanna model.
    Parameters:
    --------
    job_id (int) : Unique identifier of the job
    model_id (str) : Unique identifier of the model

    Returns:
    --------
    str - A string containing the action status
    """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }
    formatted_url = METRICS_MODEL_URL_REQUEST_RECOMPUTE_METRICS + f'?job_id={job_id}'
    if model_id:
        formatted_url += f'&model_id={model_id}'

    response = requests.post(formatted_url.format(job_id), headers=headers)
    return response.json()
