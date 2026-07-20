"""dexpaprika_search: free-text search across tokens, pools, and DEXes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import (
    DexPaprikaAPIWrapper,
    compact_json,
    format_validation_error,
    truncate,
)

_DEFAULT_LIMIT = 5
_DESCRIPTION_LIMIT = 200


class DexPaprikaSearchInput(BaseModel):
    """Input schema for dexpaprika_search."""

    query: str = Field(
        description=(
            "Free-text search term: a token name, ticker symbol, pool address, "
            "or DEX name, e.g. 'PEPE' or 'WETH'."
        )
    )
    limit: int = Field(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=20,
        description=(
            "Max tokens and max pools to return, 1-20. Raise it when the same ticker "
            "trades on several chains and the one you want may be past the default 5."
        ),
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
        "Search DexPaprika for tokens, liquidity pools, and DEXes across every supported "
        "blockchain by name, symbol, or address. Keyless. Returns matching tokens, pools, "
        "and DEXes. Use this first when you only have a name or ticker and need the "
        "contract address and network id for the other DexPaprika tools: in each token "
        "result the 'id' field is the contract address (pass it as token_address) and the "
        "'chain' field is the network id (pass it as network). Results are capped at "
        "'limit' (default 5); the same token can trade on many chains, so if the chain you "
        "want is missing, raise 'limit' or check the 'tokens_truncated' count."
    )
    args_schema: type[BaseModel] = DexPaprikaSearchInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(
        self,
        query: str,
        limit: int = _DEFAULT_LIMIT,
        *,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        data = self.api_wrapper.get("/search", {"query": query})
        return compact_json(_shape(data, limit))

    async def _arun(
        self,
        query: str,
        limit: int = _DEFAULT_LIMIT,
        *,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        data = await self.api_wrapper.aget("/search", {"query": query})
        return compact_json(_shape(data, limit))


def _shape(data: Any, limit: int) -> dict[str, Any]:
    """Keep the top `limit` matches, trim descriptions, and flag any truncation."""
    if not isinstance(data, dict):
        raise ToolException("DexPaprika API returned an unexpected response shape for /search.")
    all_tokens = data.get("tokens") or []
    all_pools = data.get("pools") or []
    tokens = []
    for token in all_tokens[:limit]:
        shaped = dict(token)
        if shaped.get("description"):
            shaped["description"] = truncate(shaped["description"], _DESCRIPTION_LIMIT)
        tokens.append(shaped)
    result: dict[str, Any] = {
        "tokens": tokens,
        "pools": all_pools[:limit],
        "dexes": data.get("dexes") or [],
    }
    if len(all_tokens) > limit:
        result["tokens_truncated"] = len(all_tokens) - limit
    if len(all_pools) > limit:
        result["pools_truncated"] = len(all_pools) - limit
    return result
