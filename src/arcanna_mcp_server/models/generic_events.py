from typing import Optional, List, Any, Union, Dict, Literal
from pydantic import BaseModel, Field


class Filter(BaseModel):
    field: str
    operator: Literal["is", "is not", "is one of", "is not one of", "starts with", "not starts with", "contains", "not contains", "exists", "not exists", "lt", "lte", "gte", "gte"]
    value: Optional[Any] = None


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


class TransferEventResponse(BaseModel):
    event_id: Optional[Union[str, int]] = Field(default=None)
    job_id: Optional[int] = Field(default=None)
    ingest_timestamp: str = Field(default=None)
    status: Optional[str] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
