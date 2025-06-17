from typing import Callable, List, Optional, Union

import requests
from arcanna_mcp_server.constants import LIST_WORKFLOWS_URL, RUN_WORKFLOW_BY_ID_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY
from arcanna_mcp_server.utils.exceptions_handler import handle_exceptions
from arcanna_mcp_server.utils.post_data import post_data


def export_tools() -> List[Callable]:
    return [
        list_agentic_workflows,
        run_agentic_workflow,
    ]


@handle_exceptions
async def list_agentic_workflows() -> list:
    """
        An agentic workflow is a suite of AI Agents that solve user defined tasks. This function lists all agentic workflows available.

    Returns:
    --------
    list
        A list containing all agentic workflows. Each workflow is a dictionary with the following keys:
        - id(str): id of the workflow
        - name(str): name of the workflow
        - description(str): description of the workflow
     """

    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(LIST_WORKFLOWS_URL, headers=headers)
    entries = response.json().get("entries")
    return [{"id": entry.get("id"), "name": entry.get("name"), "description": entry.get("description")}
            for entry in entries]


@handle_exceptions
async def run_agentic_workflow(workflow_id: Union[str, int], workflow_input: str, session_id: Optional[str] = None) -> dict:
    """
        Run an agentic workflow with a given workflow input.

    Parameters:
    --------
    workflow_id: str or int
        Unique identifier of the workflow to run
    workflow_input: str
        Input for the agentic workflow

    Returns:
    --------
    dict
        A dictionary with the following keys:
        - workflow_result(dict): Result of the workflow.
            workflow_result is a list of events. Each event is represented by a dictionary with the following keys:
                - author(str): name of the agent that created the event. Can be either the user (like a user message) or the name of an agent in the workflow
                - final(bool): flag that states the agent in the workflow finished its task or not.
                - function_calls(list): List of dictionaries with the following keys:
                    - id(str): id of the function call
                    - name(str): name of the tool/function to be called
                    - args(str): json that represents the arguments of the function/tool call
                - function_responses(list): List of dictionaries with the following keys:
                    - id(str): id of the function that was called
                    - name(str): name of the tool/function that was called
                    - response(str): the result of the function call
                - content(str): Message of the author
        - session_id(str): Workflow session id. To continue the conversation, run_agentic_workflow tool must be provided the session_id of the conversation.
     """
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "input": workflow_input,
        "wait_for_completion": True,
        "session_id": session_id
    }

    response = await post_data(RUN_WORKFLOW_BY_ID_URL.format(str(workflow_id)), headers, payload)
    return response
