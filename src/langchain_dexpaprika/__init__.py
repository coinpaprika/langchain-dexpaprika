"""LangChain tools for the DexPaprika API.

Keyless DEX market data across every network DexPaprika covers: 36 chains,
33M+ tokens, 36M+ pools. The free tier needs no API key and no signup. See
https://docs.dexpaprika.com for API documentation and
https://agents.dexpaprika.com for the agent integration guide.
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
    __version__ = metadata.version("langchain-dexpaprika")
except metadata.PackageNotFoundError:  # pragma: no cover - only during development
    __version__ = "0.0.0"

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
