"""Tests for core.execution.task_schemas — pydantic schemas."""
import pytest
from pydantic import ValidationError

from core.execution.task_schemas import (
    ContractCheckOutput,
    DocumentReviewOutput,
    GenericTaskOutput,
    RiskAnalysisOutput,
    TASK_OUTPUT_SCHEMAS,
    get_schema_for_task_type,
)


def test_document_review_valid():
    schema = DocumentReviewOutput(
        completeness=0.9,
        missing_fields=[],
        recommendation="APPROVE",
        reasoning="All fields present.",
        confidence=0.88,
    )
    assert schema.recommendation == "APPROVE"


def test_document_review_invalid_recommendation():
    with pytest.raises(ValidationError):
        DocumentReviewOutput(
            completeness=0.9,
            missing_fields=[],
            recommendation="MAYBE",
            reasoning="x",
            confidence=0.9,
        )


def test_document_review_confidence_out_of_range():
    with pytest.raises(ValidationError):
        DocumentReviewOutput(
            completeness=0.9,
            missing_fields=[],
            recommendation="APPROVE",
            reasoning="x",
            confidence=1.5,
        )


def test_document_review_completeness_out_of_range():
    with pytest.raises(ValidationError):
        DocumentReviewOutput(
            completeness=2.0,
            missing_fields=[],
            recommendation="APPROVE",
            reasoning="x",
            confidence=0.9,
        )


def test_document_review_reasoning_empty():
    with pytest.raises(ValidationError):
        DocumentReviewOutput(
            completeness=0.9,
            missing_fields=[],
            recommendation="APPROVE",
            reasoning="",
            confidence=0.9,
        )


def test_risk_analysis_valid():
    r = RiskAnalysisOutput(
        risk_level="LOW",
        risk_factors=["steady income"],
        recommendation="APPROVE",
        reasoning="Healthy ratios.",
        confidence=0.9,
    )
    assert r.risk_level == "LOW"


def test_risk_analysis_invalid_risk_level():
    with pytest.raises(ValidationError):
        RiskAnalysisOutput(
            risk_level="EXTREME",
            risk_factors=[],
            recommendation="APPROVE",
            reasoning="x",
            confidence=0.9,
        )


def test_contract_check_valid():
    c = ContractCheckOutput(
        compliance_status="COMPLIANT",
        issues=[],
        recommendation="APPROVE",
        reasoning="All clauses present.",
        confidence=0.9,
    )
    assert c.compliance_status == "COMPLIANT"


def test_contract_check_invalid_compliance():
    with pytest.raises(ValidationError):
        ContractCheckOutput(
            compliance_status="UNKNOWN",
            issues=[],
            recommendation="APPROVE",
            reasoning="x",
            confidence=0.9,
        )


def test_generic_task_output_valid():
    g = GenericTaskOutput(result="ok", reasoning="r", confidence=0.5)
    assert g.result == "ok"


def test_generic_task_output_empty_result():
    with pytest.raises(ValidationError):
        GenericTaskOutput(result="", reasoning="r", confidence=0.5)


def test_get_schema_for_task_type_known():
    assert get_schema_for_task_type("document_review") is DocumentReviewOutput
    assert get_schema_for_task_type("risk_analysis") is RiskAnalysisOutput
    assert get_schema_for_task_type("contract_check") is ContractCheckOutput


def test_get_schema_for_task_type_unknown():
    assert get_schema_for_task_type("something_else") is GenericTaskOutput


def test_task_output_schemas_registry():
    assert "document_review" in TASK_OUTPUT_SCHEMAS
    assert "risk_analysis" in TASK_OUTPUT_SCHEMAS
    assert "contract_check" in TASK_OUTPUT_SCHEMAS
