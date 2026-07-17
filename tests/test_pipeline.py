from __future__ import annotations

from datetime import date

from freeapis.constants import PROVIDER_SOURCES
from freeapis.models import ModelRecord, ProviderResult
from freeapis.pipeline import empty_document, merge_results


def model(provider: str, model_id: str, updated: str) -> ModelRecord:
    free_type = {
        "openrouter": "free_variant",
        "groq": "free_plan",
        "gemini": "free_tier",
    }[provider]
    return ModelRecord(
        provider=provider,
        model_id=model_id,
        name=model_id,
        output_types=("text",),
        free_type=free_type,
        model_url=f"https://example.com/models/{model_id}",
        api_key_url="https://example.com/keys",
        docs_url="https://example.com/docs",
        source_url=PROVIDER_SOURCES[provider],
        last_updated=updated,
    )


class ResultAdapter:
    def __init__(self, result: ProviderResult) -> None:
        self.result = result

    def fetch(self) -> ProviderResult:
        return self.result


class FailingAdapter:
    def fetch(self) -> ProviderResult:
        raise RuntimeError("fixture failure")


def existing_document():
    document = empty_document()
    document["providers"]["openrouter"] = {
        "status": "fresh",
        "source_url": PROVIDER_SOURCES["openrouter"],
        "last_successful_update": "2026-07-15",
    }
    document["providers"]["groq"] = {
        "status": "fresh",
        "source_url": PROVIDER_SOURCES["groq"],
        "last_successful_update": "2026-07-15",
    }
    document["models"] = [
        model("openrouter", "keep:free", "2026-07-15").to_dict(),
        model("groq", "remove-old", "2026-07-15").to_dict(),
    ]
    return document


def test_success_replaces_complete_provider_snapshot_and_removes_old_models():
    result = ProviderResult(
        provider="groq",
        source_url=PROVIDER_SOURCES["groq"],
        models=(model("groq", "new-model", "2026-07-17"),),
    )
    document, failed = merge_results(
        existing_document(),
        {"groq": ResultAdapter(result)},
        ("groq",),
        confirmed_on=date(2026, 7, 17),
    )

    assert failed == []
    assert [(item["provider"], item["model_id"]) for item in document["models"]] == [
        ("openrouter", "keep:free"),
        ("groq", "new-model"),
    ]
    assert document["providers"]["groq"] == {
        "status": "fresh",
        "source_url": PROVIDER_SOURCES["groq"],
        "last_successful_update": "2026-07-17",
    }


def test_failure_retains_old_models_dates_and_marks_provider_stale():
    document, failed = merge_results(
        existing_document(),
        {"groq": FailingAdapter()},
        ("groq",),
        confirmed_on=date(2026, 7, 17),
    )

    assert failed == ["groq"]
    old = next(item for item in document["models"] if item["provider"] == "groq")
    assert old["model_id"] == "remove-old"
    assert old["last_updated"] == "2026-07-15"
    assert document["providers"]["groq"] == {
        "status": "stale",
        "source_url": PROVIDER_SOURCES["groq"],
        "last_successful_update": "2026-07-15",
    }
