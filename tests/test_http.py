from __future__ import annotations

import httpx
import pytest

from freeapis.http import HttpClient
from freeapis.models import FetchError


def test_http_retries_with_exponential_backoff():
    statuses = iter((500, 429, 200))
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(next(statuses), request=request, text="ok")

    sleeps: list[float] = []
    with HttpClient(
        max_retries=3,
        backoff=0.1,
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
    ) as client:
        assert client.get_text("https://example.com") == "ok"

    assert len(calls) == 3
    assert sleeps == [0.1, 0.2]


def test_http_does_not_retry_non_retryable_status():
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404, request=request)

    with HttpClient(
        transport=httpx.MockTransport(handler), sleeper=lambda _: None
    ) as client:
        with pytest.raises(FetchError):
            client.get_text("https://example.com/missing")
    assert len(calls) == 1
