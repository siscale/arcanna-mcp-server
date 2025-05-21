from typing import Optional, List, Any, Union, Dict, Literal
from pydantic import BaseModel, Field


class Filter(BaseModel):
    field: str
    operator: Literal["is", "is not", "is one of", "is not one of", "starts with", "not starts with", "contains", "not contains", "exists", "not exists", "lt", "lte", "gte", "gte"]
    value: Optional[Any] = None


class QueryEventsRequest(BaseModel):
    job_ids: Optional[Union[List[int], int]] = None
    job_titles: Optional[Union[List[str], str]] = None
    event_ids: Optional[Union[List[str], str]] = None
    decision_points_only: Optional[bool] = False
    count_results_only: Optional[bool] = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    date_field: Optional[str] = Field(default="@timestamp")
    size: Optional[int] = Field(default=5)
    page: Optional[int] = Field(default=0)
    sort_by_column: Optional[str] = Field(default="timestamp_inference")
    sort_order: Optional[Literal['desc', 'asc']] = Field(default="desc")
    filters: Optional[List[Filter]] = Field(default_factory=list)


class EventsReprocessingModelRequest(BaseModel):
    job_id: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    size: Optional[int] = Field(default=5)
    page: Optional[int] = Field(default=0, ge=0, description="Page counting starts from 0")
    sort_by_column: Optional[str] = Field(default="@timestamp")
    sort_order: Optional[str] = Field(default="desc")
    filters: Optional[List[Filter]] = Field(default_factory=list)


class EventModel(BaseModel):
    event_id: str
    job_id: int
    job_title: str
    decision_points: Dict[str, Any]

    class Config:
        extra = "allow"


class EventsModelResponse(BaseModel):
    events: List[EventModel] = Field(default_factory=list)
    total_count: int
