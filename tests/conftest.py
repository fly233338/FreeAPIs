from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_text():
    def load(name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    return load


@pytest.fixture
def fixture_json(fixture_text):
    def load(name: str) -> Any:
        return json.loads(fixture_text(name))

    return load


class FakeHttp:
    def __init__(
        self,
        *,
        json_payload: Any = None,
        texts: dict[str, str] | None = None,
    ) -> None:
        self.json_payload = json_payload
        self.texts = texts or {}

    def get_json(self, url: str) -> Any:
        return self.json_payload

    def get_text(self, url: str) -> str:
        return self.texts[url]
