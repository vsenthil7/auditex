"""Tests for core.review.consensus_eval."""
import pytest

from core.review.consensus_eval import evaluate_consensus, is_consensus_passed


def test_evaluate_3_of_3_approve():
    assert evaluate_consensus(["APPROVE", "APPROVE", "APPROVE"]) == "3_OF_3_APPROVE"


def test_evaluate_2_of_3_approve():
    assert evaluate_consensus(["APPROVE", "APPROVE", "REJECT"]) == "2_OF_3_APPROVE"


def test_evaluate_1_of_3_approve():
    assert evaluate_consensus(["APPROVE", "REJECT", "REJECT"]) == "1_OF_3_APPROVE"


def test_evaluate_0_of_3_approve():
    assert evaluate_consensus(["REJECT", "REJECT", "REJECT"]) == "0_OF_3_APPROVE"


def test_evaluate_empty_raises():
    with pytest.raises(ValueError):
        evaluate_consensus([])


def test_evaluate_invalid_verdict_raises():
    with pytest.raises(ValueError):
        evaluate_consensus(["APPROVE", "MAYBE", "APPROVE"])


def test_evaluate_normalises_case_and_whitespace():
    assert evaluate_consensus([" approve ", "Approve", "APPROVE"]) == "3_OF_3_APPROVE"


def test_evaluate_non_standard_count():
    label = evaluate_consensus(["APPROVE", "APPROVE", "APPROVE", "REJECT"])
    assert label == "3_OF_4_APPROVE"


def test_is_consensus_passed_true():
    assert is_consensus_passed("3_OF_3_APPROVE") is True
    assert is_consensus_passed("2_OF_3_APPROVE") is True


def test_is_consensus_passed_false():
    assert is_consensus_passed("1_OF_3_APPROVE") is False
    assert is_consensus_passed("0_OF_3_APPROVE") is False
    assert is_consensus_passed("3_OF_4_APPROVE") is False
