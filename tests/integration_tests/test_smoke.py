"""Live smoke tests for parameters the standard suites do not exercise."""

from __future__ import annotations

import json

from langchain_dexpaprika import DexPaprikaPoolOHLCV, DexPaprikaTokenPools

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC_WETH_POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"


def test_pool_ohlcv_inversed_flips_pair_perspective() -> None:
    tool = DexPaprikaPoolOHLCV()
    base_args = {
        "network": "ethereum",
        "pool_address": USDC_WETH_POOL,
        "start": "2026-07-10",
        "interval": "24h",
        "limit": 2,
    }
    base = json.loads(tool.invoke(dict(base_args)))
    flipped = json.loads(tool.invoke({**base_args, "inversed": True}))
    assert base and flipped
    expected_keys = {"time_open", "time_close", "open", "high", "low", "close", "volume"}
    assert expected_keys <= set(base[0])
    assert base[0]["close"] != flipped[0]["close"]


def test_token_pools_order_by_liquidity_desc() -> None:
    tool = DexPaprikaTokenPools()
    data = json.loads(
        tool.invoke(
            {
                "network": "ethereum",
                "token_address": WETH,
                "order_by": "liquidity_usd",
                "limit": 5,
            }
        )
    )
    liquidity = [pool["liquidity_usd"] for pool in data["results"]]
    assert len(liquidity) == 5
    assert liquidity == sorted(liquidity, reverse=True)
