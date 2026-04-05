"""
Auditex -- Per-task-type output schemas.
Each task type defines the exact JSON structure Claude must return.
Pydantic validates Claude's output against these schemas at the boundary.

Adding a new task type:
  1. Define a new Pydantic model below.
  2. Register it in TASK_OUTPUT_SCHEMAS.
  3. Add a system prompt for it in claude_executor.py.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# document_review output schema
# ---------------------------------------------------------------------------
class DocumentReviewOutput(BaseModel):
    """
    Output schema for task_type="document_review".
    Claude must return a JSON object matching this structure exactly.
    """
    completeness: float = Field(
        ge=0.0, le=1.0,
        description="How complete the document is, 0.0 (empty) to 1.0 (fully complete).",
    )
    missing_fields: list[str] = Field(
        description="List of field names or sections that are absent or incomplete.",
    )
    recommendation: Literal["APPROVE", "REQUEST_ADDITIONAL_INFO", "REJECT"] = Field(
        description="Reviewer's recommended action.",
    )
    reasoning: str = Field(
        min_length=1,
        description="2-3 sentence explanation of the recommendation.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Claude's confidence in this assessment.",
    )


# ---------------------------------------------------------------------------
# Generic fallback output schema
# ---------------------------------------------------------------------------
class GenericTaskOutput(BaseModel):
    """
    Fallback output schema for any task_type not explicitly registered.
    """
    result: str = Field(
        min_length=1,
        description="Claude's output for the task.",
    )
    reasoning: str = Field(
        min_length=1,
        description="2-3 sentence explanation of the result.",
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Claude's confidence in this result.",
    )


# ---------------------------------------------------------------------------
# Registry: task_type -> Pydantic model class
# ---------------------------------------------------------------------------
TASK_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "document_review": DocumentReviewOutput,
    # Future task types registered here
}


def get_schema_for_task_type(task_type: str) -> type[BaseModel]:
    """Return the output schema class for a given task_type, or GenericTaskOutput."""
    return TASK_OUTPUT_SCHEMAS.get(task_type, GenericTaskOutput)
