"""LangChain tools for the DexPaprika API.

Free, keyless DEX market data across 36 blockchains: 33M+ tokens, 36M+ pools.
No API key, no signup. See https://docs.dexpaprika.com for API documentation
and https://agents.dexpaprika.com for the agent integration guide.
"""

from importlib import metadata

from langchain_dexpaprika._client import DexPaprikaAPIWrapper
from langchain_dexpaprika.networks import DexPaprikaNetworks
from langchain_dexpaprika.pool_ohlcv import DexPaprikaPoolOHLCV
from langchain_dexpaprika.search import DexPaprikaSearch
from langchain_dexpaprika.token_details import DexPaprikaTokenDetails
from langchain_dexpaprika.token_pools import DexPaprikaTokenPools
from langchain_dexpaprika.toolkit import DexPaprikaToolkit

try:
    __version__ = metadata.version(__package__ or "langchain-dexpaprika")
except metadata.PackageNotFoundError:  # pragma: no cover - only during development
    __version__ = ""

__all__ = [
    "DexPaprikaAPIWrapper",
    "DexPaprikaNetworks",
    "DexPaprikaPoolOHLCV",
    "DexPaprikaSearch",
    "DexPaprikaTokenDetails",
    "DexPaprikaTokenPools",
    "DexPaprikaToolkit",
    "__version__",
]
