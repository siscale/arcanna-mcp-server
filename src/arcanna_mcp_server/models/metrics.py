from typing import Dict, Optional, List
from pydantic import BaseModel, Field


class MetricsPerDecision(BaseModel):
    precision: float = Field(
        description="The ratio of true positive results to the total predicted positives (true positives + false positives)")
    recall: float = Field(
        description="The ratio of true positive results to the total actual positives (true positives + false negatives)")
    f1_score: float = Field(description="The harmonic mean of precision and recall")
    true_positives: float = Field(description="The number of correctly predicted positive instances")
    true_negatives: float = Field(description="The number of correctly predicted negative instances")
    false_positives: float = Field(description="The number of instances incorrectly predicted as positive")
    false_negatives: float = Field(description="The number of instances incorrectly predicted as negative")


class GetModelMetricsResponse(BaseModel):
    model_id: Optional[str] = Field(None, description="The unique identifier of the model")
    is_recomputing_metrics: Optional[bool] = Field(None, description="Indicates if the metrics are being recomputed")
    last_recomputed_timestamp: Optional[str] = Field(description="The timestamp of the last metrics recomputation")
    overall_accuracy: Optional[float] = Field(description="The mean accuracy across decisions")
    overall_f1_score: Optional[float] = Field(description="The mean F1 score across decisions")
    overall_recall: Optional[float] = Field(description="The mean recall across decisions")
    overall_precision: Optional[float] = Field(description="The mean precision across decisions")
    confusion_matrix: Optional[List[List[int]]] = Field(description="The confusion matrix of the model decisions")
    metrics_per_decision: Dict[str, MetricsPerDecision] = Field(description="Metrics per decision type")


class ChangedConsensusInfo(BaseModel):
    total_events: Optional[int] = Field(None, description="Number of KB alerts with changed consensus"
                                                          " after model training")
    top_events_ids: Optional[List[str]] = Field(None, description="Top 100 IDs of alerts with changed consensus"
                                                                  " after model training")
    top_buckets_ids: Optional[List[str]] = Field(None, description="Top 100 IDs of buckets with changed consensus"
                                                                   " after model training")


class GetJobMetricsResponse(BaseModel):
    start_time: Optional[str] = Field(description="The start time for computing the metrics")
    end_time: Optional[str] = Field(description="The end time for computing the metrics")
    overall_accuracy: Optional[float] = Field(description="The mean accuracy across decisions")
    overall_f1_score: Optional[float] = Field(description="The mean F1 score across decisions")
    overall_recall: Optional[float] = Field(description="The mean recall across decisions")
    overall_precision: Optional[float] = Field(description="The mean precision across decisions")
    time_saved_minutes: Optional[float] = Field(
        description="The time saved by the job in minutes. "
                    "Calculated as: Average Time spent on investigating an alert * Alerts with correct Arcanna decisions.")
    confusion_matrix: Optional[List[List[int]]] = Field(description="The confusion matrix of the model decisions")
    metrics_per_decision: Dict[str, MetricsPerDecision] = Field(description="Metrics per decision type for the job")
    active_model_id: Optional[str] = Field(description="The unique identifier of the active model")
    all_model_ids: Optional[List[str]] = Field(description="List of all model identifiers")
    total_events: Optional[int] = Field(description="Total processed events")
    total_events_in_knowledge_base: Optional[int] = Field(description="Total processed events in the knowledge base")
    total_events_with_consensus: Optional[int] = Field(description="Total processed events with feedback (consensus)")
    changed_consensus_after_training: ChangedConsensusInfo = Field(description="Information regarding changed consensus"
                                                                               " after model training")


class GetJobAndLatestModelMetricsResponse(GetJobMetricsResponse):
    active_model_metrics: GetModelMetricsResponse
