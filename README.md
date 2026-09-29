# langchain-dexpaprika

[![PyPI version](https://img.shields.io/pypi/v/langchain-dexpaprika)](https://pypi.org/project/langchain-dexpaprika/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

DexPaprika tools for LangChain agents. No API key and no signup to start: the
[DexPaprika API](https://docs.dexpaprika.com) free tier is keyless, so your agent
gets DEX market data across every supported blockchain (36 chains, 33M+ tokens,
36M+ pools) as soon as you install the package.

We built these tools for LLM consumption: descriptions tell the model exactly
which parameters exist and where to get their values, error messages quote the
API's own allowed-value lists so the model can self-correct, and outputs are
compact JSON with multi-kilobyte token descriptions trimmed.

## Installation

```bash
pip install -U langchain-dexpaprika
```

No credentials to configure. This package calls the keyless free tier and sends
no API key, so there is no environment variable to set. The free tier is keyless,
with data delayed up to 15 seconds; see
https://docs.dexpaprika.com/knowledge-base/rate-limits for the current rates and
quotas, and https://dexpaprika.com/api/pricing for the paid tiers.

## Quickstart

```python
from langchain_dexpaprika import DexPaprikaSearch

search = DexPaprikaSearch()
print(search.invoke({"query": "WETH"}))
```

This returns compact JSON with matching tokens (contract address, chain, USD
price, liquidity), pools, and DEXes.

## Tools

| Tool name | Class | What it returns |
| --- | --- | --- |
| `dexpaprika_search` | `DexPaprikaSearch` | Tokens, pools, and DEXes matching a name, symbol, or address. The entry point when you only have a ticker. |
| `dexpaprika_token_details` | `DexPaprikaTokenDetails` | Price, FDV, liquidity, pool count, and 24h/6h/1h volume with buy/sell breakdown for one token on one network. |
| `dexpaprika_token_pools` | `DexPaprikaTokenPools` | Pools where a token trades, sortable by volume, liquidity, transactions, age, price, or 24h price change. |
| `dexpaprika_pool_ohlcv` | `DexPaprikaPoolOHLCV` | Historical OHLCV candles for one pool, intervals from 1m to 24h, up to 1000 candles per call. History depth depends on your plan. |
| `dexpaprika_token_ohlcv` | `DexPaprikaTokenOHLCV` | Historical USD OHLCV candles for one token, volume-weighted across every pool it trades in on that network. Needs a Dev or Pro plan; see [get OHLCV data for a token](https://docs.dexpaprika.com/api-reference/tokens/get-ohlcv-data-for-a-token). |
| `dexpaprika_networks` | `DexPaprikaNetworks` | Every supported network with its exact id, 24h volume, transactions, and pool counts. |

## Use the toolkit in an agent

`DexPaprikaToolkit` bundles all six tools over one shared HTTP client. The
example below drives them with an Anthropic model, so install the provider and
set its key first (swap in any chat model you prefer):

```bash
pip install -U "langchain[anthropic]"
export ANTHROPIC_API_KEY=...
```

```python
from langchain.agents import create_agent
from langchain_dexpaprika import DexPaprikaToolkit

toolkit = DexPaprikaToolkit()
agent = create_agent("claude-sonnet-4-5", toolkit.get_tools())
result = agent.invoke(
    {"messages": [("user", "Find the most liquid WETH pool on ethereum")]}
)
```

The tool descriptions chain naturally: an agent starts with
`dexpaprika_search` to resolve a ticker into a contract address and network
id, then feeds those into the other tools.

## Individual tools

Every tool works standalone, sync and async:

```python
from langchain_dexpaprika import DexPaprikaPoolOHLCV

ohlcv = DexPaprikaPoolOHLCV()
candles = ohlcv.invoke(
    {
        "network": "ethereum",
        "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "start": "-24h",  # the last 24 hours, which works without a key
        "interval": "1h",
        "limit": 24,
    }
)
```

`start` and `end` take an offset back from now (`-24h`, `-7d`, `-90m`) as well
as `YYYY-MM-DD`, RFC3339 and Unix seconds. How far back you can go and how fine
the candles can be depends on your plan: without a key, the last 24 hours at
`1h` and longer; a free key opens 7 days at `10m` and longer; Dev 30 days at
every interval; Pro with no plan limit on history. A request outside your plan fails with the API's
message, which names the plan that allows it. Full table: [OHLCV limits by
plan](https://docs.dexpaprika.com/knowledge-base/rate-limits#ohlcv-limits-by-plan).

### Token OHLCV (Dev and Pro plans)

`dexpaprika_token_ohlcv` returns the same candle shape, but for a token instead
of a single pool: open, high, low, close and volume, all in USD, computed from
a volume-weighted price across every pool the token trades in on that network,
with volume summed in USD across those same pools. Use it when you want one
token's overall price history rather than the price in one specific pool.

```python
from langchain_dexpaprika import DexPaprikaTokenOHLCV

token_ohlcv = DexPaprikaTokenOHLCV()
candles = token_ohlcv.invoke(
    {
        "network": "ethereum",
        "token_address": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
        "start": "-24h",
        "interval": "1h",
        "limit": 24,
    }
)
```

This endpoint needs a Dev or Pro plan. A keyless or free-key call fails with a
403 and a message naming the required plan; on that 403, call
`dexpaprika_token_pools` to find the token's most liquid pool and fetch candles
from `dexpaprika_pool_ohlcv` on that pool instead. Pool candles are priced in the
pool's other token, not in USD, so pick a stablecoin pair where you can. See [get OHLCV data for a
token](https://docs.dexpaprika.com/api-reference/tokens/get-ohlcv-data-for-a-token)
and the [pricing page](https://dexpaprika.com/api/pricing) for which plan you
need. Dev and Pro keys call `https://api-pro.dexpaprika.com`; see "Using an API
key" below for how to point a wrapper at it.

## Using an API key (optional)

**The toolkit works without a key.** No signup, no card.

A [free key](https://console.dexpaprika.com) raises the monthly credit allowance
and the per-minute request limit, and opens 7 days of OHLCV history. Current
figures are on the [rate limits page](https://docs.dexpaprika.com/knowledge-base/rate-limits).

```python
from langchain_dexpaprika import DexPaprikaToolkit
from langchain_dexpaprika._client import DexPaprikaAPIWrapper

toolkit = DexPaprikaToolkit(api_wrapper=DexPaprikaAPIWrapper(api_key="api_your_key"))

# Or leave it out and set DEXPAPRIKA_API_KEY in the environment
toolkit = DexPaprikaToolkit()
```

An explicit `api_key` beats the environment variable, and no key at all keeps the
previous keyless behaviour unchanged.

The key is excluded from `repr()` and `model_dump()`, because these wrappers end
up inside agent traces and serialized chains, and a key in a trace is a
credential in somebody's logs.

The key is sent as the entire `Authorization` value, with nothing in front of it.

**Dev and Pro customers** also set `base_url` to `https://api-pro.dexpaprika.com`. The
host never changes on its own, because a free key sent to the Pro host returns
403.

## Error handling

We surface API errors as messages the agent can act on:

- 400 responses quote the API's message verbatim, including the exact list of
  allowed values for the offending parameter.
- 404 responses arrive with an empty body, so we synthesize a message that
  names the missing identifier and points at the tool that lists valid values.
- 429 responses are retried automatically, honoring the `Retry-After` header,
  before we tell the agent to slow down.
- 410 responses (removed endpoints) surface the replacement endpoint the API
  reports, with a hint to upgrade the package.

## Development

```bash
uv venv
uv pip install -e '.[test]'
make lint                # ruff + mypy
make test                # unit tests, sockets blocked
make integration_tests   # live API, keyless, run serially
```

## Links

- [DexPaprika API documentation](https://docs.dexpaprika.com)
- [DexPaprika agent integration guide](https://agents.dexpaprika.com)
- [API reference](https://docs.dexpaprika.com/api-reference/introduction)

## License

MIT
