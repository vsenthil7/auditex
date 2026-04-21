"""Tests for core.review.hash_commitment — commitment scheme."""
import pytest

from core.review.hash_commitment import (
    SecurityViolationError,
    compute_commitment,
    generate_nonce,
    verify_commitment,
)


def test_generate_nonce_returns_64_char_hex():
    n = generate_nonce()
    assert isinstance(n, str)
    assert len(n) == 64
    int(n, 16)  # must parse as hex


def test_generate_nonce_unique():
    assert generate_nonce() != generate_nonce()


def test_compute_commitment_is_deterministic():
    n = "a" * 64
    assert compute_commitment("APPROVE", n) == compute_commitment("APPROVE", n)


def test_compute_commitment_changes_with_verdict():
    n = "a" * 64
    assert compute_commitment("APPROVE", n) != compute_commitment("REJECT", n)


def test_compute_commitment_changes_with_nonce():
    assert compute_commitment("APPROVE", "a" * 64) != compute_commitment("APPROVE", "b" * 64)


def test_verify_commitment_valid():
    n = generate_nonce()
    h = compute_commitment("APPROVE", n)
    assert verify_commitment("APPROVE", n, h) is True


def test_verify_commitment_invalid_raises():
    n = generate_nonce()
    h = compute_commitment("APPROVE", n)
    with pytest.raises(SecurityViolationError):
        verify_commitment("REJECT", n, h)


def test_verify_commitment_wrong_nonce_raises():
    n1 = generate_nonce()
    n2 = generate_nonce()
    h = compute_commitment("APPROVE", n1)
    with pytest.raises(SecurityViolationError):
        verify_commitment("APPROVE", n2, h)


def test_verify_commitment_wrong_hash_raises():
    n = generate_nonce()
    with pytest.raises(SecurityViolationError):
        verify_commitment("APPROVE", n, "0" * 64)
