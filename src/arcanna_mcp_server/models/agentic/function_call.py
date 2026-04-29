from pydantic import BaseModel, Field


class FunctionCall(BaseModel):
    id: str = Field(description="id of the function call")
    name: str = Field(description="name of the tool/function to be called")
    args: str = Field(description="json that represents the arguments of the function/tool call")
