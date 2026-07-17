from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from freeapis.models import FetchError

LOGGER = logging.getLogger(__name__)
USER_AGENT = "FreeAPIs/0.1 (public model metadata crawler)"


class HttpClient:
    def __init__(
        self,
        *,
        timeout: float = 20.0,
        max_retries: int = 3,
        backoff: float = 0.5,
        transport: httpx.BaseTransport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.max_retries = max_retries
        self.backoff = backoff
        self.sleeper = sleeper
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            transport=transport,
        )

    def __enter__(self) -> HttpClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self.client.close()

    def get_text(self, url: str) -> str:
        return self._get(url).text

    def get_json(self, url: str) -> Any:
        response = self._get(url)
        try:
            return response.json()
        except ValueError as exc:
            raise FetchError(f"{url} did not return valid JSON") from exc

    def _get(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.get(url)
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"retryable HTTP {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                response.raise_for_status()
                return response
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                retryable = isinstance(exc, httpx.RequestError) or (
                    exc.response is not None
                    and (exc.response.status_code == 429 or exc.response.status_code >= 500)
                )
                if not retryable or attempt == self.max_retries:
                    break
                delay = self.backoff * (2**attempt)
                LOGGER.warning(
                    "HTTP request failed; retrying in %.1fs (%d/%d): %s",
                    delay,
                    attempt + 1,
                    self.max_retries,
                    url,
                )
                self.sleeper(delay)
        raise FetchError(f"HTTP request failed for {url}: {last_error}") from last_error
