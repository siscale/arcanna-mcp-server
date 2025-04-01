from pydantic import BaseModel, Field, computed_field, model_validator
from typing import Annotated, Any, Dict, List, Literal, Optional, Union


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
    hex_color: Optional[str] = Field(default=None, description="Label hex color, used for displaying in Arcanna UI")


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
        integration_type: Literal[
            'input', 'enrichment', 'processor',
            'case_creation', 'post_decision', 'output'
        ]
        enabled: bool
        auto_id: Optional[str] = Field(default=None)
        storage_tag: Optional[str] = Field(default=None)
        storage_tag_display_name: Optional[str] = Field(default=None)
        parameters: Dict[str, Any]

        @model_validator(mode='after')
        def validate_pipeline_integration(self):
            if self.storage_tag and self.integration_type != 'input':
                raise ValueError("storage_tag can be specified only for integration_type 'input'")
            forbidden_characters = [' ', '.', '*']
            if self.storage_tag:
                for forbidden_character in forbidden_characters:
                    if forbidden_character in self.storage_tag:
                        raise ValueError(f"storage_tag cannot contain forbiden characters: {forbidden_characters}")
            return self

    class AdvancedSettings(BaseModel):
        custom_labels: Optional[List[Label]] = Field(default=None)
        auto_retrain: Optional[AutoRetrainOptions] = Field(default=None, description="Auto retrain settings")
        monitoring_settings: Optional[MonitoringSettings] = Field(default=None, description="Monitoring settings")

    title: str
    description: Optional[str] = None
    category: str
    decision_points: List[str]
    feedback_columns: Optional[List[str]] = None
    advanced_settings: Optional[AdvancedSettings] = None
    pipeline_integrations: List[PipelineIntegration]
    remove_missing_pipeline_integrations: Optional[bool] = Field(
        default=False, description=(
            "When true, it indicates that pipeline_integrations which are not found in the request will be removed. "
            "Otherwise missing pipeline_integrations will be taken from previous version of the job.")
        )


ResourcePropertiesType = Union[ApiKeyProperties, IntegrationProperties, JobProperties]


class ResourceCommon(BaseModel):
    type: Any
    depends_on: Optional[List[str]] = Field(default=[])


class ApiKeyResource(ResourceCommon):
    type: Literal['api_key']
    properties: ApiKeyProperties


class IntegrationResource(ResourceCommon):
    type: Literal['integration']
    properties: IntegrationProperties


class JobResource(ResourceCommon):
    type: Literal['job']
    properties: JobProperties


ResourceUnionType = Union[ApiKeyResource, IntegrationResource, JobResource]


BaseResource = Annotated[ResourceUnionType, Field(discriminator='type')]
