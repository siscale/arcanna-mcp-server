from typing import List

from pydantic import BaseModel, Field

from arcanna_mcp_server.models.agentic.workflow_event import WorkflowEvent


class RunWorkflowResponse(BaseModel):
    workflow_result: List[WorkflowEvent] = Field(description="Result of the workflow as a list of events")
    session_id: str = Field(description=(
        "Workflow session id. To continue the conversation, run_agentic_workflow tool "
        "must be provided the session_id of the conversation."
    ))
