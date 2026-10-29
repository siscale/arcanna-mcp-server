from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import call
from arcanna_mcp_server.common.scopes import requires_scope


class Filter(BaseModel):
    field: str = Field(description="Event field name, as listed by get_filter_fields.")
    operator: Literal["is", "is not", "is one of", "is not one of", "starts with", "not starts with", "contains",
                      "not contains", "exists", "doesn't exist", "less than", "less than or equal to",
                      "greater than", "greater than or equal to"] = Field(description="Comparison to apply.")
    value: Optional[Any] = Field(default=None, description="A list for 'is one of'/'is not one of'; omit for"
                                                           " 'exists'/\"doesn't exist\".")


def filters_payload(filters: Optional[List[Filter]]) -> Optional[List[dict]]:
    if filters is None:
        return None
    return [item.model_dump(exclude_none=True) if isinstance(item, BaseModel) else item for item in filters]


JobId = Annotated[int, Field(description="Numeric id of the job.")]
EventId = Annotated[str, Field(description="Event id, as in the event_id field of query results.")]
JobIds = Annotated[Optional[Union[List[int], int]], Field(
    description="Job id or ids. Omit this and job_titles to cover every job the API key can read.")]
JobTitles = Annotated[Optional[Union[List[str], str]], Field(description="Job title or titles, instead of job_ids.")]
Filters = Annotated[Optional[List[Filter]], Field(
    description="Conditions ANDed together. Omit to match every event of the job.")]
StartDate = Annotated[Optional[str], Field(description="Lower bound on date_field: ISO 8601 or ES date math (now-7d).")]
EndDate = Annotated[Optional[str], Field(description="Upper bound on date_field: ISO 8601 or ES date math (now).")]
DateField = Annotated[Optional[str], Field(
    description="Field the dates apply to: @timestamp (alert time, default) or timestamp_inference (ingest time).")]
StorageTag = Annotated[Optional[str], Field(
    description="Restrict to one storage of the job. Omit for every storage.")]
StorageName = Annotated[Optional[str], Field(
    description="Storage holding the event, for multi-storage jobs. Omit to use the most recent match.")]


def export_tools() -> List[Callable]:
    return [
        query_arcanna_events,
        count_events,
        get_field_stats,
        get_field_groups,
        get_filter_fields,
        get_fields_mapping,
        get_event_explanation,
        get_similar_events,
        get_event_agentic_workflows,
        get_job_outliers,
        add_feedback_to_event,
        clear_event_feedback,
        add_agentic_notes,
        reprocess_events,
        reprocess_event_by_id,
        delete_events,
        ingest_event,
        export_event_by_id,
        transfer_event,
    ]


@handle_exceptions
@requires_scope('read:event_query')
async def query_arcanna_events(
        job_ids: JobIds = None,
        job_titles: JobTitles = None,
        query_body: Annotated[Optional[Dict[str, Any]], Field(
            description="Elasticsearch search body: query plus optional size, sort, aggs, track_total_hits. Key"
                        " fields: @timestamp, timestamp_inference, arcanna.original_id.keyword (alert id),"
                        " arcanna.result_label.keyword (decision), arcanna.consensus.keyword,"
                        " arcanna.bucket_state.keyword, arcanna.outlier_flag, arcanna.confidence_score.")] = None,
        decision_points_only: Annotated[bool, Field(
            description="Return only event ids and decision points, not the arcanna fields or raw event.")] = False,
        size: Annotated[Optional[int], Field(
            description="Max events returned (server default 5). A size in query_body wins.")] = None,
) -> Any:
    """Search job events with a raw Elasticsearch query body; the flexible, expensive option.

    Call get_fields_mapping first for other field names and their ES types. Keep size small; for
    distributions use size 0 with aggs. Use @timestamp for time ranges unless the user means ingest time.
    Do NOT use it only to count (count_events), to break events down by one field (get_field_groups), or to
    read why the model decided (get_event_explanation). On a server error, show it and ask the user how to
    continue."""
    return await call('POST', "/api/v2/events/raw_es_query", json={
        "job_ids": job_ids, "job_titles": job_titles, "query_body": query_body,
        "decision_points_only": decision_points_only or None, "size": size})


@handle_exceptions
@requires_scope('read:event_query')
async def count_events(
        job_id: JobId,
        filters: Filters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        date_field: DateField = None,
        storage_tag: StorageTag = None,
) -> Any:
    """Count a job's events matching filters and a date range. Returns {events_count}.

    Far cheaper than fetching events: use it for any "how many" question and to size a filter before
    reprocess_events or delete_events, which act on the same set. Do NOT fetch events with
    query_arcanna_events just to count them; for per-value counts use get_field_groups."""
    return await call('POST', "/api/v2/events/count", json={
        "job_id": job_id, "filters": filters_payload(filters), "start_date": start_date, "end_date": end_date,
        "date_field": date_field, "storage_tag": storage_tag})


@handle_exceptions
@requires_scope('read:event_query')
async def get_field_stats(
        job_id: JobId,
        field_name: Annotated[str, Field(description="Plain event field name; text fields use their keyword"
                                                     " subfield automatically.")],
        top_values_size: Annotated[int, Field(description="How many top values to return (1-100).")] = 10,
) -> Any:
    """Profile one field over ALL of a job's events: top values with counts and percentages, how many events
    have or miss it, and an approximate distinct count.

    Use it to learn what values a field holds before writing filters. It ignores dates and filters; for a
    filtered or time-bound breakdown use get_field_groups. Rejects fields the job does not contain."""
    return await call('POST', "/api/v2/events/field/stats", json={
        "job_id": job_id, "field_name": field_name, "top_values_size": top_values_size})


@handle_exceptions
@requires_scope('read:event_query')
async def get_field_groups(
        job_id: JobId,
        field_name: Annotated[str, Field(description="Event field to group by, e.g. host.name.")],
        filters: Filters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        date_field: DateField = None,
        storage_tag: StorageTag = None,
        size: Annotated[int, Field(description="How many groups to return, largest first (1-100).")] = 10,
) -> Any:
    """Count a job's events per value of one field, after filters and a date range; largest groups first.

    Answers "which hosts/users/rules produce the most alerts (last week, with decision X)". Returns total,
    groups [{value, count}] and other_count. For an unfiltered profile with missing/distinct counts use
    get_field_stats; for a single total use count_events; to list events use query_arcanna_events."""
    return await call('POST', "/api/v2/events/field/groups", json={
        "job_id": job_id, "field_name": field_name, "filters": filters_payload(filters), "start_date": start_date,
        "end_date": end_date, "date_field": date_field, "storage_tag": storage_tag, "size": size})


@handle_exceptions
@requires_scope('read:event_query')
async def get_filter_fields(job_ids: JobIds = None, job_titles: JobTitles = None) -> Any:
    """List the fields usable in filters, with the operators each accepts and the jobs that have it.

    Call it before building filters for count_events, get_field_groups, reprocess_events, delete_events or
    query_buckets. For Elasticsearch field types (query_arcanna_events) use get_fields_mapping."""
    return await call('POST', "/api/v2/filters/fields", json={"job_ids": job_ids, "job_titles": job_titles})


@handle_exceptions
@requires_scope('read:event_query')
async def get_fields_mapping(job_ids: JobIds = None, job_titles: JobTitles = None) -> Any:
    """Map every event field name of the selected jobs to its Elasticsearch type (flat dict).

    Use it to pick exact field names (e.g. the .keyword variant) for query_arcanna_events query bodies and
    aggregations. It has no operator info; for filters use get_filter_fields."""
    return await call('POST', "/api/v2/filters/fields_mapping", json={"job_ids": job_ids, "job_titles": job_titles})


@handle_exceptions
@requires_scope('read:event_summary')
async def get_event_explanation(job_id: JobId, event_id: EventId, storage_name: StorageName = None) -> Any:
    """Read the model's written summary of an event and the reasoning behind its decision.

    Each part has its own processing_status (processing/finished) and error; check it before treating empty
    text as "no reasoning". Use it for "why was this escalated/dropped"; do NOT query events for that."""
    return await call('POST', f"/api/v2/events/{job_id}/{event_id}/explanation",
                      params={"storage_name": storage_name})


@handle_exceptions
@requires_scope('read:event_query')
async def get_similar_events(job_id: JobId, event_id: EventId) -> Any:
    """List the events most similar to this one, with similarity scores, most similar first.

    Cheap precomputed lookup; use it to find precedents for an event under review. Empty for events scored
    before similarity was recorded. For bucket-level precedents use get_similar_buckets."""
    return await call('POST', f"/api/v2/events/{job_id}/{event_id}/similar")


@handle_exceptions
@requires_scope('read:event_query')
async def get_event_agentic_workflows(job_id: JobId, event_id: EventId) -> Any:
    """List the agentic workflow runs recorded on an event and what each one recorded.

    An empty list is normal: most events are never touched by a workflow."""
    return await call('POST', f"/api/v2/events/{job_id}/{event_id}/agentic-workflows")


@handle_exceptions
@requires_scope('read:job_metadata')
async def get_job_outliers(
        job_id: JobId,
        limit: Annotated[int, Field(description="Max outliers returned; total is always reported.")] = 50,
) -> Any:
    """List a job's outlier events (unusual relative to what the model has seen): event_id, bucket_id and
    UI links for each.

    The endpoint returns every outlier, so the tool trims to limit and adds total. To filter or count
    outliers by date use count_events with arcanna.outlier_flag is true."""
    result = await call('GET', f"/api/v2/events/{job_id}/outliers")
    outliers = result.get("outliers", []) if isinstance(result, dict) else []
    return {"total": len(outliers), "outliers": outliers[:limit]}


@handle_exceptions
@requires_scope('write:event_feedback')
async def add_feedback_to_event(
        job_id: JobId,
        event_id: EventId,
        label: Annotated[str, Field(description="Label id or name configured on the job, e.g. Escalate or Drop.")],
        storage_name: StorageName = None,
        feedback_approval_state: Annotated[Optional[Literal['pending', 'approved', 'rejected']], Field(
            description="Approval state to record. Omit for the job's default.")] = None,
        metadata: Annotated[Optional[Dict[str, str]], Field(
            description="Free-form key/value pairs stored with the feedback.")] = None,
) -> Any:
    """Label an event with the analyst's decision; approved feedback trains future models.

    Escalate means investigate, Drop means false positive. An unknown label fails and lists the valid ones.
    To undo your label use clear_event_feedback; for bucket-labelled jobs see the bucket tools."""
    return await call('PUT', f"/api/v2/events/{job_id}/{event_id}/feedback", params={
        "feedback_label": label, "feedback_approval_state": feedback_approval_state, "storage_name": storage_name},
        json=metadata)


@handle_exceptions
@requires_scope('write:event_feedback')
async def clear_event_feedback(job_id: JobId, event_id: EventId, storage_name: StorageName = None) -> Any:
    """Remove the API key user's own feedback from one event and recompute its consensus.

    Other users' feedback stays; a no-op if this user never labelled it. Does not affect jobs that take
    feedback on buckets. To change a label, just call add_feedback_to_event again."""
    return await call('DELETE', f"/api/v2/events/{job_id}/{event_id}/feedback", params={"storage_name": storage_name})


@handle_exceptions
@requires_scope('write:event_agentic_notes')
async def add_agentic_notes(
        job_id: JobId,
        event_id: EventId,
        agent_notes: Annotated[str, Field(description="The agent's findings, as text.")],
        agent_saved_objects: Annotated[Optional[dict], Field(
            description="Structured objects to store with the notes (IOCs, verdicts...).")] = None,
        workflow_name: Annotated[Optional[str], Field(description="Name of the workflow producing the notes.")]
        = None,
        workflow_id: Annotated[Optional[str], Field(description="Id of that workflow.")] = None,
        session_id: Annotated[Optional[str], Field(description="Session id of the workflow run.")] = None,
) -> Any:
    """Append an agent-generated entry (notes and saved objects) to an event.

    Existing entries are kept; the server sets the timestamp. Read entries back with
    get_event_agentic_workflows. Does not change the event's label; use add_feedback_to_event for that."""
    return await call('POST', f"/api/v2/events/{job_id}/{event_id}/add_agentic_notes", json={
        "agent_notes": agent_notes, "agent_saved_objects": agent_saved_objects or {}, "workflow_name": workflow_name,
        "workflow_id": workflow_id, "session_id": session_id})


@handle_exceptions
@requires_scope('execute:reprocess_events')
async def reprocess_events(
        job_id: JobId,
        filters: Filters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        date_field: DateField = None,
        storage_tag: StorageTag = None,
) -> Any:
    """Mark every event matching filters and dates for the pipeline to score again (new model, enrichment or
    integrations) without re-ingesting. Returns events_updated.

    Asynchronous: events are reprocessed later. With no filters and no dates it marks the whole job, so check
    the size with count_events first and confirm with the user. For one event use reprocess_event_by_id, for
    buckets reprocess_buckets."""
    return await call('POST', f"/api/v2/events/{job_id}/reprocess", json={
        "filters": filters_payload(filters), "start_date": start_date, "end_date": end_date,
        "date_field": date_field, "storage_tag": storage_tag})


@handle_exceptions
@requires_scope('execute:reprocess_events')
async def reprocess_event_by_id(job_id: JobId, event_id: EventId) -> Any:
    """Mark one event for the pipeline to score again. Asynchronous; for many events use reprocess_events."""
    return await call('POST', f"/api/v2/events/{job_id}/{event_id}/reprocess")


@handle_exceptions
@requires_scope('delete:events')
async def delete_events(
        job_id: JobId,
        filters: Filters = None,
        start_date: StartDate = None,
        end_date: EndDate = None,
        date_field: DateField = None,
        storage_tag: StorageTag = None,
        confirm: Annotated[bool, Field(description="Must be true to delete; set only after the user agreed.")]
        = False,
) -> Any:
    """Delete every event of a job matching filters and dates. Returns events_deleted.

    Irreversible. With no filters and no dates it deletes ALL the job's events. First run count_events with
    the same arguments, tell the user what will be removed and confirm with the user first, then call again
    with confirm=true; without it the server rejects the call. To delete whole buckets use delete_buckets."""
    return await call('DELETE', f"/api/v2/events/{job_id}", params={"confirm": str(confirm).lower()}, json={
        "filters": filters_payload(filters), "start_date": start_date, "end_date": end_date,
        "date_field": date_field, "storage_tag": storage_tag})


@handle_exceptions
@requires_scope('write:events')
async def ingest_event(
        job_id: JobId,
        raw_body: Annotated[dict, Field(description="The event payload; must contain the fields the job requires.")],
        storage_name: Annotated[Optional[str], Field(
            description="Storage to save the event in. Omit for the first one the API key can use.")] = None,
) -> Any:
    """Send one raw event (JSON) to a job, which ingests it under a new event id and decides on it
    asynchronously. Returns the ingestion status and new id.

    Missing required fields are rejected with the list of what is missing. To copy an existing event to
    another job use transfer_event."""
    return await call('POST', "/api/v1/events/", json={
        "job_id": job_id, "raw_body": raw_body, "storage_name": storage_name})


@handle_exceptions
@requires_scope('read:event_export')
async def export_event_by_id(job_id: JobId, event_id: EventId, storage_name: StorageName = None) -> Any:
    """Export one event's full stored JSON (arcanna_event), including Arcanna's transformations and fields.

    Large; for searching or a few fields use query_arcanna_events, for the decision rationale
    get_event_explanation."""
    return await call('GET', f"/api/v1/events/{job_id}/{event_id}/export", params={"storage_name": storage_name})


@handle_exceptions
@requires_scope('read:event_export', 'write:events')
async def transfer_event(
        source_job_id: Annotated[int, Field(description="Job that currently holds the event.")],
        event_id: EventId,
        destination_job_id: Annotated[int, Field(description="Job that will ingest the copy.")],
        source_storage_name: Annotated[Optional[str], Field(
            description="Storage of the event in the source job, for multi-storage jobs.")] = None,
        destination_storage_name: Annotated[Optional[str], Field(
            description="Storage to ingest into on the destination job, for multi-input jobs.")] = None,
) -> Any:
    """Copy an event from one job to another: exports it from the source and ingests it into the destination
    under a new id. The source event is kept. Returns the destination ingestion status."""
    exported = await call('GET', f"/api/v1/events/{source_job_id}/{event_id}/export",
                          params={"storage_name": source_storage_name})
    event_source = exported.get("arcanna_event") if isinstance(exported, dict) else None
    if event_source is None:
        return {"status": "NOK",
                "error_message": f"Event with id {event_id} not found in source job with id {source_job_id}"}
    return await call('POST', "/api/v1/events/", json={
        "job_id": destination_job_id, "raw_body": event_source, "storage_name": destination_storage_name})
