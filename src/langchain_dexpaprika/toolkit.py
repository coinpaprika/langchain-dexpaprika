"""DexPaprikaToolkit: all five DexPaprika tools behind one constructor."""

from __future__ import annotations

from langchain_core.tools import BaseTool, BaseToolkit
from pydantic import Field

from langchain_dexpaprika._client import DexPaprikaAPIWrapper
from langchain_dexpaprika.networks import DexPaprikaNetworks
from langchain_dexpaprika.pool_ohlcv import DexPaprikaPoolOHLCV
from langchain_dexpaprika.search import DexPaprikaSearch
from langchain_dexpaprika.token_details import DexPaprikaTokenDetails
from langchain_dexpaprika.token_pools import DexPaprikaTokenPools


class DexPaprikaToolkit(BaseToolkit):
    """Toolkit bundling the five DexPaprika tools over one shared HTTP client.

    Example:
        .. code-block:: python

            from langchain_dexpaprika import DexPaprikaToolkit

            toolkit = DexPaprikaToolkit()
            tools = toolkit.get_tools()
    """

    api_wrapper: DexPaprikaAPIWrapper = Field(default_factory=DexPaprikaAPIWrapper)

    def get_tools(self) -> list[BaseTool]:
        """Return one instance of each tool, all sharing this toolkit's wrapper."""
        return [
            DexPaprikaSearch(api_wrapper=self.api_wrapper),
            DexPaprikaTokenDetails(api_wrapper=self.api_wrapper),
            DexPaprikaTokenPools(api_wrapper=self.api_wrapper),
            DexPaprikaPoolOHLCV(api_wrapper=self.api_wrapper),
            DexPaprikaNetworks(api_wrapper=self.api_wrapper),
        ]
