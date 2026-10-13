"""dexpaprika_pool_indicator: a technical indicator computed from one pool's OHLCV."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import (
    DexPaprikaAPIWrapper,
    compact_json,
    encode_path_segment,
    format_validation_error,
)
from langchain_dexpaprika._indicators import (
    CURSOR_FIELD_DESCRIPTION,
    END_FIELD_DESCRIPTION,
    FAST_PERIOD_FIELD_DESCRIPTION,
    INDICATOR_GUIDE,
    INTERVAL_FIELD_DESCRIPTION,
    PARAMETER_SCOPE_NOTE,
    PERIOD_FIELD_DESCRIPTION,
    SIGNAL_PERIOD_FIELD_DESCRIPTION,
    SLOW_PERIOD_FIELD_DESCRIPTION,
    START_FIELD_DESCRIPTION,
    STD_DEV_FIELD_DESCRIPTION,
    IndicatorName,
    Interval,
    build_params,
)


class DexPaprikaPoolIndicatorInput(BaseModel):
    """Input schema for dexpaprika_pool_indicator."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    pool_address: str = Field(
        description="Pool contract address, e.g. from dexpaprika_token_pools."
    )
    indicator: IndicatorName = Field(
        description="Which indicator to compute: 'rsi', 'ema', 'macd', 'bbands', or 'vwap'."
    )
    interval: Interval | None = Field(default=None, description=INTERVAL_FIELD_DESCRIPTION)
    start: str | int | None = Field(default=None, description=START_FIELD_DESCRIPTION)
    end: str | int | None = Field(default=None, description=END_FIELD_DESCRIPTION)
    limit: int = Field(default=100, ge=1, le=1000, description="Number of candles, 1-1000.")
    cursor: str | None = Field(default=None, description=CURSOR_FIELD_DESCRIPTION)
    period: int | None = Field(default=None, ge=1, le=200, description=PERIOD_FIELD_DESCRIPTION)
    fast_period: int | None = Field(
        default=None, ge=1, le=200, description=FAST_PERIOD_FIELD_DESCRIPTION
    )
    slow_period: int | None = Field(
        default=None, ge=2, le=200, description=SLOW_PERIOD_FIELD_DESCRIPTION
    )
    signal_period: int | None = Field(
        default=None, ge=1, le=200, description=SIGNAL_PERIOD_FIELD_DESCRIPTION
    )
    std_dev: float | None = Field(default=None, gt=0, le=10, description=STD_DEV_FIELD_DESCRIPTION)


class DexPaprikaPoolIndicator(BaseTool):
    """Get a technical indicator computed from one liquidity pool's OHLCV history.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaPoolIndicator

            tool = DexPaprikaPoolIndicator()
            tool.invoke(
                {
                    "network": "ethereum",
                    "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
                    "indicator": "rsi",
                    "interval": "1h",
                    "start": "-6h",
                }
            )
    """

    name: str = "dexpaprika_pool_indicator"
    description: str = (
        "Get a technical indicator computed from one liquidity pool's OHLCV "
        "history: rsi, ema, macd, bbands, or vwap. "
        + INDICATOR_GUIDE
        + " "
        + PARAMETER_SCOPE_NOTE
        + " Works without an API key. How far back you can query and the "
        "fastest interval available depend on your plan; see "
        "https://docs.dexpaprika.com/knowledge-base/rate-limits and "
        "https://dexpaprika.com/api/pricing for current limits."
    )
    args_schema: type[BaseModel] = DexPaprikaPoolIndicatorInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        pool_address: str,
        indicator: IndicatorName,
        interval: Interval | None = None,
        start: str | int | None = None,
        end: str | int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        period: int | None = None,
        fast_period: int | None = None,
        slow_period: int | None = None,
        signal_period: int | None = None,
        std_dev: float | None = None,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get(
            _path(network, pool_address),
            build_params(
                indicator,
                interval,
                start,
                end,
                limit,
                cursor,
                period,
                fast_period,
                slow_period,
                signal_period,
                std_dev,
            ),
            not_found=_not_found_message(network, pool_address),
        )
        return compact_json(data)

    async def _arun(
        self,
        network: str,
        pool_address: str,
        indicator: IndicatorName,
        interval: Interval | None = None,
        start: str | int | None = None,
        end: str | int | None = None,
        limit: int = 100,
        cursor: str | None = None,
        period: int | None = None,
        fast_period: int | None = None,
        slow_period: int | None = None,
        signal_period: int | None = None,
        std_dev: float | None = None,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget(
            _path(network, pool_address),
            build_params(
                indicator,
                interval,
                start,
                end,
                limit,
                cursor,
                period,
                fast_period,
                slow_period,
                signal_period,
                std_dev,
            ),
            not_found=_not_found_message(network, pool_address),
        )
        return compact_json(data)


def _path(network: str, pool_address: str) -> str:
    net = encode_path_segment(network, field="network")
    pool = encode_path_segment(pool_address, field="pool_address")
    return f"/networks/{net}/pools/{pool}/indicators"


def _not_found_message(network: str, pool_address: str) -> str:
    return (
        f"Pool {pool_address} not found on network '{network}'. Check both values; "
        "pool addresses come from dexpaprika_token_pools and network ids from "
        "dexpaprika_networks."
    )
