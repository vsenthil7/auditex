"""Smoke tests that consume shared conftest fixtures so they're covered."""
from __future__ import annotations


def test_sample_executor_output_fixture(sample_executor_output):
    assert sample_executor_output["recommendation"] == "APPROVE"
    assert 0.0 <= sample_executor_output["confidence"] <= 1.0
    assert isinstance(sample_executor_output["missing_fields"], list)


def test_sample_risk_output_fixture(sample_risk_output):
    assert sample_risk_output["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert sample_risk_output["recommendation"] == "APPROVE"
    assert isinstance(sample_risk_output["risk_factors"], list)


def test_sample_contract_output_fixture(sample_contract_output):
    assert sample_contract_output["compliance_status"] == "COMPLIANT"
    assert sample_contract_output["recommendation"] == "APPROVE"
    assert isinstance(sample_contract_output["issues"], list)
