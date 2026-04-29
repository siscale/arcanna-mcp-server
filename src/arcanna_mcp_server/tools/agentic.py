import requests
from typing import Annotated, Callable, List, Optional, Union

from pydantic import Field

from arcanna_mcp_server.constants import LIST_WORKFLOWS_URL, RUN_WORKFLOW_BY_ID_URL, UPSERT_WORKFLOWS_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.models.agentic.agentic_workflow_summary import AgenticWorkflowSummary
from arcanna_mcp_server.models.agentic.env_variable import EnvVariable
from arcanna_mcp_server.models.agentic.run_workflow_response import RunWorkflowResponse
from arcanna_mcp_server.models.agentic.workflow_settings import WorkflowSettings
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.post_data import post_data
from arcanna_mcp_server.utils.tool_scopes import requires_scope


def export_tools() -> List[Callable]:
    return [
        list_agentic_workflows,
        run_agentic_workflow,
        create_agentic_workflow,
    ]


@handle_exceptions
@requires_scope('read:agents')
async def list_agentic_workflows() -> List[AgenticWorkflowSummary]:
    """
        An agentic workflow is a suite of AI Agents that solve user defined tasks. This function lists all agentic workflows available.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(LIST_WORKFLOWS_URL, headers=headers)
    entries = response.json().get("entries")
    return [AgenticWorkflowSummary(id=entry.get("id"), name=entry.get("name"), description=entry.get("description"))
            for entry in entries]


@handle_exceptions
@requires_scope('execute:agents')
async def run_agentic_workflow(
        workflow_id: Annotated[Union[str, int], Field(description="Unique identifier of the workflow to run")],
        workflow_input: Annotated[str, Field(description="Input for the agentic workflow")],
        session_id: Annotated[Optional[str], Field(description=(
            "Workflow session id. Provide this to continue an existing conversation; "
            "omit to start a new session."
        ))] = None,
) -> RunWorkflowResponse:
    """
        Run an agentic workflow with a given workflow input.
     """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "input": workflow_input,
        "wait_for_completion": True,
        "session_id": session_id,
    }

    response = await post_data(RUN_WORKFLOW_BY_ID_URL.format(str(workflow_id)), headers, payload)
    return RunWorkflowResponse(**response)


@handle_exceptions
@requires_scope('write:agents')
async def create_agentic_workflow(
        name: Annotated[str, Field(description="Name of the workflow")],
        source_code: Annotated[str, Field(description="Python source code for the workflow containing agent definitions")],
        description: Annotated[Optional[str], Field(description="Description of the workflow")] = "",
        env_variables: Annotated[Optional[List[EnvVariable]], Field(description="List of environment variables for the workflow.")] = None,
        settings: Annotated[Optional[WorkflowSettings], Field(description="Resource settings for the workflow.")] = None,
) -> Annotated[
    dict,
    Field(description=(
        "A dictionary with the response from the workflow creation endpoint. "
        "Success response typically contains confirmation of workflow creation."
    ))
]:
    """
        Create or update an agentic workflow with the provided configuration.
        Before using this tool, make sure to generate the code instructions for your workflow using the generate_agentic_code_instructions tool.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "name": name,
        "description": description,
        "source_code": source_code,
        "env_variables": [env_var.model_dump() for env_var in env_variables] if env_variables else None,
        "settings": settings.model_dump() if settings else None,
    }

    response = await post_data(UPSERT_WORKFLOWS_URL, headers, payload)
    return response

@handle_exceptions
@requires_scope('write:agents')
async def update_agentic_workflow(
        workflow_id: Annotated[str, Field(description="Unique identifier for the workflow")],
        source_code: Annotated[str, Field(description="Python source code for the workflow containing agent definitions")],
        env_variables: Annotated[Optional[List[EnvVariable]], Field(description="List of environment variables for the workflow.")] = None,
        settings: Annotated[Optional[WorkflowSettings], Field(description="Resource settings for the workflow.")] = None,
) -> Annotated[
    dict,
    Field(description=(
        "A dictionary with the response from the workflow creation endpoint. "
        "Success response typically contains confirmation of workflow creation."
    ))
]:
    """
        Create or update an agentic workflow with the provided configuration.
        To update the name of the workflow, name of root_agent must be modified.
        To update the description of the workflow, description of root_agent must be modified.
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "id": workflow_id,
        "source_code": source_code,
        "env_variables": [env_var.model_dump() for env_var in env_variables] if env_variables else None,
        "settings": settings.model_dump() if settings else None,
    }

    response = await post_data(UPSERT_WORKFLOWS_URL, headers, payload)
    return response
