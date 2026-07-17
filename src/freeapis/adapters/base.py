from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from freeapis.http import HttpClient
from freeapis.models import ProviderResult
from freeapis.validation import validate_provider_result


class ProviderAdapter(ABC):
    provider: str
    source_url: str

    def __init__(self, http: HttpClient, *, confirmed_on: date | None = None) -> None:
        self.http = http
        self.confirmed_on = confirmed_on or date.today()

    @abstractmethod
    def fetch(self) -> ProviderResult:
        """Fetch and validate a complete provider snapshot."""

    def result(self, models: list) -> ProviderResult:
        result = ProviderResult(
            provider=self.provider,
            source_url=self.source_url,
            models=tuple(sorted(models, key=lambda model: model.model_id)),
        )
        validate_provider_result(result)
        return result
