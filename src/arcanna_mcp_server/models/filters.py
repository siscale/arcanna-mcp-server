from typing import List, Union, Optional
from pydantic import BaseModel, Field, model_validator


class FilterFieldsObject(BaseModel):
    field_name: str
    available_operators: List[str]
    available_in_jobs: List[int] = Field(default_factory=list)
