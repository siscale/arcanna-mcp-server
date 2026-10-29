from typing import Annotated, Any, Callable, List, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

JobId = Annotated[int, Field(description="Numeric id of the job.")]
ModelId = Annotated[str, Field(description="Model id of the job, e.g. from active_model_id / all_model_ids of"
                                           " get_job_metrics; the .hdf5 suffix is optional.")]
JobIds = Annotated[Optional[List[int]], Field(description="Job ids to include. Omit for all jobs.")]
StartDate = Annotated[Optional[str], Field(description="Only events newer than this ISO 8601 date/time.")]
EndDate = Annotated[Optional[str], Field(description="Only events older than this ISO 8601 date/time.")]
Filters = Annotated[Optional[List[dict]], Field(
    description="AND-combined event filters [{field, operator, value}]. Operators: is, is not, is one of, is not"
                " one of, starts with, not starts with, contains, not contains, exists, doesn't exist. Useful fields:"
                " arcanna.result_label (decision), arcanna.consensus, arcanna.outlier_flag,"
                " arcanna.bucket_state / arcanna.knowledge_base_state.")]


def export_tools() -> List[Callable]:
    return [
        get_job_metrics,
        get_job_and_model_metrics,
        get_model_metrics,
        request_model_metrics_recompute,
        get_platform_metrics,
        get_internal_metrics,
        get_field_metrics,
        export_feedback,
        set_production_date,
    ]


def _filters_body(filters: Optional[List[dict]]) -> Optional[dict]:
    return {"filters": filters} if filters else None


@handle_exceptions
@requires_scope('read:job_metrics')
async def get_job_metrics(job_id: JobId, start_date: StartDate = None, end_date: EndDate = None,
                          filters: Filters = None) -> Any:
    """How well a job's decisions match analyst feedback, over a period (all time when no dates).

    Returns overall accuracy/f1/precision/recall, metrics_per_decision, confusion_matrix, time_saved_minutes
    (avg investigation time x correct decisions), feedback and event counts, active_model_id, all_model_ids.
    Fast: nothing is recomputed. For the active model's own metrics use get_job_and_model_metrics."""
    return await call('POST', "/api/v2/metrics/job",
                      params={"job_id": job_id, "start_datetime": start_date, "end_datetime": end_date},
                      json=_filters_body(filters))


@handle_exceptions
@requires_scope('read:job_metrics', 'execute:recompute_model_metrics')
async def get_job_and_model_metrics(job_id: JobId, start_date: StartDate = None, end_date: EndDate = None,
                                    filters: Filters = None) -> Any:
    """Job metrics (as get_job_metrics) plus active_model_metrics of the job's current model (accuracy/f1/
    precision/recall, per-decision, confusion matrix on its training data, last_recomputed_timestamp).

    Slow: recomputes the model metrics first and waits up to 2 minutes. Prefer get_job_metrics when the model
    part is not needed."""
    return await call('POST', "/api/v2/metrics/job_and_latest_model",
                      params={"job_id": job_id, "start_datetime": start_date, "end_datetime": end_date,
                              "timeout_s": 120},
                      json=_filters_body(filters))


@handle_exceptions
@requires_scope('read:job_metrics')
async def get_model_metrics(job_id: JobId, model_id: ModelId) -> Any:
    """Stored metrics of one model of a job, including inactive ones: overall accuracy/f1/precision/recall,
    per-decision metrics, confusion matrix, knowledge base counts, is_recomputing_metrics and
    last_recomputed_timestamp.

    Fast, never recomputes; if stale call request_model_metrics_recompute and read again later."""
    return await call('GET', "/api/v2/metrics/model", params={"job_id": job_id, "model_id": model_id})


@handle_exceptions
@requires_scope('execute:recompute_model_metrics')
async def request_model_metrics_recompute(job_id: JobId, model_id: ModelId) -> Any:
    """Queue a recomputation of one model's metrics and return at once with a status.

    The new metrics are not returned: read them later with get_model_metrics (is_recomputing_metrics shows
    progress)."""
    return await call('POST', "/api/v2/metrics/model/request_recompute_metrics",
                      params={"job_id": job_id, "model_id": model_id})


@handle_exceptions
@requires_scope('read:platform_monitoring')
async def get_platform_metrics(
        job_ids: JobIds = None,
        aggregation_time_interval: Annotated[str, Field(
            description="Bucket size in days, e.g. '1d', '7d', '30d'.")] = '7d',
) -> Any:
    """Platform activity over time: ingestion and decision volumes across jobs, bucketed per interval.

    Shows how busy the platform is, not model quality; for accuracy use get_job_metrics or get_model_metrics."""
    return await call('POST', "/api/v2/metrics/platform_metrics",
                      params={"job_ids": job_ids, "aggregation_time_interval": aggregation_time_interval})


@handle_exceptions
@requires_scope('read:platform_monitoring')
async def get_internal_metrics(
        job_ids: JobIds = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        aggregation_time_interval: Annotated[Optional[str], Field(
            description="Split by this interval, e.g. '7d'. Omit for no time split.")] = None,
        latest_n_models: Annotated[int, Field(
            description="Latest models to include per job (the model in use is always added).")] = 2,
        confidence_score_threshold: Annotated[float, Field(
            description="0-100 split between low and high confidence decisions.")] = 60,
        include_field_stats: Annotated[bool, Field(
            description="Also include precomputed decision point field statistics.")] = False,
) -> Any:
    """Comprehensive per-job report: job, model and feedback metrics, confidence split, optionally field stats.

    Heavy: may recompute model metrics (waits up to 2 minutes); usernames are obfuscated. For one job's
    accuracy prefer get_job_metrics."""
    return await call('POST', "/api/v2/metrics/internal_metrics", params={
        "job_ids": job_ids, "start_datetime": start_date, "end_datetime": end_date,
        "aggregation_time_interval": aggregation_time_interval, "latest_n_models_to_recompute": latest_n_models,
        "confidence_score_threshold": confidence_score_threshold, "include_field_stats": include_field_stats})


@handle_exceptions
@requires_scope('read:job_metrics')
async def get_field_metrics(
        job_ids: JobIds = None,
        decision_points_only: Annotated[bool, Field(
            description="Only decision point fields; false for every event field.")] = True,
        get_top_values: Annotated[bool, Field(description="Include each field's most frequent values.")] = True,
) -> Any:
    """Per-field statistics of the jobs' events (coverage, cardinality, top values).

    Use it to judge which fields make good decision points. Can be large with decision_points_only=false."""
    return await call('POST', "/api/v2/metrics/field_metrics", params={
        "job_ids": job_ids, "decision_points_only": decision_points_only, "get_top_values": get_top_values})


@handle_exceptions
@requires_scope('read:job_metrics')
async def export_feedback(job_ids: JobIds = None, start_date: StartDate = None, end_date: EndDate = None) -> Any:
    """Export raw analyst feedback documents (who labelled what, when) for the jobs and period.

    Can be very large: always narrow by job and dates. For aggregated feedback quality use get_job_metrics."""
    return await call('POST', "/api/v2/metrics/export_feedback",
                      params={"job_ids": job_ids, "start_datetime": start_date, "end_datetime": end_date})


@handle_exceptions
@requires_scope('execute:recompute_model_metrics', 'read:job_metrics')
async def set_production_date(
        job_id: JobId,
        production_date: Annotated[str, Field(
            description="ISO 8601 timestamp the model went into production; only later events count.")],
) -> Any:
    """Set when a job's model went into production, so production accuracy counts only events after it.

    Triggers a recomputation of the current model's metrics."""
    return await call('PUT', "/api/v2/metrics/production_date",
                      params={"job_id": job_id, "production_date": production_date})
