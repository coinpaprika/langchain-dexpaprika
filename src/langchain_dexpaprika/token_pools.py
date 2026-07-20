"""dexpaprika_token_pools: liquidity pools where a token trades on one network."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import (
    DexPaprikaAPIWrapper,
    compact_json,
    encode_path_segment,
    format_validation_error,
)

OrderBy = Literal[
    "volume_usd_24h",
    "volume_usd_7d",
    "volume_usd_30d",
    "liquidity_usd",
    "txns_24h",
    "created_at",
    "price_usd",
    "price_change_percentage_24h",
]


class DexPaprikaTokenPoolsInput(BaseModel):
    """Input schema for dexpaprika_token_pools."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    token_address: str = Field(
        description="Token contract address whose pools to list (EVM 0x... or Solana mint)."
    )
    order_by: OrderBy = Field(
        default="volume_usd_24h",
        description="Field to sort the pools by.",
    )
    sort: Literal["asc", "desc"] = Field(default="desc", description="Sort direction.")
    limit: int = Field(default=10, ge=1, le=100, description="Number of pools to return, 1-100.")


class DexPaprikaTokenPools(BaseTool):
    """List the pools where a token trades on one network.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaTokenPools

            tool = DexPaprikaTokenPools()
            tool.invoke(
                {
                    "network": "ethereum",
                    "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                    "limit": 3,
                }
            )
    """

    name: str = "dexpaprika_token_pools"
    description: str = (
        "List the liquidity pools where a token trades on one network, sorted by 24h "
        "volume, liquidity, transaction count, creation date, price, or 24h price "
        "change. Returns each pool's address, DEX name, price in USD, liquidity in USD, "
        "24h/7d/30d volume, and price change percentages. Use it to find the most "
        "liquid pool for a token before fetching OHLCV candles. Note: the nested "
        "tokens list in each pool carries contract addresses only, not symbols."
    )
    args_schema: type[BaseModel] = DexPaprikaTokenPoolsInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        token_address: str,
        order_by: OrderBy = "volume_usd_24h",
        sort: Literal["asc", "desc"] = "desc",
        limit: int = 10,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get(
            _path(network),
            _params(token_address, order_by, sort, limit),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(_shape(data))

    async def _arun(
        self,
        network: str,
        token_address: str,
        order_by: OrderBy = "volume_usd_24h",
        sort: Literal["asc", "desc"] = "desc",
        limit: int = 10,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget(
            _path(network),
            _params(token_address, order_by, sort, limit),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(_shape(data))


def _path(network: str) -> str:
    return f"/networks/{encode_path_segment(network, field='network')}/pools/search"


def _params(token_address: str, order_by: str, sort: str, limit: int) -> dict[str, Any]:
    return {
        "token_address": token_address,
        "order_by": order_by,
        "sort": sort,
        "limit": limit,
    }


def _not_found_message(network: str, token_address: str) -> str:
    return (
        f"No pools found: network '{network}' or token {token_address} is unknown. "
        "Use dexpaprika_networks for valid network ids and dexpaprika_search to "
        "find the token's address and chain."
    )


def _shape(data: Any) -> dict[str, Any]:
    """Pass pools through untouched, keeping the cursor so agents can paginate."""
    if not isinstance(data, dict):
        raise ToolException("DexPaprika API returned an unexpected response shape for pools.")
    return {
        "results": data.get("results") or [],
        "has_next_page": data.get("has_next_page", False),
        "next_cursor": data.get("next_cursor"),
    }
