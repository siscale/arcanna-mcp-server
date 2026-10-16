from typing import Annotated, Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import AGENTS, call
from arcanna_mcp_server.common.scopes import requires_scope

BASE = "/api/v1/agents-workflow"
HITL_TOOL_NAME = "request_human_input"
LAST_EVENTS = 5
CONTENT_LIMIT = 2000


class EnvVariable(BaseModel):
    name: str = Field(description="Name of the variable.")
    value: str = Field(description="Value of the variable.")
    is_secret: bool = Field(default=False, description="Whether the value is a secret (masked in the UI).")
    should_encrypt: bool = Field(default=False, description="Whether the value is stored encrypted.")


class WorkflowSettings(BaseModel):
    limits: Optional[Dict[str, Any]] = Field(
        default=None, description="Resource limits, e.g. {cpu_time_limits_seconds: 3, memory_limits_mb: 30}.")


WorkflowId = Annotated[str, Field(description="Id of the agentic workflow, as returned by list_agentic_workflows.")]
SessionId = Annotated[str, Field(description="Id of the workflow run session, as returned by the run.")]
SourceCode = Annotated[str, Field(description="Python source defining the agents. The root_agent's name and"
                                              " description become the workflow's name and description.")]
Settings = Annotated[Optional[WorkflowSettings], Field(description="Resource settings; omit for server defaults.")]
PreviousSession = Annotated[Optional[str], Field(
    description="Session id to continue an existing conversation; omit to start a new session.")]

# The upsert endpoint resets omitted flags to their defaults, so an update re-sends the stored ones.
_KEPT_ON_UPDATE = ("is_shared", "use_in_assistant", "memory_enabled", "persistent_workflow_sessions",
                   "remove_agentic_tool_calls", "tags", "selected_model", "is_draft")


def export_tools() -> List[Callable]:
    return [
        list_agentic_workflows,
        get_agentic_workflow_by_id,
        create_agentic_workflow,
        update_agentic_workflow,
        run_agentic_workflow,
        test_agentic_workflow,
        list_agent_tools,
        list_llm_providers,
        get_workflow_session,
        answer_workflow_decision,
        continue_workflow_session,
        stop_workflow_sessions,
    ]


def _env(env_variables: Optional[List[EnvVariable]]) -> Optional[List[dict]]:
    return [variable.model_dump() for variable in env_variables] if env_variables else None


@handle_exceptions
@requires_scope('read:agents')
async def list_agentic_workflows() -> Any:
    """List all agentic workflows as [{id, name, description, is_shared}].

    Use get_agentic_workflow_by_id for the source code and settings of one workflow."""
    response = await call('GET', f"{BASE}/list", service=AGENTS)
    entries = response.get("entries") if isinstance(response, dict) else None
    if entries is None:
        return response
    return [{"id": entry.get("id"), "name": entry.get("name"), "description": entry.get("description"),
             "is_shared": entry.get("is_shared", False)} for entry in entries]


@handle_exceptions
@requires_scope('read:agents')
async def get_agentic_workflow_by_id(
        workflow_id: WorkflowId,
        commit_hash: Annotated[Optional[str], Field(
            description="Version of the workflow to return. Omit for the latest.")] = None,
) -> Any:
    """Fetch one agentic workflow in full: source code, env variables (secrets masked), settings, flags."""
    return await call('GET', f"{BASE}/{workflow_id}", service=AGENTS, params={"commit_hash": commit_hash})


@handle_exceptions
@requires_scope('write:agents')
async def create_agentic_workflow(
        source_code: SourceCode,
        settings: Settings = None,
        env_variables: Annotated[Optional[List[EnvVariable]], Field(
            description="Environment variables injected into the workflow.")] = None,
) -> Any:
    """Create an agentic workflow from Python source. The code is validated first; errors come back as the
    error message. Returns {workflow_id, commit_hash}.

    Try code without saving it via test_agentic_workflow. To change an existing workflow use
    update_agentic_workflow, not this."""
    return await call('POST', f"{BASE}/upsert", service=AGENTS, json={
        "source_code": source_code, "settings": settings.model_dump() if settings else None,
        "env_variables": _env(env_variables)})


@handle_exceptions
@requires_scope('write:agents')
async def update_agentic_workflow(
        workflow_id: WorkflowId,
        source_code: SourceCode,
        settings: Settings = None,
        env_variables: Annotated[Optional[List[EnvVariable]], Field(
            description="Omit to keep the existing variables; a list replaces them all.")] = None,
) -> Any:
    """Replace the source code (and optionally settings / env variables) of an existing workflow, creating a
    new version. Sharing, assistant and memory flags, tags and model are kept. Returns {workflow_id, commit_hash}.

    Send the full source, not a diff: read it first with get_agentic_workflow_by_id."""
    existing = await call('GET', f"{BASE}/{workflow_id}", service=AGENTS)
    kept = {key: existing.get(key) for key in _KEPT_ON_UPDATE}
    return await call('POST', f"{BASE}/upsert", service=AGENTS, json={
        **kept, "id": workflow_id, "source_code": source_code,
        "settings": settings.model_dump() if settings else existing.get("settings"),
        "env_variables": _env(env_variables)})


@handle_exceptions
@requires_scope('execute:agents')
async def run_agentic_workflow(
        workflow_id: WorkflowId,
        workflow_input: Annotated[Optional[str], Field(
            description="Input prompt. Omit only to resume a session after answer_workflow_decision.")] = None,
        session_id: PreviousSession = None,
) -> Any:
    """Run a saved agentic workflow and wait for it to finish. Returns {session_id, workflow_result: [events]}.

    If the workflow pauses for a human decision, the run returns early: call get_workflow_session with the
    session_id, then answer_workflow_decision, then call this again with that
    session_id and no input. To try unsaved code use test_agentic_workflow."""
    return await call('POST', f"{BASE}/run/{workflow_id}", service=AGENTS, json={
        "input": workflow_input, "wait_for_completion": True, "session_id": session_id})


@handle_exceptions
@requires_scope('execute:agents')
async def test_agentic_workflow(
        workflow_input: Annotated[str, Field(description="Input prompt for the workflow.")],
        source_code: Annotated[str, Field(description="Python source defining the agents to try.")],
        session_id: PreviousSession = None,
        env_variables: Annotated[Optional[List[EnvVariable]], Field(
            description="Environment variables injected into the test run.")] = None,
) -> Any:
    """Run unsaved workflow source code once and wait for the result, without creating a saved workflow.
    Returns {session_id, workflow_id (draft), workflow_result: [events]}.

    Use it to iterate on code before create_agentic_workflow / update_agentic_workflow. HITL pauses are
    handled as in run_agentic_workflow."""
    return await call('POST', f"{BASE}/test/run", service=AGENTS, json={
        "user_input": workflow_input, "wait_for_completion": True, "source_code": source_code,
        "session_id": session_id, "env_variables": _env(env_variables)})


@handle_exceptions
@requires_scope('read:agents')
async def list_agent_tools() -> Any:
    """List the MCP tools that agents inside agentic workflows can call in Arcanna's agent runtime.

    These are the workflow runtime's tools, not the tools of this MCP server."""
    return await call('GET', "/api/v1/tools-discovery", service=AGENTS)


@handle_exceptions
@requires_scope('read:agents')
async def list_llm_providers() -> Any:
    """List the LLM integrations usable as models in agentic workflows: [{integration_id, provider,
    available_models}]. Use it to pick the model/provider the workflow code references."""
    return await call('GET', f"{BASE}/llm-providers", service=AGENTS)


def _compact_event(event: dict) -> dict:
    content = event.get("content")
    if isinstance(content, str) and len(content) > CONTENT_LIMIT:
        content = content[:CONTENT_LIMIT] + "...[truncated]"
    compact = {"author": event.get("author"), "content": content, "final": event.get("final"),
               "hitl_event_id": event.get("hitl_event_id"), "decision": event.get("decision")}
    if event.get("function_calls"):
        compact["function_calls"] = [call_.get("name") for call_ in event["function_calls"]]
    return {key: value for key, value in compact.items() if value not in (None, False)}


def _pending_decisions(events: List[dict]) -> List[dict]:
    answered = {response.get("id") for event in events for response in event.get("function_responses") or []}
    pending = []
    for event in events:
        if event.get("hitl_event_id") and not event.get("decision"):
            pending.append({"decision_target": "agent", "hitl_event_id": event["hitl_event_id"],
                            "author": event.get("author"), "content": _compact_event(event).get("content")})
        for function_call in event.get("function_calls") or []:
            if function_call.get("name") == HITL_TOOL_NAME and function_call.get("id") not in answered:
                pending.append({"decision_target": "tool_call", "hitl_event_id": function_call.get("id"),
                                "author": event.get("author"), "question_args": function_call.get("args")})
    return pending


@handle_exceptions
@requires_scope('read:agents')
async def get_workflow_session(session_id: SessionId) -> Any:
    """Read a workflow run session: state (e.g. running, finished, failed, awaiting_decision), error,
    pending_decisions (each with decision_target + hitl_event_id for answer_workflow_decision),
    breakpoint_pauses (agents paused at a debug breakpoint), event_count and the last 5 events compacted.

    Trimmed: full event log and run_stats are dropped, long contents truncated. Poll this after a run that
    returned early."""
    session = await call('GET', f"{BASE}/sessions/{session_id}", service=AGENTS)
    if not isinstance(session, dict) or "events" not in session:
        return session
    events = session.get("events") or []
    return {"state": session.get("state"), "error": session.get("error"),
            "pending_decisions": _pending_decisions(events) if session.get("state") == "awaiting_decision" else [],
            "breakpoint_pauses": session.get("breakpoint_pauses"),
            "interrupt_request": session.get("interrupt_request"),
            "last_invocation_id": session.get("last_invocation_id"),
            "workflow_commit_hash": session.get("workflow_commit_hash"), "run_by": session.get("run_by"),
            "last_update_time": session.get("last_update_time"), "event_count": len(events),
            "last_events": [_compact_event(event) for event in events[-LAST_EVENTS:]]}


@handle_exceptions
@requires_scope('execute:agents')
async def answer_workflow_decision(
        session_id: SessionId,
        decision_target: Annotated[Optional[Literal['agent', 'tool_call']], Field(
            description="'agent' approves/rejects a HITL agent; 'tool_call' answers a request_human_input call."
                        " Taken from pending_decisions.")] = None,
        hitl_event_id: Annotated[Optional[str], Field(
            description="hitl_event_id from get_workflow_session pending_decisions.")] = None,
        hitl_agent_decision: Annotated[Optional[Literal['approve', 'reject']], Field(
            description="Required when decision_target is 'agent'.")] = None,
        human_response: Annotated[Optional[str], Field(
            description="Free-text answer (max 4000 chars). Required when decision_target is 'tool_call'.")] = None,
        stop_session: Annotated[bool, Field(
            description="True stops the waiting session instead of answering; other fields are ignored.")] = False,
) -> Any:
    """Answer a workflow session paused in state awaiting_decision (human in the loop).

    First call get_workflow_session: its pending_decisions give decision_target and hitl_event_id. Then resume
    with run_agentic_workflow(same workflow_id and session_id, no workflow_input). Reject ends the session.
    Do NOT use for debug breakpoints, use continue_workflow_session."""
    return await call('POST', f"{BASE}/sessions/{session_id}/decision", service=AGENTS, json={
        "decision_target": decision_target, "hitl_event_id": hitl_event_id,
        "hitl_agent_decision": hitl_agent_decision, "human_response": human_response, "stop_session": stop_session})


@handle_exceptions
@requires_scope('execute:agents')
async def continue_workflow_session(
        session_id: SessionId,
        agent: Annotated[str, Field(
            description="Name of the paused agent to resume (a key of breakpoint_pauses in get_workflow_session).")],
        edited_model_input: Annotated[Optional[dict], Field(
            description="Replacement model request {contents: [{role, text}], system_instruction}, text only."
                        " Omit to continue with the original input.")] = None,
) -> Any:
    """Resume one agent paused at a DEBUG model-input breakpoint, optionally with an edited model request.

    Breakpoints exist only in debug runs; paused agents are listed in get_workflow_session breakpoint_pauses.
    This is NOT for answering human-in-the-loop requests (state awaiting_decision): use
    answer_workflow_decision for those."""
    return await call('POST', f"{BASE}/sessions/{session_id}/continue", service=AGENTS, json={
        "agent": agent, "edited_model_input": edited_model_input})


@handle_exceptions
@requires_scope('execute:agents')
async def stop_workflow_sessions(
        workflow_id: WorkflowId,
        session_ids: Annotated[List[str], Field(description="Ids of the sessions of that workflow to stop.")],
) -> Any:
    """Stop running or waiting sessions of one workflow. Returns {stopped_session_ids, skipped_session_ids};
    skipped are sessions already finished, deleted or belonging to another workflow.

    Stopped runs cannot be resumed from where they were."""
    return await call('POST', f"{BASE}/sessions/bulk/stop", service=AGENTS, json={
        "workflow_id": workflow_id, "session_ids": session_ids})
