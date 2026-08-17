"""Optional API key, and the header rules that go with it.

Assertions run against the request that reaches an httpx.MockTransport, so they
describe what would leave the process rather than what was stored on the model.

The Bearer rule is the regression this file exists for: ``Authorization: Bearer
api_...`` returns 401 because the API checksums the raw header value, and the
mistake has resurfaced three times in four months.
"""

from __future__ import annotations

import httpx
import pytest

from langchain_dexpaprika._client import (
    API_KEY_ENV_VAR,
    USER_AGENT,
    DexPaprikaAPIWrapper,
    resolve_api_key,
)


def headers_seen(**kwargs: object) -> httpx.Headers:
    """Build a wrapper, make one call, return the headers the server received."""
    captured: dict[str, httpx.Headers] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        return httpx.Response(200, json=[])

    wrapper = DexPaprikaAPIWrapper(transport=httpx.MockTransport(handler), **kwargs)
    wrapper.get("/networks")
    return captured["headers"]


# ── The Bearer rule ────────────────────────────────────────────────────────


def test_key_is_the_entire_authorization_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    assert headers_seen(api_key="api_abc123")["authorization"] == "api_abc123"


@pytest.mark.parametrize("scheme", ["Bearer", "Token", "ApiKey", "Basic", "Key"])
def test_no_scheme_word_is_ever_prepended(monkeypatch: pytest.MonkeyPatch, scheme: str) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    value = headers_seen(api_key="api_abc123")["authorization"]
    assert not value.lower().startswith(scheme.lower())


# ── Keyless stays the default ──────────────────────────────────────────────


def test_no_key_sends_no_authorization_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    assert "authorization" not in headers_seen()


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_blank_key_is_keyless_not_an_empty_header(
    monkeypatch: pytest.MonkeyPatch, blank: str
) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    assert "authorization" not in headers_seen(api_key=blank)


# ── Precedence ─────────────────────────────────────────────────────────────


def test_environment_variable_is_used_when_no_argument_is_given() -> None:
    assert resolve_api_key(env={API_KEY_ENV_VAR: "api_from_env"}) == "api_from_env"


def test_explicit_argument_beats_the_environment() -> None:
    assert resolve_api_key("api_explicit", env={API_KEY_ENV_VAR: "api_from_env"}) == "api_explicit"


def test_environment_key_reaches_the_wire(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(API_KEY_ENV_VAR, "api_from_env")
    assert headers_seen()["authorization"] == "api_from_env"


def test_surrounding_whitespace_is_trimmed() -> None:
    assert resolve_api_key("  api_padded\n") == "api_padded"


# ── Header injection ───────────────────────────────────────────────────────


@pytest.mark.parametrize("hostile", ["api_a\r\nX-Evil: 1", "api_a\nb", "api_a\0b"])
def test_key_with_control_characters_is_dropped(hostile: str) -> None:
    # Dropped rather than sanitized: a mangled key authenticates as nobody, and
    # the data endpoints ignore an unreadable key instead of rejecting it, so
    # the caller would never find out.
    assert resolve_api_key(hostile) is None


# ── Identification and hosts ───────────────────────────────────────────────


def test_user_agent_is_always_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    assert headers_seen()["user-agent"] == USER_AGENT
    assert headers_seen(api_key="api_abc123")["user-agent"] == USER_AGENT


def test_a_key_alone_never_changes_the_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Free keys are served from the default host; only Pro moves, and a free key
    # sent to the Pro host returns 403.
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    wrapper = DexPaprikaAPIWrapper(api_key="api_abc123")
    assert wrapper.base_url == "https://api.dexpaprika.com"


def test_pro_customers_set_the_host_explicitly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    wrapper = DexPaprikaAPIWrapper(api_key="api_pro", base_url="https://api-pro.dexpaprika.com")
    assert wrapper.base_url == "https://api-pro.dexpaprika.com"


# ── The key must not leak ──────────────────────────────────────────────────


def test_the_key_is_not_in_the_repr_or_a_dump(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # These wrappers end up inside agent traces and serialized chains, so a key
    # in repr() or model_dump() is a credential in somebody's logs.
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    wrapper = DexPaprikaAPIWrapper(api_key="api_secret_value")
    assert "api_secret_value" not in repr(wrapper)
    assert "api_secret_value" not in str(wrapper.model_dump())
