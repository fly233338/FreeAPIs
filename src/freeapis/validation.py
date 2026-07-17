from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urlparse

from freeapis.constants import (
    FREE_TYPES,
    OUTPUT_TYPE_ORDER,
    PROVIDER_ORDER,
    PROVIDER_SOURCES,
    PROVIDER_STATUSES,
    SCHEMA_VERSION,
)
from freeapis.models import ModelRecord, ProviderResult, ValidationError

MODEL_FIELDS = (
    "provider",
    "model_id",
    "name",
    "output_types",
    "free_type",
    "model_url",
    "api_key_url",
    "docs_url",
    "source_url",
    "last_updated",
)
PROVIDER_FIELDS = ("status", "source_url", "last_successful_update")


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_model(record: dict[str, Any]) -> None:
    errors: list[str] = []
    if tuple(record) != MODEL_FIELDS:
        errors.append(f"fields must be exactly {MODEL_FIELDS}")
    provider = record.get("provider")
    if provider not in PROVIDER_ORDER:
        errors.append(f"invalid provider: {provider!r}")
    model_id = record.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        errors.append("model_id must be a non-empty string")
    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name must be a non-empty string")
    outputs = record.get("output_types")
    if not isinstance(outputs, list) or not outputs:
        errors.append("output_types must be a non-empty list")
    elif (
        any(item not in OUTPUT_TYPE_ORDER for item in outputs)
        or len(outputs) != len(set(outputs))
        or outputs != sorted(outputs, key=OUTPUT_TYPE_ORDER.index)
    ):
        errors.append("output_types contains invalid, duplicate, or unsorted values")
    if record.get("free_type") not in FREE_TYPES:
        errors.append(f"invalid free_type: {record.get('free_type')!r}")
    for field in ("model_url", "api_key_url", "docs_url", "source_url"):
        if not _valid_url(record.get(field)):
            errors.append(f"{field} must be an absolute HTTPS URL")
    if not _valid_date(record.get("last_updated")):
        errors.append("last_updated must be an ISO 8601 date")
    if errors:
        identity = f"{provider}/{model_id}"
        raise ValidationError(f"invalid model {identity}: " + "; ".join(errors))


def validate_provider_result(result: ProviderResult) -> None:
    if result.provider not in PROVIDER_ORDER:
        raise ValidationError(f"unknown provider result: {result.provider!r}")
    if result.source_url != PROVIDER_SOURCES[result.provider]:
        raise ValidationError(f"unexpected source URL for {result.provider}")
    if not result.models:
        raise ValidationError(f"{result.provider} returned no publishable models")
    ids = [model.model_id for model in result.models]
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{result.provider} returned duplicate model IDs")
    for model in result.models:
        validate_model(model.to_dict())
        if model.provider != result.provider:
            raise ValidationError(
                f"result for {result.provider} contains model for {model.provider}"
            )


def validate_document(document: dict[str, Any]) -> None:
    if tuple(document) != ("schema_version", "generated_at", "providers", "models"):
        raise ValidationError("top-level fields or field order are invalid")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValidationError(f"schema_version must be {SCHEMA_VERSION}")
    if not _valid_timestamp(document.get("generated_at")):
        raise ValidationError("generated_at must be an ISO 8601 UTC timestamp ending in Z")

    providers = document.get("providers")
    if not isinstance(providers, dict) or tuple(providers) != PROVIDER_ORDER:
        raise ValidationError("providers must contain all providers in stable order")
    for provider, metadata in providers.items():
        if not isinstance(metadata, dict) or tuple(metadata) != PROVIDER_FIELDS:
            raise ValidationError(f"invalid metadata fields for {provider}")
        if metadata.get("status") not in PROVIDER_STATUSES:
            raise ValidationError(f"invalid status for {provider}")
        if metadata.get("source_url") != PROVIDER_SOURCES[provider]:
            raise ValidationError(f"invalid source_url for {provider}")
        successful = metadata.get("last_successful_update")
        if successful is not None and not _valid_date(successful):
            raise ValidationError(f"invalid last_successful_update for {provider}")

    models = document.get("models")
    if not isinstance(models, list):
        raise ValidationError("models must be a list")
    identities: list[tuple[int, str]] = []
    seen: set[tuple[str, str]] = set()
    for record in models:
        if not isinstance(record, dict):
            raise ValidationError("each model must be an object")
        validate_model(record)
        identity = (record["provider"], record["model_id"])
        if identity in seen:
            raise ValidationError(f"duplicate model: {identity[0]}/{identity[1]}")
        seen.add(identity)
        identities.append((PROVIDER_ORDER.index(identity[0]), identity[1]))
    if identities != sorted(identities):
        raise ValidationError("models are not sorted by provider and model_id")
