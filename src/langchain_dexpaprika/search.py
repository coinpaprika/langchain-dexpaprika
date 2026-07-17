"""dexpaprika_search: free-text search across tokens, pools, and DEXes."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import DexPaprikaAPIWrapper, compact_json, truncate

_MAX_RESULTS = 5
_DESCRIPTION_LIMIT = 200


class DexPaprikaSearchInput(BaseModel):
    """Input schema for dexpaprika_search."""

    query: str = Field(
        description=(
            "Free-text search term: a token name, ticker symbol, pool address, "
            "or DEX name, e.g. 'PEPE' or 'WETH'."
        )
    )


class DexPaprikaSearch(BaseTool):
    """Search DexPaprika for tokens, pools, and DEXes by name, symbol, or address.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaSearch

            tool = DexPaprikaSearch()
            tool.invoke({"query": "WETH"})
    """

    name: str = "dexpaprika_search"
    description: str = (
        "Search DexPaprika for tokens, liquidity pools, and DEXes across 36 blockchains "
        "by name, symbol, or address. Free and keyless. Returns matching tokens (with "
        "chain, contract address, price in USD, liquidity), pools, and DEXes. Use this "
        "first when you only have a name or ticker and need the contract address and "
        "network id for other DexPaprika tools."
    )
    args_schema: type[BaseModel] = DexPaprikaSearchInput
    handle_tool_error: bool = True
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get("/search", {"query": query})
        return compact_json(_shape(data))

    async def _arun(
        self,
        query: str,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget("/search", {"query": query})
        return compact_json(_shape(data))


def _shape(data: dict[str, Any]) -> dict[str, Any]:
    """Keep the top matches and cut multi-kilobyte token descriptions."""
    tokens = []
    for token in (data.get("tokens") or [])[:_MAX_RESULTS]:
        shaped = dict(token)
        if shaped.get("description"):
            shaped["description"] = truncate(shaped["description"], _DESCRIPTION_LIMIT)
        tokens.append(shaped)
    return {
        "tokens": tokens,
        "pools": (data.get("pools") or [])[:_MAX_RESULTS],
        "dexes": data.get("dexes") or [],
    }
