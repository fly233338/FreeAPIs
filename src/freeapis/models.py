from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ModelRecord:
    provider: str
    model_id: str
    name: str
    output_types: tuple[str, ...]
    free_type: str
    model_url: str
    api_key_url: str
    docs_url: str
    source_url: str
    last_updated: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["output_types"] = list(self.output_types)
        return data


@dataclass(frozen=True, slots=True)
class ProviderResult:
    provider: str
    source_url: str
    models: tuple[ModelRecord, ...]


class FreeAPIsError(Exception):
    """Base exception for expected application failures."""


class FetchError(FreeAPIsError):
    """A provider could not produce a valid, non-empty result."""


class ValidationError(FreeAPIsError):
    """Generated data failed schema or consistency validation."""
