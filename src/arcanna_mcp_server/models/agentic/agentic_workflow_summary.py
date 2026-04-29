from pydantic import BaseModel, Field


class AgenticWorkflowSummary(BaseModel):
    id: str = Field(description="id of the workflow")
    name: str = Field(description="name of the workflow")
    description: str = Field(description="description of the workflow")
