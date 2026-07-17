"""Unit tests for the shared client: error translation, retries, output shaping.

Everything runs against an httpx.MockTransport, so no sockets are opened.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from langchain_core.tools import ToolException
from pytest_mock import MockerFixture

from langchain_dexpaprika import (
    DexPaprikaNetworks,
    DexPaprikaPoolOHLCV,
    DexPaprikaSearch,
    DexPaprikaTokenDetails,
    DexPaprikaTokenPools,
    DexPaprikaToolkit,
)
from langchain_dexpaprika._client import DexPaprikaAPIWrapper

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"

BAD_ORDER_BY_MESSAGE = (
    "invalid query parameters: order_by (must be one of [volume_usd_24h volume_usd_7d "
    "volume_usd_30d liquidity_usd txns_24h created_at price_usd "
    "price_change_percentage_24h])"
)


def make_wrapper(handler: Any) -> DexPaprikaAPIWrapper:
    return DexPaprikaAPIWrapper(transport=httpx.MockTransport(handler))


def test_400_message_surfaces_verbatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": BAD_ORDER_BY_MESSAGE})

    wrapper = make_wrapper(handler)
    with pytest.raises(ToolException) as exc_info:
        wrapper.get("/networks/ethereum/pools/search", {"order_by": "bogus"})
    assert str(exc_info.value) == BAD_ORDER_BY_MESSAGE


def test_404_empty_body_synthesizes_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, content=b"")

    tool = DexPaprikaTokenDetails(api_wrapper=make_wrapper(handler))
    # handle_tool_error=True turns the ToolException into an error string.
    result = tool.invoke({"network": "notachain", "token_address": WETH})
    assert WETH in result
    assert "notachain" in result
    assert "dexpaprika_networks" in result


def test_410_surfaces_replacement_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            410,
            json={
                "code": 410,
                "message": "endpoint removed",
                "replacement": "/networks/:network/pools/search",
            },
        )

    wrapper = make_wrapper(handler)
    with pytest.raises(ToolException) as exc_info:
        wrapper.get("/networks/ethereum/tokens/0xabc/pools")
    message = str(exc_info.value)
    assert "HTTP 410" in message
    assert "/networks/:network/pools/search" in message


def test_429_honors_retry_after_then_succeeds(mocker: MockerFixture) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "20"})
        return httpx.Response(200, json={"ok": True})

    sleep = mocker.patch("langchain_dexpaprika._client.time.sleep")
    wrapper = make_wrapper(handler)
    assert wrapper.get("/networks") == {"ok": True}
    assert len(calls) == 2
    sleep.assert_called_once_with(20.0)


def test_429_exhausted_raises(mocker: MockerFixture) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "20"})

    mocker.patch("langchain_dexpaprika._client.time.sleep")
    wrapper = make_wrapper(handler)
    with pytest.raises(ToolException, match="rate limit"):
        wrapper.get("/networks")
    # Initial request plus max_retries (default 2).
    assert len(calls) == 3


async def test_async_429_honors_retry_after(mocker: MockerFixture) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "20"})
        return httpx.Response(200, json={"ok": True})

    sleep = mocker.patch("langchain_dexpaprika._client.asyncio.sleep")
    wrapper = make_wrapper(handler)
    assert await wrapper.aget("/networks") == {"ok": True}
    assert len(calls) == 2
    sleep.assert_called_once_with(20.0)


async def test_async_400_message_surfaces_verbatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": BAD_ORDER_BY_MESSAGE})

    wrapper = make_wrapper(handler)
    with pytest.raises(ToolException) as exc_info:
        await wrapper.aget("/networks/ethereum/pools/search")
    assert str(exc_info.value) == BAD_ORDER_BY_MESSAGE


def test_search_truncates_descriptions_and_caps_results() -> None:
    tokens = [
        {"id": f"0x{i}", "chain": "ethereum", "symbol": f"T{i}", "description": "x" * 1000}
        for i in range(8)
    ]
    pools = [{"id": f"0xp{i}", "chain": "ethereum"} for i in range(7)]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"tokens": tokens, "pools": pools, "dexes": []})

    tool = DexPaprikaSearch(api_wrapper=make_wrapper(handler))
    data = json.loads(tool.invoke({"query": "WETH"}))
    assert len(data["tokens"]) == 5
    assert len(data["pools"]) == 5
    for token in data["tokens"]:
        assert len(token["description"]) <= 200
        assert token["description"].endswith("...")


def test_token_details_drops_short_windows_and_truncates_description() -> None:
    summary = {
        "price_usd": 1800.0,
        "fdv": 1.0,
        "liquidity_usd": 2.0,
        "pools": 3,
        "24h": {"volume_usd": 1.0},
        "6h": {"volume_usd": 1.0},
        "1h": {"volume_usd": 1.0},
        "30m": {"volume_usd": 1.0},
        "15m": {"volume_usd": 1.0},
        "5m": {"volume_usd": 1.0},
        "1m": {"volume_usd": 1.0},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"id": WETH, "symbol": "WETH", "description": "y" * 2000, "summary": summary},
        )

    tool = DexPaprikaTokenDetails(api_wrapper=make_wrapper(handler))
    data = json.loads(tool.invoke({"network": "ethereum", "token_address": WETH}))
    assert len(data["description"]) <= 280
    assert {"24h", "6h", "1h"} <= set(data["summary"])
    assert not {"30m", "15m", "5m", "1m"} & set(data["summary"])


def test_token_pools_keeps_pagination_cursor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "results": [{"id": "0xpool"}],
                "has_next_page": True,
                "next_cursor": "abc123",
                "query": "ignored",
            },
        )

    tool = DexPaprikaTokenPools(api_wrapper=make_wrapper(handler))
    data = json.loads(tool.invoke({"network": "ethereum", "token_address": WETH}))
    assert data == {"results": [{"id": "0xpool"}], "has_next_page": True, "next_cursor": "abc123"}


def test_pool_ohlcv_builds_params_and_omits_defaults() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    tool = DexPaprikaPoolOHLCV(api_wrapper=make_wrapper(handler))
    tool.invoke(
        {
            "network": "ethereum",
            "pool_address": "0xpool",
            "start": "2026-07-10",
            "limit": 3,
        }
    )
    tool.invoke(
        {
            "network": "ethereum",
            "pool_address": "0xpool",
            "start": "2026-07-10",
            "end": "2026-07-12",
            "inversed": True,
        }
    )
    first, second = (dict(httpx.QueryParams(r.url.query)) for r in seen)
    assert first == {"start": "2026-07-10", "interval": "24h", "limit": "3"}
    assert second["inversed"] == "true"
    assert second["end"] == "2026-07-12"


def test_networks_sends_user_agent_and_returns_compact_json() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"id": "ethereum", "display_name": "Ethereum"}])

    tool = DexPaprikaNetworks(api_wrapper=make_wrapper(handler))
    result = tool.invoke({})
    assert result == '[{"id":"ethereum","display_name":"Ethereum"}]'
    assert seen[0].headers["User-Agent"].startswith("langchain-dexpaprika/")


def test_toolkit_returns_five_tools_sharing_one_wrapper() -> None:
    toolkit = DexPaprikaToolkit()
    tools = toolkit.get_tools()
    assert [tool.name for tool in tools] == [
        "dexpaprika_search",
        "dexpaprika_token_details",
        "dexpaprika_token_pools",
        "dexpaprika_pool_ohlcv",
        "dexpaprika_networks",
    ]
    wrappers = {id(tool.api_wrapper) for tool in tools}  # type: ignore[attr-defined]
    assert wrappers == {id(toolkit.api_wrapper)}
