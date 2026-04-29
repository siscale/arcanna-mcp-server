from pydantic import BaseModel, Field


class EnvVariable(BaseModel):
    name: str = Field(description="variable name")
    value: str = Field(description="variable value")
    is_secret: bool = Field(default=False, description="whether the variable is secret")
    should_encrypt: bool = Field(default=False, description="whether the variable should be encrypted")
