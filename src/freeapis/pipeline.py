from __future__ import annotations

import copy
import json
import logging
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from freeapis.adapters import GeminiAdapter, GroqAdapter, OpenRouterAdapter
from freeapis.adapters.base import ProviderAdapter
from freeapis.constants import (
    DATA_PATH,
    PROVIDER_ORDER,
    PROVIDER_SOURCES,
    README_PATHS,
    SCHEMA_VERSION,
)
from freeapis.http import HttpClient
from freeapis.render import check_readmes, render_readmes
from freeapis.validation import validate_document, validate_provider_result

LOGGER = logging.getLogger(__name__)


def utc_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def empty_document() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_timestamp(),
        "providers": {
            provider: {
                "status": "stale",
                "source_url": PROVIDER_SOURCES[provider],
                "last_successful_update": None,
            }
            for provider in PROVIDER_ORDER
        },
        "models": [],
    }


def load_document(path: Path = DATA_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    validate_document(document)
    return document


def write_document(document: dict[str, Any], path: Path = DATA_PATH) -> None:
    validate_document(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def default_adapters(http: HttpClient, confirmed_on: date) -> dict[str, ProviderAdapter]:
    return {
        "openrouter": OpenRouterAdapter(http, confirmed_on=confirmed_on),
        "groq": GroqAdapter(http, confirmed_on=confirmed_on),
        "gemini": GeminiAdapter(http, confirmed_on=confirmed_on),
    }


def merge_results(
    existing: dict[str, Any],
    adapters: dict[str, ProviderAdapter],
    selected: tuple[str, ...],
    *,
    confirmed_on: date,
) -> tuple[dict[str, Any], list[str]]:
    document = copy.deepcopy(existing)
    failed: list[str] = []
    for provider in selected:
        adapter = adapters[provider]
        try:
            result = adapter.fetch()
            validate_provider_result(result)
        except Exception as exc:  # isolate provider failures by design
            LOGGER.error("%s update failed: %s", provider, exc)
            document["providers"][provider]["status"] = "stale"
            failed.append(provider)
            continue

        retained = [model for model in document["models"] if model["provider"] != provider]
        retained.extend(model.to_dict() for model in result.models)
        document["models"] = retained
        document["providers"][provider] = {
            "status": "fresh",
            "source_url": result.source_url,
            "last_successful_update": confirmed_on.isoformat(),
        }

    document["schema_version"] = SCHEMA_VERSION
    document["generated_at"] = utc_timestamp()
    document["models"] = sorted(
        document["models"],
        key=lambda model: (PROVIDER_ORDER.index(model["provider"]), model["model_id"]),
    )
    validate_document(document)
    return document, failed


def update_repository(
    *,
    provider: str | None = None,
    data_path: Path = DATA_PATH,
    readme_paths: tuple[Path, Path] = README_PATHS,
    adapters: dict[str, ProviderAdapter] | None = None,
    confirmed_on: date | None = None,
) -> list[str]:
    today = confirmed_on or date.today()
    existing = load_document(data_path) if data_path.exists() else empty_document()
    selected = (provider,) if provider else PROVIDER_ORDER

    if adapters is None:
        with HttpClient() as http:
            document, failed = merge_results(
                existing,
                default_adapters(http, today),
                selected,
                confirmed_on=today,
            )
    else:
        document, failed = merge_results(
            existing, adapters, selected, confirmed_on=today
        )
    write_document(document, data_path)
    render_readmes(document, readme_paths)
    return failed


def check_repository(
    *,
    data_path: Path = DATA_PATH,
    readme_paths: tuple[Path, Path] = README_PATHS,
) -> list[str]:
    try:
        document = load_document(data_path)
    except Exception as exc:
        return [f"{data_path}: {exc}"]
    try:
        return check_readmes(document, readme_paths)
    except Exception as exc:
        return [f"README validation failed: {exc}"]
