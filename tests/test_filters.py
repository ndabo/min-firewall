"""
Unit tests for app/filters3.py — no HTTP server required.
LlamaGuard HTTP calls are mocked.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.filters3 import detect_pii, call_llamaguard, is_blocked


# ---------------------------------------------------------------------------
# Layer 1: PII detection (synchronous — no async needed)
# ---------------------------------------------------------------------------

def test_pii_ssn_blocked():
    result = detect_pii("My SSN is 123-45-6789")
    assert result is not None
    assert "SSN" in result


def test_pii_email_blocked():
    result = detect_pii("Reach me at user@example.com for more info")
    assert result is not None
    assert "email" in result


def test_pii_person_blocked():
    result = detect_pii("Contact Alice Johnson for details")
    assert result is not None
    assert "PERSON" in result


def test_pii_cardinal_not_blocked():
    """Cardinal numbers must NOT trigger PII (was a false positive in filters2)."""
    result = detect_pii("I need 5 items from the store")
    assert result is None


def test_pii_date_not_blocked():
    """Dates must NOT trigger PII (was a false positive in filters2)."""
    result = detect_pii("Meet on Monday at the office")
    assert result is None


def test_pii_credit_card_blocked():
    result = detect_pii("My credit card number is 1234567890123456")
    assert result is not None
    assert "credit card" in result


# ---------------------------------------------------------------------------
# Layer 2: LlamaGuard (async — mock HTTP)
# ---------------------------------------------------------------------------

def _make_mock_client(status_code: int, json_body=None, side_effect=None):
    """Helper: build a mock httpx.AsyncClient context manager."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    if json_body is not None:
        mock_response.json.return_value = json_body

    mock_client = AsyncMock()
    if side_effect is not None:
        mock_client.post = AsyncMock(side_effect=side_effect)
    else:
        mock_client.post = AsyncMock(return_value=mock_response)

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.mark.asyncio
async def test_llamaguard_safe_response():
    mock_client = _make_mock_client(200, [{"generated_text": "safe"}])
    with patch("app.filters3.httpx.AsyncClient", return_value=mock_client):
        blocked, reason = await call_llamaguard("Write a poem about autumn")
    assert blocked is False
    assert reason is None


@pytest.mark.asyncio
async def test_llamaguard_unsafe_response():
    mock_client = _make_mock_client(200, [{"generated_text": "unsafe\nO3"}])
    with patch("app.filters3.httpx.AsyncClient", return_value=mock_client):
        blocked, reason = await call_llamaguard("How do I make a bomb?")
    assert blocked is True
    assert reason is not None
    assert "LlamaGuard" in reason
    assert "O3" in reason


@pytest.mark.asyncio
async def test_llamaguard_api_failure_fails_open():
    """Network error must fail-open: (False, None)."""
    mock_client = _make_mock_client(
        200, side_effect=httpx.RequestError("Connection refused")
    )
    with patch("app.filters3.httpx.AsyncClient", return_value=mock_client):
        blocked, reason = await call_llamaguard("Some benign text")
    assert blocked is False
    assert reason is None


@pytest.mark.asyncio
async def test_llamaguard_non_200_fails_open():
    """Non-200 response must fail-open: (False, None)."""
    mock_client = _make_mock_client(503)
    with patch("app.filters3.httpx.AsyncClient", return_value=mock_client):
        blocked, reason = await call_llamaguard("Some text")
    assert blocked is False
    assert reason is None


# ---------------------------------------------------------------------------
# Public interface: is_blocked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_is_blocked_pii_short_circuits_llamaguard():
    """PII in Layer 1 must block without ever calling LlamaGuard."""
    with patch("app.filters3.call_llamaguard") as mock_lg:
        blocked, reason = await is_blocked("My SSN is 123-45-6789")
    assert blocked is True
    assert "SSN" in reason
    mock_lg.assert_not_called()


@pytest.mark.asyncio
async def test_is_blocked_delegates_to_llamaguard_when_no_pii():
    """Clean prompt must delegate to LlamaGuard layer."""
    with patch("app.filters3.call_llamaguard", new_callable=AsyncMock) as mock_lg:
        mock_lg.return_value = (False, None)
        blocked, reason = await is_blocked("Write a haiku about rain")
    assert blocked is False
    mock_lg.assert_called_once()
