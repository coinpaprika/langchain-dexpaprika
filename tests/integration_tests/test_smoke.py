"""Live smoke tests for parameters the standard suites do not exercise."""

from __future__ import annotations

import json

from langchain_dexpaprika import (
    DexPaprikaPoolIndicator,
    DexPaprikaPoolOHLCV,
    DexPaprikaTokenIndicator,
    DexPaprikaTokenOHLCV,
    DexPaprikaTokenPools,
)

WETH = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
USDC_WETH_POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"


def test_pool_ohlcv_inversed_flips_pair_perspective() -> None:
    tool = DexPaprikaPoolOHLCV()
    base_args = {
        "network": "ethereum",
        "pool_address": USDC_WETH_POOL,
        "start": "-24h",
        "interval": "1h",
        "limit": 2,
    }
    base = json.loads(tool.invoke(dict(base_args)))
    flipped = json.loads(tool.invoke({**base_args, "inversed": True}))
    assert base and flipped
    expected_keys = {"time_open", "time_close", "open", "high", "low", "close", "volume"}
    assert expected_keys <= set(base[0])
    assert base[0]["close"] != flipped[0]["close"]


def test_token_ohlcv_keyless_403_names_the_required_plan() -> None:
    # Live check that the plan gate is real and the message an agent gets is
    # still what our tool description promises to fall back on.
    tool = DexPaprikaTokenOHLCV()
    result = tool.invoke(
        {
            "network": "ethereum",
            "token_address": WETH,
            "start": "-24h",
            "interval": "1h",
            "limit": 3,
        }
    )
    assert "Dev or Pro plan" in result
    assert "403" in result


def test_pool_indicator_rsi_is_a_momentum_value_in_range() -> None:
    tool = DexPaprikaPoolIndicator()
    data = json.loads(
        tool.invoke(
            {
                "network": "ethereum",
                "pool_address": USDC_WETH_POOL,
                "indicator": "rsi",
                "interval": "1h",
                "start": "-6h",
            }
        )
    )
    assert data["indicator"] == "rsi"
    assert data["pool_address"] == USDC_WETH_POOL
    assert data["data"]
    for point in data["data"]:
        assert 0 <= point["value"] <= 100


def test_pool_indicator_macd_returns_macd_signal_and_histogram() -> None:
    tool = DexPaprikaPoolIndicator()
    data = json.loads(
        tool.invoke(
            {
                "network": "ethereum",
                "pool_address": USDC_WETH_POOL,
                "indicator": "macd",
                "interval": "1h",
                "start": "-6h",
            }
        )
    )
    assert data["indicator"] == "macd"
    point = data["data"][0]
    assert {"macd", "signal", "histogram", "timestamp"} <= set(point)


def test_pool_indicator_rejects_a_parameter_for_the_wrong_indicator() -> None:
    # fast_period belongs to macd; sending it with indicator=rsi is a 400 that
    # names the offending parameter, which is what our tool description
    # promises an agent will see if it mixes up the per-indicator parameters.
    tool = DexPaprikaPoolIndicator()
    result = tool.invoke(
        {
            "network": "ethereum",
            "pool_address": USDC_WETH_POOL,
            "indicator": "rsi",
            "interval": "1h",
            "start": "-6h",
            "fast_period": 3,
        }
    )
    assert "fast_period" in result


def test_token_indicator_keyless_403_names_the_required_plan() -> None:
    # Live check that the plan gate is real and the message an agent gets is
    # still what our tool description promises to fall back on.
    tool = DexPaprikaTokenIndicator()
    result = tool.invoke(
        {
            "network": "ethereum",
            "token_address": WETH,
            "indicator": "rsi",
            "interval": "1h",
            "start": "-6h",
        }
    )
    assert "Dev or Pro plan" in result
    assert "403" in result


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
