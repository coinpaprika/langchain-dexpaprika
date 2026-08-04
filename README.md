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
no API key, so there is no environment variable to set. The free tier is 200,000
credits per month per IP at 30 requests per minute, with data delayed up to 15
seconds; see https://dexpaprika.com/pricing for the paid tiers.

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
| `dexpaprika_pool_ohlcv` | `DexPaprikaPoolOHLCV` | Historical OHLCV candles for one pool, intervals from 1m to 24h, up to 366 candles per call. |
| `dexpaprika_networks` | `DexPaprikaNetworks` | Every supported network with its exact id, 24h volume, transactions, and pool counts. |

## Use the toolkit in an agent

`DexPaprikaToolkit` bundles all five tools over one shared HTTP client. The
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
        "start": "2026-07-10",
        "interval": "24h",
        "limit": 7,
    }
)
```

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
