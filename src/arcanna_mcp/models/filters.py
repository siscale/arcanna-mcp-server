from typing import List, Union, Optional
from pydantic import BaseModel, Field, model_validator


class FilterFieldsRequest(BaseModel):
    job_ids: Optional[Union[List[int], int]] = None
    job_titles: Optional[Union[List[str], str]] = None


class FilterFieldsObject(BaseModel):
    field_name: str
    available_operators: List[str]
    available_in_jobs: List[int] = Field(default_factory=list)
