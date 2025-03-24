from typing import List, Union, Optional
from pydantic import BaseModel, Field, model_validator


class FilterFieldsRequest(BaseModel):
    job_ids: Optional[Union[List[int], int]] = None
    job_titles: Optional[Union[List[str], str]] = None

    @model_validator(mode="before")
    def validate_request(cls, values):
        cls.normalize_list_fields(values)
        return values

    @classmethod
    def normalize_list_fields(cls, values):
        for field in ["job_ids", "job_titles"]:
            if field in values and values[field] and not isinstance(values[field], list):
                values[field] = [values[field]]

class FilterFieldsObject(BaseModel):
    field_name: str
    available_operators: List[str]
    available_in_jobs: List[int] = Field(default_factory=list)
