from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

from freeapis.adapters.base import ProviderAdapter
from freeapis.constants import OUTPUT_TYPE_ORDER, PROVIDER_SOURCES
from freeapis.models import FetchError, ModelRecord, ProviderResult

LOGGER = logging.getLogger(__name__)
EXCLUDED_TERMS = (
    "embedding",
    "rerank",
    "moderation",
    "classifier",
    "classification",
    "content-safety",
    "content safety",
    "prompt-guard",
    "prompt guard",
    "safeguard",
    "speech-to-text",
    "speech to text",
    "transcription",
    "whisper",
)


class OpenRouterAdapter(ProviderAdapter):
    provider = "openrouter"
    source_url = PROVIDER_SOURCES[provider]
    free_type = "free_variant"

    def fetch(self) -> ProviderResult:
        payload = self.http.get_json(self.source_url)
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise FetchError("OpenRouter response is missing the data array")

        models: list[ModelRecord] = []
        for item in payload["data"]:
            model = self._parse_model(item)
            if model is not None:
                models.append(model)
        return self.result(models)

    def _parse_model(self, item: object) -> ModelRecord | None:
        if not isinstance(item, dict):
            return None
        model_id = item.get("id")
        if not isinstance(model_id, str) or not model_id.endswith(":free"):
            return None
        if model_id == "openrouter/free":
            return None

        name = item.get("name")
        description = item.get("description", "")
        searchable = f"{model_id} {name} {description}".lower()
        if any(term in searchable for term in EXCLUDED_TERMS):
            LOGGER.info("OpenRouter: excluded non-generative model %s", model_id)
            return None

        architecture = item.get("architecture")
        output_modalities = (
            architecture.get("output_modalities")
            if isinstance(architecture, dict)
            else None
        )
        if not isinstance(output_modalities, list):
            LOGGER.warning("OpenRouter: cannot confirm output type for %s", model_id)
            return None
        outputs = tuple(
            output
            for output in OUTPUT_TYPE_ORDER
            if output in {str(value).lower() for value in output_modalities}
        )
        if not outputs:
            LOGGER.info("OpenRouter: excluded non-generative model %s", model_id)
            return None
        if not self._has_zero_core_prices(item.get("pricing")):
            LOGGER.warning("OpenRouter: free ID has inconsistent pricing: %s", model_id)
            return None
        if not isinstance(name, str) or not name.strip():
            LOGGER.warning("OpenRouter: model has no official name: %s", model_id)
            return None

        encoded_id = quote(model_id, safe="/:")
        return ModelRecord(
            provider=self.provider,
            model_id=model_id,
            name=name.strip(),
            output_types=outputs,
            free_type=self.free_type,
            model_url=f"https://openrouter.ai/{encoded_id}",
            api_key_url="https://openrouter.ai/settings/keys",
            docs_url="https://openrouter.ai/docs/quickstart",
            source_url=self.source_url,
            last_updated=self.confirmed_on.isoformat(),
        )

    @staticmethod
    def _has_zero_core_prices(pricing: object) -> bool:
        if not isinstance(pricing, dict):
            return False
        for field in ("prompt", "completion"):
            try:
                if Decimal(str(pricing[field])) != 0:
                    return False
            except (KeyError, InvalidOperation, ValueError):
                return False
        return True
