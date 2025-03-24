
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from arcanna_mcp.models.resource_type import ResourceType


class ApiKeyProperties(BaseModel):
    name: str

    @computed_field
    @property
    def title(self) -> str:
        return self.name


class IntegrationProperties(BaseModel):
    title: str
    integration_type: str
    parameters: Dict[str, Any]


class Label(BaseModel):
    name: str
    hex_color: str


class AutoRetrainOptions(BaseModel):
    class AutoRetrainBlockers(BaseModel):
        consensus_flipping: bool = Field(default=False, description="Buckets/events with flipping consensus")
        low_confidence_score: bool = Field(default=False, description="Buckets/events with low confidence score")
        undecided_consensus: bool = Field(default=False, description="Bucket/events with undecided consensus")
        consensus_low_score: bool = Field(default=False, description="Buckets/events with low consensus score")
        outliers: bool = Field(default=False, description="Outliers")
        consensus_changes: bool = Field(default=False, description="Consensus changes since last training session")

    enabled: bool
    cron: str
    blockers: Optional[AutoRetrainBlockers] = Field(default=None)


class MonitoringSettings(BaseModel):
    class MonitorInfo(BaseModel):
        name: Literal[
            "results_with_error_logs_in_last_x_minutes",
            "error_job_state_in_last_x_minutes",
            "no_data_processed_in_last_x_minutes"
        ]
        active: bool
        interval_check: int

    throttling: int
    monitors: List[MonitorInfo]


class JobProperties(BaseModel):
    class PipelineIntegration(BaseModel):
        resource: str
        integration_type: str
        enabled: bool
        auto_id: Optional[str] = Field(default=None)
        parameters: Dict[str, Any]

    class Feature(BaseModel):
        name: str
        type: str

    class AdvancedSettings(BaseModel):
        custom_labels: Optional[List[Label]] = Field(default=None)
        auto_retrain: Optional[AutoRetrainOptions] = Field(default=None, description="Auto retrain settings")
        monitoring_settings: Optional[MonitoringSettings] = Field(default=None, description="Monitoring settings")

    title: str
    description: Optional[str] = None
    category: str
    features: List[str]
    feedback_columns: Optional[List[str]] = None
    advanced_settings: Optional[AdvancedSettings] = None
    pipeline_integrations: List[PipelineIntegration]


ResourcePropertiesType = Union[ApiKeyProperties, IntegrationProperties, JobProperties]


class ResourceCommon(BaseModel):
    type: Any
    depends_on: Optional[List[str]] = Field(default=[])


class ApiKeyResource(ResourceCommon):
    type: Literal[ResourceType.API_KEY] = ResourceType.API_KEY.value
    properties: ApiKeyProperties


class IntegrationResource(ResourceCommon):
    type: Literal[ResourceType.INTEGRATION] = ResourceType.INTEGRATION.value
    properties: IntegrationProperties


class JobResource(ResourceCommon):
    type: Literal[ResourceType.JOB] = ResourceType.JOB.value
    properties: JobProperties


ResourceUnionType = Union[ApiKeyResource, IntegrationResource, JobResource]


BaseResource = Annotated[ResourceUnionType, Field(discriminator='type')]
