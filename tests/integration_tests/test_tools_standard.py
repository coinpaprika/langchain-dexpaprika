"""langchain-tests standard integration suites, one per tool.

These hit the live keyless API. Roughly 4 requests per suite (sync and async,
with and without a ToolCall), about 20 per full run. Run them serially; the
API's burst limiter allows roughly 30 requests per 20 seconds.
"""

from typing import Any

from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_dexpaprika import (
    DexPaprikaNetworks,
    DexPaprikaPoolOHLCV,
    DexPaprikaSearch,
    DexPaprikaTokenDetails,
    DexPaprikaTokenPools,
)

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC_WETH_POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"


class TestDexPaprikaSearchIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaSearch]:
        return DexPaprikaSearch

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"query": "WETH"}


class TestDexPaprikaTokenDetailsIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaTokenDetails]:
        return DexPaprikaTokenDetails

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"network": "ethereum", "token_address": WETH}


class TestDexPaprikaTokenPoolsIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaTokenPools]:
        return DexPaprikaTokenPools

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {"network": "ethereum", "token_address": WETH, "limit": 3}


class TestDexPaprikaPoolOHLCVIntegration(ToolsIntegrationTests):
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


class TestDexPaprikaNetworksIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> type[DexPaprikaNetworks]:
        return DexPaprikaNetworks

    @property
    def tool_constructor_params(self) -> dict[str, Any]:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict[str, Any]:
        return {}
