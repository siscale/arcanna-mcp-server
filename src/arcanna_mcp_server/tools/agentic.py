from typing import Annotated, Callable, List, Optional, Union

from pydantic import Field

from arcanna_mcp_server.constants import LIST_WORKFLOWS_URL, RUN_WORKFLOW_BY_ID_URL, UPSERT_WORKFLOWS_URL, \
    TEST_RUN_WORKFLOW_BY_ID_URL, TOOL_DISCOVERY_URL, LLM_PROVIDERS_DISCOVERY_URL, GET_WORKFLOW_BY_ID_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.models.agentic.workflow_settings import WorkflowSettings
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.post_data import post_data
from arcanna_mcp_server.utils.get_data import get_data
from arcanna_mcp_server.utils.tool_scopes import requires_scope


def _headers():
    return {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json",
    }


def export_tools() -> List[Callable]:
    return [
        list_agentic_workflows,
        get_agentic_workflow_by_id,
        create_agentic_workflow,
        update_agentic_workflow,
        run_agentic_workflow,
        test_agentic_workflow,
        agents_tool_discovery,
        get_llm_integrations
    ]


@handle_exceptions
@requires_scope('read:agents')
async def list_agentic_workflows():
    """
    List all available agentic workflows. Returns a summary of each workflow including its ID, name, and description.
    """
    response = await get_data(LIST_WORKFLOWS_URL, _headers())
    entries = response.get("entries")
    if entries is None:
        return response

    return [{
        "id": entry.get("id"),
        "name": entry.get("name"),
        "description": entry.get("description"),
        "is_shared": entry.get("is_shared", False)
    } for entry in entries]


@handle_exceptions
@requires_scope('read:agents')
async def get_agentic_workflow_by_id(
        workflow_id: Annotated[Union[str, int], Field(description="Unique identifier of the workflow to fetch.")]
):
    """
    Fetch full details of an agentic workflow by its ID.
    """
    return await get_data(GET_WORKFLOW_BY_ID_URL.format(workflow_id), _headers())


@handle_exceptions
@requires_scope('execute:agents')
async def run_agentic_workflow(
        workflow_id: Annotated[Union[str, int], Field(description="Unique identifier of the workflow to run.")],
        workflow_input: Annotated[str, Field(description="Input for the agentic workflow.")],
        session_id: Annotated[Optional[str], Field(description=(
                "Workflow session ID. Provide this to continue an existing conversation; "
                "omit to start a new session."
        ))] = None,
):
    """
    Run an agentic workflow and wait for completion.
    Returns the workflow's output including agent events and responses.
    """
    payload = {
        "input": workflow_input,
        "wait_for_completion": True,
        "session_id": session_id,
    }

    return await post_data(RUN_WORKFLOW_BY_ID_URL.format(str(workflow_id)), _headers(), payload)


@handle_exceptions
@requires_scope('execute:agents')
async def test_agentic_workflow(
        workflow_input: Annotated[str, Field(description="Input for the agentic workflow.")],
        source_code: Annotated[str, Field(
            description="Python source code containing agent definitions.")],
        session_id: Annotated[Optional[str], Field(description=(
                "Workflow session ID. Provide this to continue an existing conversation; "
                "omit to start a new session."
        ))] = None,
):
    """
    Test an agentic workflow.
    Returns the workflow's output including agent events and responses.
    """
    payload = {
        "user_input": workflow_input,
        "wait_for_completion": True,
        "source_code": source_code,
        "session_id": session_id,
    }

    return await post_data(TEST_RUN_WORKFLOW_BY_ID_URL, _headers(), payload)


@handle_exceptions
@requires_scope('write:agents')
async def create_agentic_workflow(
        source_code: Annotated[str, Field(description="Python source code containing agent definitions. The root_agent's name and description become the workflow's name and description.")],
        settings: Annotated[Optional[WorkflowSettings], Field(description="Resource settings for the workflow.")] = None,
) -> dict:
    """
    Create an agentic workflow with the provided configuration.
    """
    payload = {
        "source_code": source_code,
        "settings": settings.model_dump() if settings else None,
    }

    return await post_data(UPSERT_WORKFLOWS_URL, _headers(), payload)


@handle_exceptions
@requires_scope('write:agents')
async def update_agentic_workflow(
        workflow_id: Annotated[str, Field(description="Unique identifier of the workflow to update.")],
        source_code: Annotated[str, Field(description="Python source code containing agent definitions. The root_agent's name and description become the workflow's name and description.")],
        settings: Annotated[Optional[WorkflowSettings], Field(description="Resource settings for the workflow.")] = None,
) -> dict:
    """
    Update an existing agentic workflow with the provided configuration.
    """
    payload = {
        "id": workflow_id,
        "source_code": source_code,
        "settings": settings.model_dump() if settings else None,
    }

    return await post_data(UPSERT_WORKFLOWS_URL, _headers(), payload)


@handle_exceptions
@requires_scope('read:agents')
async def agents_tool_discovery() -> dict:
    """
    Discover tools for agents in agentic workflows. These tools can be found in Arcanna's environment where agents run
    and have access to them.
    """
    return await get_data(TOOL_DISCOVERY_URL, _headers())


@handle_exceptions
@requires_scope('read:agents')
async def get_llm_integrations() -> dict:
    """
    Discover llm integrations to choose one or multiple providers for the model used in agentic workflows.
    """
    return await get_data(LLM_PROVIDERS_DISCOVERY_URL, _headers())
