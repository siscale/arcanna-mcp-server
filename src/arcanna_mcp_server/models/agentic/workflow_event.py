from typing import List

from pydantic import BaseModel, Field

from arcanna_mcp_server.models.agentic.function_call import FunctionCall
from arcanna_mcp_server.models.agentic.function_response import FunctionResponse


class WorkflowEvent(BaseModel):
    author: str = Field(description=(
        "name of the agent that created the event. Can be either the user "
        "(like a user message) or the name of an agent in the workflow"
    ))
    final: bool = Field(description="flag that states the agent in the workflow finished its task or not")
    function_calls: List[FunctionCall] = Field(description="List of function calls performed during this event")
    function_responses: List[FunctionResponse] = Field(description="List of function responses generated during this event")
    content: str = Field(description="Message of the author")
