from pydantic import BaseModel, Field


class EnvVariable(BaseModel):
    name: str = Field(description="variable name")
    is_secret: bool = Field(default=False, description="whether the variable is secret")


class EnvVariableRequestPayload(EnvVariable):
    value: str = Field(description="variable value")
    should_encrypt: bool = Field(default=False, description="whether the variable should be encrypted")
