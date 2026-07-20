"""dexpaprika_networks: the list of supported blockchain networks."""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_dexpaprika._client import (
    DexPaprikaAPIWrapper,
    compact_json,
    format_validation_error,
)


class DexPaprikaNetworksInput(BaseModel):
    """dexpaprika_networks takes no arguments."""


class DexPaprikaNetworks(BaseTool):
    """List every blockchain network DexPaprika covers, with activity stats.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaNetworks

            tool = DexPaprikaNetworks()
            tool.invoke({})
    """

    name: str = "dexpaprika_networks"
    description: str = (
        "List every blockchain network supported by DexPaprika with its exact "
        "network id (e.g. 'ethereum', 'solana', 'bsc', 'base'), 24h DEX volume, "
        "transaction count, and pool count. Call this when you need a valid network id "
        "or want to compare activity across chains."
    )
    args_schema: type[BaseModel] = DexPaprikaNetworksInput
    handle_tool_error: bool = True
    handle_validation_error: bool | str | Callable[..., str] | None = format_validation_error
    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def _run(self, *, run_manager: CallbackManagerForToolRun | None = None) -> str:
        return compact_json(self.api_wrapper.get("/networks"))

    async def _arun(self, *, run_manager: AsyncCallbackManagerForToolRun | None = None) -> str:
        return compact_json(await self.api_wrapper.aget("/networks"))
