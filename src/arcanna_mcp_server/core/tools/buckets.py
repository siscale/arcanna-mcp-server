from typing import Annotated, Any, Callable, List, Literal, Optional

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope
from arcanna_mcp_server.core.tools.events import EndDate, Filter, JobId, StartDate, StorageTag, filters_payload

BucketId = Annotated[str, Field(description="Bucket id from the 'id' column of query_buckets, NOT its 'bucket_id'"
                                            " column.")]
BucketIds = Annotated[List[str], Field(description="Bucket ids from the 'id' column of query_buckets.")]
BucketFilters = Annotated[Optional[List[Filter]], Field(
    description="Conditions on decision point values, ANDed. Omit to match every bucket of the job.")]
DecisionFilters = Annotated[Optional[List[str]], Field(
    description="Keep only buckets whose model decision is one of these labels.")]
ConsensusFilters = Annotated[Optional[List[str]], Field(
    description="Keep only buckets whose analyst consensus is one of these labels.")]
QuickFilters = Annotated[Optional[dict], Field(
    description="UI shortcuts: feedback: buckets_with[out]_my_feedback|buckets_with[out]_any_feedback;"
                " training_status: in_model|new; model: misclassified_buckets|old_model_decision;"
                " confidence_score: {min, max}; requiring_attention: [tags].")]
ExcludeProcessed = Annotated[Optional[bool], Field(
    description="Leave out buckets the API key's user already gave feedback on.")]
IncludeProcessed = Annotated[Optional[bool], Field(
    description="Keep only buckets the API key's user already gave feedback on.")]


def export_tools() -> List[Callable]:
    return [
        query_buckets,
        get_bucket,
        get_similar_buckets,
        reprocess_buckets,
        request_bucket_model_update,
        request_bucket_model_update_by_filters,
        approve_bucket_feedback,
        update_bucket_feedback_state,
        delete_buckets,
    ]


@handle_exceptions
@requires_scope('read:event_query')
async def query_buckets(
        job_id: JobId,
        filters: BucketFilters = None,
        decision_filters: DecisionFilters = None,
        consensus_filters: ConsensusFilters = None,
        quick_filters: QuickFilters = None,
        free_search_text: Annotated[Optional[str], Field(description="Free text matched across bucket fields.")]
        = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        storage_tag: StorageTag = None,
        exclude_processed: ExcludeProcessed = None,
        include_processed: IncludeProcessed = None,
        sort_by_column: Annotated[Optional[str], Field(
            description="Sort field; a feature is features_values.<name>. Defaults to the bucket timestamp.")]
        = None,
        sort_order: Annotated[Literal['asc', 'desc'], Field(description="Sort direction.")] = 'asc',
        size: Annotated[int, Field(description="Buckets per page (1-1000).")] = 20,
        page_from: Annotated[int, Field(description="Index of the first bucket, from 0; add size for next page.")]
        = 0,
) -> Any:
    """Page through a job's buckets (a bucket groups events with identical decision point values and is
    labelled as a unit). Returns the page plus total matching.

    Each bucket is a list of {name, value} columns, feature columns flagged is_feature; use its 'id' column
    with the other bucket tools. Use it to review decisions/consensus or find buckets needing feedback. For
    individual events use the event tools; for one bucket in full use get_bucket."""
    return await call('POST', "/api/v2/buckets/query", json={
        "job_id": job_id, "filters": filters_payload(filters), "decision_filters": decision_filters,
        "consensus_filters": consensus_filters, "quick_filters": quick_filters, "free_search_text": free_search_text,
        "start_date": start_date, "end_date": end_date, "storage_tag": storage_tag,
        "exclude_processed": exclude_processed, "include_processed": include_processed,
        "sort_by_column": sort_by_column, "sort_order": sort_order, "size": size, "from": page_from})


@handle_exceptions
@requires_scope('read:event_query')
async def get_bucket(job_id: JobId, bucket_id: BucketId) -> Any:
    """Read one bucket in full: shared feature values (decision_points), analyst consensus, model decision,
    state, consensus_overwritten and is_old_model_decision (true when an older model scored it)."""
    return await call('GET', f"/api/v2/buckets/{job_id}/{bucket_id}")


@handle_exceptions
@requires_scope('read:event_query')
async def get_similar_buckets(job_id: JobId, bucket_id: BucketId) -> Any:
    """List the knowledge-base buckets nearest this one by embedding, with similarity percentages, most
    similar first.

    Use it to find labelled precedents before deciding a bucket. Empty when it has no precedents. For
    event-level precedents use get_similar_events."""
    return await call('POST', f"/api/v2/buckets/{job_id}/{bucket_id}/similar")


@handle_exceptions
@requires_scope('execute:reprocess_events')
async def reprocess_buckets(job_id: JobId, buckets_ids: BucketIds) -> Any:
    """Send every event of these buckets back through the pipeline (picks up a changed model, enrichment or
    integration) without re-ingesting.

    Does not retrain or change labels. Runs in the background: success means accepted, and unknown ids are
    ignored silently. To only revisit the model's decision at the next training use
    request_bucket_model_update."""
    return await call('POST', f"/api/v2/buckets/{job_id}/reprocess", json={"buckets_ids": buckets_ids})


@handle_exceptions
@requires_scope('execute:job_operations')
async def request_bucket_model_update(job_id: JobId, buckets_ids: BucketIds) -> Any:
    """Flag specific buckets so the next training run revisits the model's decision on them. Returns
    buckets_updated, the only confirmation (unknown ids are skipped silently).

    Changes no feedback or labels and does not start training (train_job does). To flag by filter use
    request_bucket_model_update_by_filters."""
    return await call('POST', f"/api/v2/buckets/{job_id}/request-model-update", json={"buckets_ids": buckets_ids})


@handle_exceptions
@requires_scope('execute:job_operations')
async def request_bucket_model_update_by_filters(
        job_id: JobId,
        filters: BucketFilters = None,
        decision_filters: DecisionFilters = None,
        consensus_filters: ConsensusFilters = None,
        quick_filters: QuickFilters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        storage_tag: StorageTag = None,
        exclude_processed: Annotated[Optional[bool], Field(
            description="Leave out buckets the API key's user already gave feedback on (server default true).")]
        = None,
        include_processed: IncludeProcessed = None,
) -> Any:
    """Flag every bucket matching the filters (selected as in query_buckets) so the next training run
    revisits the model's decision on them. Returns buckets_updated.

    With no filters it flags every bucket of the job: preview with query_buckets using the same filters and
    confirm with the user. For a known list of ids use request_bucket_model_update."""
    return await call('POST', "/api/v2/buckets/request_model_update_by_filters", json={
        "job_id": job_id, "filters": filters_payload(filters), "decision_filters": decision_filters,
        "consensus_filters": consensus_filters, "quick_filters": quick_filters, "start_date": start_date,
        "end_date": end_date, "storage_tag": storage_tag, "exclude_processed": exclude_processed,
        "include_processed": include_processed})


@handle_exceptions
@requires_scope('write:event_feedback')
async def approve_bucket_feedback(job_id: JobId, buckets_ids: BucketIds) -> Any:
    """Approve every pending feedback entry on these buckets, from any user, and recompute their consensus.
    Returns updated_count.

    Only approved feedback counts towards retraining. To approve, reject or reopen one user's entry use
    update_bucket_feedback_state."""
    return await call('POST', f"/api/v2/buckets/{job_id}/approve-feedback", json={"buckets_ids": buckets_ids})


@handle_exceptions
@requires_scope('write:event_feedback')
async def update_bucket_feedback_state(
        job_id: JobId,
        bucket_id: BucketId,
        feedback_username: Annotated[str, Field(description="User whose feedback entry on the bucket to change.")],
        new_state: Annotated[Literal['pending', 'approved', 'rejected'], Field(description="State to set.")],
) -> Any:
    """Move one user's feedback on a bucket between pending, approved and rejected, and recompute the
    bucket's consensus.

    Only approved feedback counts towards retraining. Fails if the bucket or that user's entry does not
    exist. To approve all pending feedback on several buckets use approve_bucket_feedback."""
    return await call('POST', f"/api/v2/buckets/{job_id}/{bucket_id}/feedback/state", json={
        "feedback_username": feedback_username, "new_state": new_state})


@handle_exceptions
@requires_scope('delete:buckets')
async def delete_buckets(
        job_id: JobId,
        filters: BucketFilters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        date_field: Annotated[Optional[Literal['last_entry_timestamp', 'bucket_creation_timestamp']], Field(
            description="Bucket timestamp the dates apply to (server default last_entry_timestamp).")] = None,
        confirm: Annotated[bool, Field(description="Must be true to delete; set only after the user agreed.")]
        = False,
) -> Any:
    """Delete every bucket matching filters and dates, together with all their events. Returns
    buckets_deleted and events_deleted.

    Irreversible. With no filters and no dates it deletes ALL the job's buckets and events. Preview with
    query_buckets, confirm with the user first, then call again with confirm=true; without it the server
    rejects the call. To delete events only use delete_events."""
    return await call('DELETE', f"/api/v2/buckets/{job_id}", params={"confirm": str(confirm).lower()}, json={
        "filters": filters_payload(filters), "start_date": start_date, "end_date": end_date,
        "date_field": date_field})
