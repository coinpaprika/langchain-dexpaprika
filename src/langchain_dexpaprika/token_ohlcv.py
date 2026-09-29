"""dexpaprika_token_ohlcv: historical USD OHLCV candles for one token, across all its pools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import (
    DexPaprikaAPIWrapper,
    compact_json,
    encode_path_segment,
    format_validation_error,
)

Interval = Literal["1m", "5m", "10m", "15m", "30m", "1h", "6h", "12h", "24h"]


class DexPaprikaTokenOHLCVInput(BaseModel):
    """Input schema for dexpaprika_token_ohlcv."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    token_address: str = Field(
        description=(
            "Token contract address, e.g. from dexpaprika_search or dexpaprika_token_pools."
        )
    )
    start: str | int = Field(
        description=(
            "REQUIRED start of the window. Simplest is an offset back from now, which needs "
            "no knowledge of today's date: '-24h' (last 24 hours), '-7d', '-90m' (units s, "
            "m, h, d). Also 'YYYY-MM-DD', RFC3339, or Unix seconds. This endpoint needs a "
            "Dev or Pro plan; on the Dev plan history goes back 30 days."
        )
    )
    end: str | int | None = Field(
        default=None,
        description="Optional end of the window, same formats as start (e.g. '-1h').",
    )
    interval: Interval = Field(
        default="24h",
        description="Candle interval, from 1m to 24h.",
    )
    limit: int = Field(default=30, ge=1, le=1000, description="Number of candles, 1-1000.")


class DexPaprikaTokenOHLCV(BaseTool):
    """Get historical USD OHLCV candles for a token, across every pool it trades in.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaTokenOHLCV

            tool = DexPaprikaTokenOHLCV()
            tool.invoke(
                {
                    "network": "ethereum",
                    "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "start": "-24h",
                    "interval": "1h",
                    "limit": 24,
                }
            )
    """

    name: str = "dexpaprika_token_ohlcv"
    description: str = (
        "Get historical OHLCV price candles (open, high, low, close, volume, all in USD) "
        "for one token, from a volume-weighted price across every pool the token trades in "
        "on that network; volume is the USD total across those same pools. Use it for a "
        "token's overall price history instead of one pool's price, for trend and "
        "volatility analysis and charting. This endpoint needs a Dev or Pro plan: keyless "
        "and free-key calls fail with a 403 naming the required plan. If you get that 403, "
        "do not retry this tool; instead call dexpaprika_token_pools to find the token's "
        "most liquid pool and get candles from dexpaprika_pool_ohlcv on that pool instead. "
        "Pool candles are priced in the pool's other token, not USD, so prefer a pool "
        "paired with a stablecoin."
    )
    args_schema: type[BaseModel] = DexPaprikaTokenOHLCVInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        token_address: str,
        start: str | int,
        end: str | int | None = None,
        interval: Interval = "24h",
        limit: int = 30,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get(
            _path(network, token_address),
            _params(start, end, interval, limit),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(data)

    async def _arun(
        self,
        network: str,
        token_address: str,
        start: str | int,
        end: str | int | None = None,
        interval: Interval = "24h",
        limit: int = 30,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget(
            _path(network, token_address),
            _params(start, end, interval, limit),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(data)


def _path(network: str, token_address: str) -> str:
    net = encode_path_segment(network, field="network")
    token = encode_path_segment(token_address, field="token_address")
    return f"/networks/{net}/tokens/{token}/ohlcv"


def _params(
    start: str | int,
    end: str | int | None,
    interval: str,
    limit: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {"start": start, "interval": interval, "limit": limit}
    if end is not None:
        params["end"] = end
    return params


def _not_found_message(network: str, token_address: str) -> str:
    return (
        f"Token {token_address} not found on network '{network}'. Check both values; "
        "token addresses come from dexpaprika_search or dexpaprika_token_pools and "
        "network ids from dexpaprika_networks."
    )
