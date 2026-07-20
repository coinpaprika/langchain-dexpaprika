"""dexpaprika_pool_ohlcv: historical OHLCV candles for one liquidity pool."""

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


class DexPaprikaPoolOHLCVInput(BaseModel):
    """Input schema for dexpaprika_pool_ohlcv."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    pool_address: str = Field(
        description="Pool contract address, e.g. from dexpaprika_token_pools."
    )
    start: str | int = Field(
        description="REQUIRED start of the window: 'YYYY-MM-DD', RFC3339, or Unix seconds."
    )
    end: str | int | None = Field(
        default=None,
        description="Optional end of the window, same formats as start.",
    )
    interval: Interval = Field(default="24h", description="Candle interval.")
    limit: int = Field(default=30, ge=1, le=366, description="Number of candles, 1-366.")
    inversed: bool = Field(
        default=False,
        description=(
            "Set true to flip the pair and quote prices from the other token's perspective."
        ),
    )


class DexPaprikaPoolOHLCV(BaseTool):
    """Get historical OHLCV candles for a liquidity pool.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaPoolOHLCV

            tool = DexPaprikaPoolOHLCV()
            tool.invoke(
                {
                    "network": "ethereum",
                    "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                    "start": "2026-07-10",
                    "interval": "24h",
                    "limit": 3,
                }
            )
    """

    name: str = "dexpaprika_pool_ohlcv"
    description: str = (
        "Get historical OHLCV price candles (open, high, low, close, volume in USD) for "
        "one liquidity pool. Candle interval from 1 minute to 24 hours, up to 366 "
        "candles per call. Use for price history, trend and volatility analysis, and "
        "charting. The price is for the pool's token pair, not a global token average."
    )
    args_schema: type[BaseModel] = DexPaprikaPoolOHLCVInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        pool_address: str,
        start: str | int,
        end: str | int | None = None,
        interval: Interval = "24h",
        limit: int = 30,
        inversed: bool = False,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get(
            _path(network, pool_address),
            _params(start, end, interval, limit, inversed),
            not_found=_not_found_message(network, pool_address),
        )
        return compact_json(data)

    async def _arun(
        self,
        network: str,
        pool_address: str,
        start: str | int,
        end: str | int | None = None,
        interval: Interval = "24h",
        limit: int = 30,
        inversed: bool = False,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget(
            _path(network, pool_address),
            _params(start, end, interval, limit, inversed),
            not_found=_not_found_message(network, pool_address),
        )
        return compact_json(data)


def _path(network: str, pool_address: str) -> str:
    net = encode_path_segment(network, field="network")
    pool = encode_path_segment(pool_address, field="pool_address")
    return f"/networks/{net}/pools/{pool}/ohlcv"


def _params(
    start: str | int,
    end: str | int | None,
    interval: str,
    limit: int,
    inversed: bool,
) -> dict[str, Any]:
    params: dict[str, Any] = {"start": start, "interval": interval, "limit": limit}
    if end is not None:
        params["end"] = end
    if inversed:
        params["inversed"] = "true"
    return params


def _not_found_message(network: str, pool_address: str) -> str:
    return (
        f"Pool {pool_address} not found on network '{network}'. Check both values; "
        "pool addresses come from dexpaprika_token_pools and network ids from "
        "dexpaprika_networks."
    )
