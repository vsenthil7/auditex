"""
Auditex -- Per-task-type output schemas.
Each task type defines the exact JSON structure Claude must return.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DocumentReviewOutput(BaseModel):
    completeness: float = Field(ge=0.0, le=1.0)
    missing_fields: list[str]
    recommendation: Literal["APPROVE", "REQUEST_ADDITIONAL_INFO", "REJECT"]
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class RiskAnalysisOutput(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    risk_factors: list[str]
    recommendation: Literal["APPROVE", "REQUEST_ADDITIONAL_INFO", "REJECT"]
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class ContractCheckOutput(BaseModel):
    compliance_status: Literal["COMPLIANT", "PARTIAL", "NON_COMPLIANT"]
    issues: list[str]
    recommendation: Literal["APPROVE", "REQUEST_AMENDMENTS", "REJECT"]
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class GenericTaskOutput(BaseModel):
    result: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


TASK_OUTPUT_SCHEMAS: dict[str, type[BaseModel]] = {
    "document_review": DocumentReviewOutput,
    "risk_analysis":   RiskAnalysisOutput,
    "contract_check":  ContractCheckOutput,
}


def get_schema_for_task_type(task_type: str) -> type[BaseModel]:
    return TASK_OUTPUT_SCHEMAS.get(task_type, GenericTaskOutput)
