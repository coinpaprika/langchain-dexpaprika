"""langchain-tests standard unit suites, one per tool.

These never touch the network; we run them with pytest-socket blocking sockets
to prove it.
"""

from typing import Any

from langchain_tests.unit_tests import ToolsUnitTests

from langchain_dexpaprika import (
    DexPaprikaNetworks,
    DexPaprikaPoolOHLCV,
    DexPaprikaSearch,
    DexPaprikaTokenDetails,
    DexPaprikaTokenPools,
)

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC_WETH_POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"


class TestDexPaprikaSearchUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaSearch]:
        return DexPaprikaSearch

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"query": "WETH"}


class TestDexPaprikaTokenDetailsUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaTokenDetails]:
        return DexPaprikaTokenDetails

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"network": "ethereum", "token_address": WETH}


class TestDexPaprikaTokenPoolsUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaTokenPools]:
        return DexPaprikaTokenPools

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"network": "ethereum", "token_address": WETH, "limit": 3}


class TestDexPaprikaPoolOHLCVUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaPoolOHLCV]:
        return DexPaprikaPoolOHLCV

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {
            "network": "ethereum",
            "pool_address": USDC_WETH_POOL,
            "start": "2026-07-10",
            "interval": "24h",
            "limit": 3,
        }


class TestDexPaprikaNetworksUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaNetworks]:
        return DexPaprikaNetworks

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {}
