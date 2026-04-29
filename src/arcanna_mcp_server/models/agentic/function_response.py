from pydantic import BaseModel, Field


class FunctionResponse(BaseModel):
    id: str = Field(description="id of the function that was called")
    name: str = Field(description="name of the tool/function that was called")
    response: str = Field(description="the result of the function call")
