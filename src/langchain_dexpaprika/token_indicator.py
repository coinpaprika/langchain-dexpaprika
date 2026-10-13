"""dexpaprika_token_indicator: a technical indicator from one token's OHLCV."""

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


class DexPaprikaTokenIndicatorInput(BaseModel):
    """Input schema for dexpaprika_token_indicator."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    token_address: str = Field(
        description=(
            "Token contract address, e.g. from dexpaprika_search or dexpaprika_token_pools."
        )
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


class DexPaprikaTokenIndicator(BaseTool):
    """Get a technical indicator computed from one token's OHLCV history.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaTokenIndicator

            tool = DexPaprikaTokenIndicator()
            tool.invoke(
                {
                    "network": "ethereum",
                    "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "indicator": "macd",
                    "interval": "1h",
                    "start": "-6h",
                }
            )
    """

    name: str = "dexpaprika_token_indicator"
    description: str = (
        "Get a technical indicator computed from one token's volume-weighted "
        "OHLCV history across every pool it trades in on that network: rsi, "
        "ema, macd, bbands, or vwap. "
        + INDICATOR_GUIDE
        + " "
        + PARAMETER_SCOPE_NOTE
        + " This endpoint needs a Dev or Pro plan: a keyless or "
        "free-key call fails with a 403 naming the required plan. If you get "
        "that 403, do not retry this tool; instead call dexpaprika_token_pools "
        "to find the token's most liquid pool and call dexpaprika_pool_indicator "
        "on that pool instead, which works without a key. See "
        "https://docs.dexpaprika.com/knowledge-base/rate-limits and "
        "https://dexpaprika.com/api/pricing for current plan limits."
    )
    args_schema: type[BaseModel] = DexPaprikaTokenIndicatorInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        token_address: str,
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
            _path(network, token_address),
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
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(data)

    async def _arun(
        self,
        network: str,
        token_address: str,
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
            _path(network, token_address),
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
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(data)


def _path(network: str, token_address: str) -> str:
    net = encode_path_segment(network, field="network")
    token = encode_path_segment(token_address, field="token_address")
    return f"/networks/{net}/tokens/{token}/indicators"


def _not_found_message(network: str, token_address: str) -> str:
    return (
        f"Token {token_address} not found on network '{network}'. Check both values; "
        "token addresses come from dexpaprika_search or dexpaprika_token_pools and "
        "network ids from dexpaprika_networks."
    )
