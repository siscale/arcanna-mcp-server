from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WorkflowSettings(BaseModel):
    limits: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Resource limits configuration with nested limit settings."
    )
