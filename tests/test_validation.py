from __future__ import annotations

import copy

import pytest

from freeapis.models import ValidationError
from freeapis.pipeline import empty_document
from freeapis.validation import validate_document
from tests.test_pipeline import model


def valid_document():
    document = empty_document()
    document["models"] = [
        model("openrouter", "a:free", "2026-07-17").to_dict(),
        model("groq", "b", "2026-07-17").to_dict(),
    ]
    return document


def test_valid_document_has_fixed_fields_enums_urls_dates_and_sorting():
    validate_document(valid_document())


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("free_type", "free", "free_type"),
        ("output_types", ["audio", "text"], "output_types"),
        ("model_url", "http://example.com/model", "HTTPS"),
        ("last_updated", "07/17/2026", "ISO 8601"),
    ],
)
def test_invalid_model_values_are_rejected(field, value, message):
    document = valid_document()
    document["models"][0][field] = value
    with pytest.raises(ValidationError, match=message):
        validate_document(document)


def test_extra_model_field_is_rejected():
    document = valid_document()
    document["models"][0]["quota"] = "unknown"
    with pytest.raises(ValidationError, match="fields"):
        validate_document(document)


def test_duplicate_and_unstable_order_are_rejected():
    duplicate = valid_document()
    duplicate["models"].append(copy.deepcopy(duplicate["models"][0]))
    with pytest.raises(ValidationError, match="duplicate"):
        validate_document(duplicate)

    unsorted = valid_document()
    unsorted["models"].reverse()
    with pytest.raises(ValidationError, match="sorted"):
        validate_document(unsorted)


def test_invalid_provider_metadata_is_rejected():
    document = valid_document()
    document["providers"]["groq"]["status"] = "failed"
    with pytest.raises(ValidationError, match="status"):
        validate_document(document)
