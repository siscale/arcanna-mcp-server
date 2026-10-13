from typing import Annotated, Any, Callable, List, Literal, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope

JobId = Annotated[int, Field(description="Numeric id of the job.")]
AutoId = Annotated[str, Field(description="Job-local slot id of the input integration (auto_id in get_job_status"
                                          " components), not the integration's own id.")]
RequestId = Annotated[str, Field(description="Id of the validation run, as returned by submit or history.")]


def export_tools() -> List[Callable]:
    return [
        start_job,
        stop_job,
        train_job,
        get_job_status,
        get_job_input_state,
        reset_job_input_state,
        submit_training_config_validation,
        get_training_config_validation,
        list_training_config_validations,
        cancel_training_config_validation,
    ]


@handle_exceptions
@requires_scope('execute:job_operations')
async def start_job(job_id: JobId) -> Any:
    """Start a job's ingestion pipeline.

    Queues the start and returns immediately; check get_job_status to confirm it runs.
    Does NOT train the model, use train_job for that."""
    return await call('POST', f"/api/v2/jobs/{job_id}/start")


@handle_exceptions
@requires_scope('execute:job_operations')
async def stop_job(job_id: JobId) -> Any:
    """Stop a job's ingestion pipeline.

    Events, feedback and the trained model are kept; start_job resumes ingestion."""
    return await call('POST', f"/api/v2/jobs/{job_id}/stop")


@handle_exceptions
@requires_scope('execute:job_operations')
async def train_job(job_id: JobId) -> Any:
    """Retrain a job's model from the approved feedback.

    Asynchronous: returns when training starts, not when it finishes (poll get_job_status, model section).
    Does not affect ingestion. To compare decision point sets without changing the model, use
    submit_training_config_validation instead."""
    return await call('POST', f"/api/v2/jobs/{job_id}/train")


@handle_exceptions
@requires_scope('read:job_metadata')
async def get_job_status(job_id: JobId) -> Any:
    """One-call job health: run state, last error, ingestion counters, pipeline integrations with validity,
    last trained model and feedback counts (including pending approvals).

    Use it first when asked whether a job works. Cheap, reads stored status only; to test an integration's
    connection use check_integration_health."""
    return await call('GET', f"/api/v2/jobs/{job_id}/status")


@handle_exceptions
@requires_scope('read:resources')
async def get_job_input_state(job_id: JobId, auto_id: AutoId) -> Any:
    """Read where one job input resumes ingesting from (its stored read position).

    Returns {} when the input has not ingested yet."""
    return await call('GET', f"/api/v2/jobs/{job_id}/input-state", params={"auto_id": auto_id})


@handle_exceptions
@requires_scope('write:resources')
async def reset_job_input_state(job_id: JobId, auto_id: AutoId) -> Any:
    """Clear one job input's read position so its next run re-reads the source from the beginning.

    Irreversible, and the job will re-ingest events it has already seen. Confirm with the user first."""
    return await call('POST', f"/api/v2/jobs/{job_id}/reset-input-state", params={"auto_id": auto_id})


@handle_exceptions
@requires_scope('execute:job_operations')
async def submit_training_config_validation(
        job_id: JobId,
        configurations: Annotated[List[dict], Field(
            description="Candidate decision point sets, each scored against the job's current set (always included"
                        " as baseline, do not repeat it).")],
        buckets_cutoff_date: Annotated[Optional[str], Field(
            description="Use only buckets whose last entry is newer than this timestamp.")] = None,
        iterations: Annotated[int, Field(
            description="Train/score rounds per configuration; more is steadier and proportionally slower.")] = 1,
        seed: Annotated[Optional[int], Field(description="Fix to make the splits repeatable.")] = None,
        split_strategy: Annotated[Literal['random', 'date', 'k-fold'], Field(
            description="random picks validation buckets at random, date takes the newest, k-fold rotates folds.")]
        = 'random',
        validation_ratio: Annotated[float, Field(description="Fraction of labelled data held back for scoring.")]
        = 0.2,
) -> Any:
    """Start an offline experiment comparing alternative decision point sets with the job's current one.

    Changes nothing on the job. Returns a request_id at once; the run takes minutes, so poll
    get_training_config_validation. Warnings flag candidates unlikely to be informative."""
    return await call('POST', f"/api/v2/jobs/{job_id}/training-config-validation", json={
        "configurations": configurations, "buckets_cutoff_date": buckets_cutoff_date, "iterations": iterations,
        "seed": seed, "split_strategy": split_strategy, "validation_ratio": validation_ratio})


@handle_exceptions
@requires_scope('read:job_metrics')
async def get_training_config_validation(
        job_id: JobId,
        request_id: Annotated[Optional[str], Field(
            description="Validation run to read. Omit for the job's latest run.")] = None,
) -> Any:
    """Poll a training config validation run: its state and, once finished, the score of every configuration.

    Use list_training_config_validations to find older runs."""
    if request_id is None:
        return await call('GET', f"/api/v2/jobs/{job_id}/training-config-validation")
    return await call('GET', f"/api/v2/jobs/{job_id}/training-config-validation/{request_id}")


@handle_exceptions
@requires_scope('read:job_metrics')
async def list_training_config_validations(job_id: JobId) -> Any:
    """List the job's past training config validation runs, newest first."""
    return await call('GET', f"/api/v2/jobs/{job_id}/training-config-validation/history")


@handle_exceptions
@requires_scope('execute:job_operations')
async def cancel_training_config_validation(job_id: JobId, request_id: RequestId) -> Any:
    """Cancel a running training config validation; partial results are discarded. A finished run is left as is."""
    return await call('POST', f"/api/v2/jobs/{job_id}/training-config-validation/{request_id}/cancel")
