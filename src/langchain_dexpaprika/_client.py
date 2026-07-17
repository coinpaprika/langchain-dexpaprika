"""Thin sync and async HTTP client for the public DexPaprika API.

We keep every HTTP concern in one place: base URL, timeout, User-Agent,
retry-on-429, and the translation of API error responses into ToolException
messages that an agent can act on. The API is keyless, so there is no
credential handling anywhere in this package.
"""

from __future__ import annotations

import asyncio
import json
import time
from importlib import metadata
from typing import Any

import httpx
from langchain_core.tools import ToolException
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

DEFAULT_BASE_URL = "https://api.dexpaprika.com"
DEFAULT_RETRY_AFTER_SECONDS = 20.0

try:
    _VERSION = metadata.version("langchain-dexpaprika")
except metadata.PackageNotFoundError:  # pragma: no cover - only during development
    _VERSION = "0.0.0"

USER_AGENT = f"langchain-dexpaprika/{_VERSION}"


def truncate(text: str | None, limit: int) -> str | None:
    """Cut a string to at most ``limit`` characters, marking the cut with an ellipsis."""
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def compact_json(data: Any) -> str:
    """Serialize tool output as compact JSON to keep token usage low."""
    return json.dumps(data, separators=(",", ":"), default=str)


def _retry_after_seconds(response: httpx.Response) -> float:
    """Read the Retry-After header (the API sends 20), clamped to a sane range."""
    raw = response.headers.get("Retry-After")
    try:
        seconds = float(raw) if raw is not None else DEFAULT_RETRY_AFTER_SECONDS
    except ValueError:
        seconds = DEFAULT_RETRY_AFTER_SECONDS
    return min(max(seconds, 1.0), 60.0)


def _json_body(response: httpx.Response) -> dict[str, Any]:
    """Parse an error body if there is one; DexPaprika 404s have an empty body."""
    try:
        body = response.json()
    except (json.JSONDecodeError, ValueError):
        return {}
    return body if isinstance(body, dict) else {}


def _process_response(response: httpx.Response, path: str, *, not_found: str | None) -> Any:
    """Turn an httpx response into parsed JSON or a ToolException the agent can act on."""
    status = response.status_code
    if 200 <= status < 300:
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ToolException(
                f"DexPaprika API returned a non-JSON body for {path} (HTTP {status})."
            ) from exc
    body = _json_body(response)
    if status == 400:
        # The API's 400 messages list the exact allowed values for a bad
        # parameter, so we surface them verbatim; that lets the agent
        # self-correct on the next call.
        message = body.get("message")
        if message:
            raise ToolException(str(message))
        raise ToolException(f"DexPaprika API rejected the request to {path} (HTTP 400).")
    if status == 404:
        # 404 responses come with an empty body, so we synthesize the message.
        raise ToolException(
            not_found
            or (
                f"DexPaprika API has no data for {path} (HTTP 404). Check every identifier "
                "in the request; valid network ids come from the dexpaprika_networks tool."
            )
        )
    if status == 410:
        # Removed endpoints answer 410 with a JSON body naming the replacement,
        # for example {"code":410,"message":"endpoint removed",
        # "replacement":"/networks/:network/pools/search"}.
        replacement = body.get("replacement")
        hint = f" The API reports the replacement endpoint: {replacement}." if replacement else ""
        raise ToolException(
            f"DexPaprika API removed the endpoint {path} (HTTP 410).{hint} "
            "Upgrade langchain-dexpaprika to a release that uses the replacement endpoint."
        )
    if status == 429:
        raise ToolException(
            "DexPaprika API rate limit hit (HTTP 429) and retries were exhausted. The "
            "keyless tier allows short bursts of roughly 30 requests per 20 seconds; "
            "wait about 20 seconds before the next call."
        )
    raise ToolException(f"DexPaprika API returned HTTP {status} for {path}.")


class DexPaprikaAPIWrapper(BaseModel):
    """Shared sync and async HTTP wrapper for the DexPaprika REST API.

    One instance can back any number of tools; the toolkit shares a single
    wrapper across all five. No API key is needed: the DexPaprika API is
    public and keyless.

    Attributes:
        base_url: API origin. Override it to point tools at a mock server in
            tests or at a different deployment.
        timeout: Per-request timeout in seconds.
        max_retries: How many times a 429 is retried (honoring Retry-After)
            before we give up and raise a ToolException.
        transport: Optional httpx transport, used by our unit tests to inject
            an ``httpx.MockTransport``. Leave unset in production.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_url: str = DEFAULT_BASE_URL
    timeout: float = 15.0
    max_retries: int = 2
    transport: Any = Field(default=None, exclude=True, repr=False)

    _sync_client: httpx.Client | None = PrivateAttr(default=None)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self._headers(),
                transport=self.transport,
            )
        return self._sync_client

    def _new_async_client(self) -> httpx.AsyncClient:
        # We build a fresh async client per call. Caching one would bind its
        # connection pool to whichever event loop ran first, which breaks the
        # next call when a framework spins up a new loop. At one request per
        # tool call the pooling win would be negligible anyway.
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._headers(),
            transport=self.transport,
        )

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        not_found: str | None = None,
    ) -> Any:
        """GET ``path`` and return parsed JSON, retrying 429s per Retry-After."""
        attempt = 0
        while True:
            try:
                response = self._get_sync_client().get(path, params=params)
            except httpx.HTTPError as exc:
                raise ToolException(f"DexPaprika API request to {path} failed: {exc}") from exc
            if response.status_code == 429 and attempt < self.max_retries:
                attempt += 1
                time.sleep(_retry_after_seconds(response))
                continue
            return _process_response(response, path, not_found=not_found)

    async def aget(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        not_found: str | None = None,
    ) -> Any:
        """Async variant of :meth:`get`."""
        async with self._new_async_client() as client:
            attempt = 0
            while True:
                try:
                    response = await client.get(path, params=params)
                except httpx.HTTPError as exc:
                    raise ToolException(f"DexPaprika API request to {path} failed: {exc}") from exc
                if response.status_code == 429 and attempt < self.max_retries:
                    attempt += 1
                    await asyncio.sleep(_retry_after_seconds(response))
                    continue
                return _process_response(response, path, not_found=not_found)
