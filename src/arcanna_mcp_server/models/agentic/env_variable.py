from pydantic import BaseModel, Field


class EnvVariable(BaseModel):
    name: str = Field(description="name of the variable")
    value: str = Field(description="value of the variable")
    is_secret: bool = Field(default=False, description="Weather or not the variable is a secret")
    should_encrypt: bool = Field(default=False, description="Should the var be encrypted")
