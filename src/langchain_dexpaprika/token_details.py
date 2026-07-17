"""dexpaprika_token_details: market data for one token on one network."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import DexPaprikaAPIWrapper, compact_json, truncate

_DESCRIPTION_LIMIT = 280
# The API also returns 30m/15m/5m/1m windows; we drop them to keep the output
# compact. 24h/6h/1h cover what agents actually reason about.
_DROPPED_WINDOWS = ("30m", "15m", "5m", "1m")


class DexPaprikaTokenDetailsInput(BaseModel):
    """Input schema for dexpaprika_token_details."""

    network: str = Field(
        description="Network id from dexpaprika_networks, e.g. 'ethereum', 'solana', 'base'."
    )
    token_address: str = Field(
        description="Token contract address (EVM 0x... or Solana mint address)."
    )


class DexPaprikaTokenDetails(BaseTool):
    """Get current market data for a single token on a specific network.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaTokenDetails

            tool = DexPaprikaTokenDetails()
            tool.invoke(
                {
                    "network": "ethereum",
                    "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
                }
            )
    """

    name: str = "dexpaprika_token_details"
    description: str = (
        "Get current market data for one token on a specific network: USD price, fully "
        "diluted valuation, total DEX liquidity in USD, number of pools, and traded "
        "volume with buy/sell breakdown over 24h/6h/1h windows. Requires the exact "
        "contract address and network id (find them with dexpaprika_search)."
    )
    args_schema: type[BaseModel] = DexPaprikaTokenDetailsInput
    handle_tool_error: bool = True
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        network: str,
        token_address: str,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get(
            _path(network, token_address),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(_shape(data))

    async def _arun(
        self,
        network: str,
        token_address: str,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget(
            _path(network, token_address),
            not_found=_not_found_message(network, token_address),
        )
        return compact_json(_shape(data))


def _path(network: str, token_address: str) -> str:
    return f"/networks/{quote(network, safe='')}/tokens/{quote(token_address, safe='')}"


def _not_found_message(network: str, token_address: str) -> str:
    return (
        f"Token {token_address} not found on network '{network}'. Check the address and "
        "the network id (use dexpaprika_networks for valid network ids, or "
        "dexpaprika_search to find the token's address and chain)."
    )


def _shape(data: dict[str, Any]) -> dict[str, Any]:
    """Trim long descriptions and drop sub-hour summary windows."""
    shaped = dict(data)
    if shaped.get("description"):
        shaped["description"] = truncate(shaped["description"], _DESCRIPTION_LIMIT)
    summary = shaped.get("summary")
    if isinstance(summary, dict):
        shaped["summary"] = {k: v for k, v in summary.items() if k not in _DROPPED_WINDOWS}
    return shaped
