"""Regression tests for the pre-release hardening pass.

Covered here: validation errors come back as recoverable tool messages, an
unexpected (non-object) 200 body is a ToolException not a raw traceback,
dot-segment path arguments are rejected, search reports truncation and honors
its limit, non-ASCII output is not escaped, OHLCV accepts an integer start, and
sockets are blocked by configuration rather than only by CLI flag.
"""

from __future__ import annotations

import json
import socket
from typing import Any

import httpx
import pytest
from pytest_socket import SocketBlockedError

from langchain_dexpaprika import (
    DexPaprikaPoolOHLCV,
    DexPaprikaSearch,
    DexPaprikaTokenDetails,
    DexPaprikaTokenPools,
)
from langchain_dexpaprika._client import DexPaprikaAPIWrapper, compact_json

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"


def wrapper_returning(body: Any, status: int = 200) -> DexPaprikaAPIWrapper:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body)

    return DexPaprikaAPIWrapper(transport=httpx.MockTransport(handler))


# --- validation errors are recoverable, not raw exceptions (finding #2) ---


def test_bad_enum_casing_returns_helpful_message() -> None:
    tool = DexPaprikaTokenPools(api_wrapper=wrapper_returning({"results": []}))
    out = tool.invoke({"network": "ethereum", "token_address": WETH, "order_by": "VOLUME_USD_24H"})
    assert isinstance(out, str)
    assert "order_by" in out
    # the allowed values are surfaced so the model can self-correct
    assert "volume_usd_24h" in out


def test_missing_required_arg_returns_helpful_message() -> None:
    tool = DexPaprikaTokenDetails(api_wrapper=wrapper_returning({"id": WETH}))
    out = tool.invoke({"network": "ethereum"})
    assert "token_address" in out


def test_out_of_range_limit_returns_helpful_message() -> None:
    tool = DexPaprikaTokenPools(api_wrapper=wrapper_returning({"results": []}))
    out = tool.invoke({"network": "ethereum", "token_address": WETH, "limit": 0})
    assert "limit" in out


# --- unexpected 200 body shape is a clean ToolException (finding #3) ---


@pytest.mark.parametrize("body", [[], "surprise", 123])
def test_search_unexpected_body_is_tool_error(body: Any) -> None:
    tool = DexPaprikaSearch(api_wrapper=wrapper_returning(body))
    out = tool.invoke({"query": "x"})
    assert "unexpected response shape" in out


def test_token_details_unexpected_body_is_tool_error() -> None:
    # Previously dict([]) silently returned "{}"; now it is a clean error.
    tool = DexPaprikaTokenDetails(api_wrapper=wrapper_returning([]))
    out = tool.invoke({"network": "ethereum", "token_address": WETH})
    assert "unexpected response shape" in out


def test_token_pools_unexpected_body_is_tool_error() -> None:
    tool = DexPaprikaTokenPools(api_wrapper=wrapper_returning([]))
    out = tool.invoke({"network": "ethereum", "token_address": WETH})
    assert "unexpected response shape" in out


# --- dot-segment path arguments cannot escape the prefix (finding #4) ---


@pytest.mark.parametrize("bad", ["..", ".", "..."])
def test_dot_segment_network_rejected(bad: str) -> None:
    tool = DexPaprikaTokenDetails(api_wrapper=wrapper_returning({"id": WETH}))
    out = tool.invoke({"network": bad, "token_address": WETH})
    assert "Invalid network" in out


def test_dot_segment_pool_address_rejected() -> None:
    tool = DexPaprikaPoolOHLCV(api_wrapper=wrapper_returning([]))
    out = tool.invoke({"network": "ethereum", "pool_address": "..", "start": "2026-07-10"})
    assert "Invalid pool_address" in out


# --- search truncation signal and limit (finding #1) ---


def test_search_reports_truncation_and_honors_limit() -> None:
    tokens = [{"id": f"0x{i}", "chain": "ethereum"} for i in range(8)]
    pools = [{"id": f"0xp{i}"} for i in range(7)]
    tool = DexPaprikaSearch(
        api_wrapper=wrapper_returning({"tokens": tokens, "pools": pools, "dexes": []})
    )

    capped = json.loads(tool.invoke({"query": "x", "limit": 3}))
    assert len(capped["tokens"]) == 3
    assert capped["tokens_truncated"] == 5
    assert capped["pools_truncated"] == 4

    full = json.loads(tool.invoke({"query": "x", "limit": 20}))
    assert "tokens_truncated" not in full
    assert "pools_truncated" not in full


# --- output compactness and typing (findings #13, #14) ---


def test_compact_json_keeps_non_ascii_unescaped() -> None:
    out = compact_json({"name": "Café ☕ 币"})
    assert "Café ☕ 币" in out
    assert "\\u" not in out
    assert json.loads(out)["name"] == "Café ☕ 币"


def test_pool_ohlcv_accepts_integer_start() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    tool = DexPaprikaPoolOHLCV(
        api_wrapper=DexPaprikaAPIWrapper(transport=httpx.MockTransport(handler))
    )
    tool.invoke({"network": "ethereum", "pool_address": "0xpool", "start": 1752192000, "limit": 2})
    params = dict(httpx.QueryParams(seen[0].url.query))
    assert params["start"] == "1752192000"


# --- hermeticity is enforced by config, not just the CLI flag (finding #15) ---


def test_sockets_blocked_by_config() -> None:
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
