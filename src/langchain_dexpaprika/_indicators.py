"""Shared pieces for the pool and token indicator tools.

Both tools expose the same `indicator` choices over the same query-parameter
surface, on a pool path and a token path respectively. Keeping the types, the
decision-relevant description text, and the parameter builder here keeps the
two tool modules from drifting apart.
"""

from __future__ import annotations

from typing import Any, Literal

IndicatorName = Literal["rsi", "ema", "macd", "bbands", "vwap"]
Interval = Literal["1m", "5m", "10m", "15m", "30m", "1h", "6h", "12h", "24h", "1d"]

INDICATOR_GUIDE = (
    "Pick one indicator per call with the 'indicator' field. rsi is a 0-100 "
    "momentum oscillator, commonly read as overbought above 70 and oversold "
    "below 30. ema is a trend-following moving average that tracks recent "
    "price more closely than a simple average. macd returns macd, signal, "
    "and histogram; the histogram changing sign (crossing zero) marks a "
    "bullish or bearish crossover between the macd and signal lines. bbands "
    "(Bollinger Bands) returns upper, middle, and lower bands, where price "
    "riding the upper or lower band signals a strong trend and a narrowing "
    "band width signals a squeeze that often precedes a breakout. vwap "
    "returns a volume-weighted average price; price trading above vwap is "
    "commonly read as bullish pressure and below vwap as bearish. These are "
    "standard technical-analysis readings, not financial advice, and work "
    "best combined with other signals rather than alone."
)

INTERVAL_FIELD_DESCRIPTION = (
    "Candle interval, from 1m to 24h ('1d' is the same interval as '24h'). "
    "Always pass this explicitly: the server default differs between "
    "keyless and keyed callers, so omitting it makes results inconsistent "
    "across calls."
)

START_FIELD_DESCRIPTION = (
    "Optional start of the window: an offset back from now ('-24h', '-7d', "
    "'-90m', units s/m/h/d), 'YYYY-MM-DD', RFC3339, or Unix seconds. Without "
    "an API key only the last 24 hours are available."
)

END_FIELD_DESCRIPTION = (
    "Optional end of the window, same formats as start. Exclusive; defaults to now."
)

CURSOR_FIELD_DESCRIPTION = (
    "Pagination cursor from a previous response's next_cursor. Do not combine with start."
)

PERIOD_FIELD_DESCRIPTION = (
    "Lookback length for rsi (default 14), ema (default 20), bbands (default "
    "20), or vwap (default 14). Not accepted by macd; sending it with "
    "indicator='macd' is rejected."
)

FAST_PERIOD_FIELD_DESCRIPTION = "macd only: fast EMA length, default 12."

SLOW_PERIOD_FIELD_DESCRIPTION = (
    "macd only: slow EMA length, default 26. Must be greater than fast_period."
)

SIGNAL_PERIOD_FIELD_DESCRIPTION = "macd only: signal line length, default 9."

STD_DEV_FIELD_DESCRIPTION = "bbands only: standard deviation multiplier for the bands, default 2."

PARAMETER_SCOPE_NOTE = (
    "Only send the parameters that apply to the chosen indicator (period "
    "for rsi, ema, bbands, and vwap; fast_period, slow_period, and "
    "signal_period for macd; std_dev for bbands). The API rejects a "
    "parameter sent for the wrong indicator with a 400 naming it, so leave "
    "the others unset rather than filling in their defaults yourself."
)


def build_params(
    indicator: str,
    interval: str | None,
    start: str | int | None,
    end: str | int | None,
    limit: int,
    cursor: str | None,
    period: int | None,
    fast_period: int | None,
    slow_period: int | None,
    signal_period: int | None,
    std_dev: float | None,
) -> dict[str, Any]:
    """Build query params, sending only what the caller actually set.

    The API rejects a parameter that belongs to a different indicator (for
    example `fast_period` with `indicator=rsi`), so we never fill in a
    default for one the caller did not pass; an unset field here stays out
    of the request entirely.
    """
    params: dict[str, Any] = {"indicator": indicator, "limit": limit}
    if interval is not None:
        params["interval"] = interval
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if cursor is not None:
        params["cursor"] = cursor
    if period is not None:
        params["period"] = period
    if fast_period is not None:
        params["fast_period"] = fast_period
    if slow_period is not None:
        params["slow_period"] = slow_period
    if signal_period is not None:
        params["signal_period"] = signal_period
    if std_dev is not None:
        params["std_dev"] = std_dev
    return params
