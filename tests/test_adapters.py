from __future__ import annotations

import copy
from datetime import date

import pytest

from freeapis.adapters.gemini import GeminiAdapter
from freeapis.adapters.groq import GroqAdapter
from freeapis.adapters.openrouter import OpenRouterAdapter
from freeapis.constants import PROVIDER_SOURCES
from freeapis.models import FetchError, ValidationError
from tests.conftest import FakeHttp

TODAY = date(2026, 7, 17)


def test_openrouter_filters_and_normalizes(fixture_json):
    adapter = OpenRouterAdapter(
        FakeHttp(json_payload=fixture_json("openrouter_models.json")),
        confirmed_on=TODAY,
    )
    result = adapter.fetch()

    assert [model.model_id for model in result.models] == [
        "example/multimodal:free",
        "example/text:free",
    ]
    assert result.models[0].output_types == ("image", "audio")
    assert {model.free_type for model in result.models} == {"free_variant"}
    assert {model.last_updated for model in result.models} == {"2026-07-17"}


def test_openrouter_rejects_duplicate_ids(fixture_json):
    payload = fixture_json("openrouter_models.json")
    payload["data"].append(copy.deepcopy(payload["data"][0]))
    with pytest.raises(ValidationError, match="duplicate"):
        OpenRouterAdapter(FakeHttp(json_payload=payload), confirmed_on=TODAY).fetch()


@pytest.mark.parametrize("payload", [{}, {"data": "changed"}])
def test_openrouter_detects_structure_change(payload):
    with pytest.raises(FetchError, match="data array"):
        OpenRouterAdapter(FakeHttp(json_payload=payload), confirmed_on=TODAY).fetch()


def test_groq_uses_only_free_table_and_public_details(fixture_text):
    source = PROVIDER_SOURCES["groq"]
    detail_files = {
        "example/text-model": "groq_model_text.html",
        "example/tts-model": "groq_model_tts.html",
        "example/whisper-model": "groq_model_transcription.html",
        "example/prompt-guard": "groq_model_safety.html",
    }
    texts = {source: fixture_text("groq_rate_limits.html")}
    texts.update(
        {
            GroqAdapter.detail_url(model_id): fixture_text(filename)
            for model_id, filename in detail_files.items()
        }
    )
    result = GroqAdapter(FakeHttp(texts=texts), confirmed_on=TODAY).fetch()

    assert [(model.model_id, model.output_types) for model in result.models] == [
        ("example/text-model", ("text",)),
        ("example/tts-model", ("audio",)),
    ]
    assert all(model.free_type == "free_plan" for model in result.models)
    assert "developer-only" not in " ".join(model.model_id for model in result.models)


@pytest.mark.parametrize(
    "html, message",
    [
        ("<html><body><p>changed</p></body></html>", "missing"),
        ("<button>Free Plan Limits</button><table><tr><th>MODEL ID</th></tr></table>", "empty"),
    ],
)
def test_groq_detects_missing_or_empty_table(html, message):
    with pytest.raises(FetchError, match=message):
        GroqAdapter.parse_free_plan_ids(html)


def test_groq_rejects_duplicate_ids(fixture_text):
    html = fixture_text("groq_rate_limits.html").replace(
        "</tbody>",
        "<tr><td>example/text-model</td><td>30</td><td>1K</td><td>6K</td></tr></tbody>",
        1,
    )
    source = PROVIDER_SOURCES["groq"]
    texts = {
        source: html,
        GroqAdapter.detail_url("example/text-model"): fixture_text("groq_model_text.html"),
        GroqAdapter.detail_url("example/tts-model"): fixture_text("groq_model_tts.html"),
        GroqAdapter.detail_url("example/whisper-model"): fixture_text("groq_model_transcription.html"),
        GroqAdapter.detail_url("example/prompt-guard"): fixture_text("groq_model_safety.html"),
    }
    with pytest.raises(ValidationError, match="duplicate"):
        GroqAdapter(FakeHttp(texts=texts), confirmed_on=TODAY).fetch()


def test_gemini_free_core_pricing_types_and_multiple_ids(fixture_text):
    source = PROVIDER_SOURCES["gemini"]
    result = GeminiAdapter(
        FakeHttp(texts={source: fixture_text("gemini_pricing.html")}),
        confirmed_on=TODAY,
    ).fetch()

    assert [(model.model_id, model.output_types) for model in result.models] == [
        ("gemini-free-text", ("text",)),
        ("gemini-speech-one", ("audio",)),
        ("gemini-speech-two", ("audio",)),
        ("imagen-free-generate-001", ("image",)),
    ]
    assert all(model.free_type == "free_tier" for model in result.models)
    assert all("gemini-paid" != model.model_id for model in result.models)
    assert all("embedding" not in model.model_id for model in result.models)


@pytest.mark.parametrize(
    "html, message",
    [
        ("<html><h2>Pricing changed</h2></html>", "model sections"),
        (
            "<html><h2>Gemini X</h2><p><code>gemini-x</code></p><p>No table</p></html>",
            "core pricing tables",
        ),
    ],
)
def test_gemini_detects_structure_change(html, message):
    source = PROVIDER_SOURCES["gemini"]
    with pytest.raises(FetchError, match=message):
        GeminiAdapter(FakeHttp(texts={source: html}), confirmed_on=TODAY).fetch()
