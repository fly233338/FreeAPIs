from __future__ import annotations

import logging
from urllib.parse import quote

from bs4 import BeautifulSoup

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
    "content safety",
    "content-safety",
    "prompt guard",
    "prompt-guard",
    "safeguard",
    "speech to text",
    "speech-to-text",
    "transcription",
    "whisper",
)


class GroqAdapter(ProviderAdapter):
    provider = "groq"
    source_url = PROVIDER_SOURCES[provider]
    free_type = "free_plan"

    def fetch(self) -> ProviderResult:
        rate_limits_html = self.http.get_text(self.source_url)
        model_ids = self.parse_free_plan_ids(rate_limits_html)
        models: list[ModelRecord] = []
        for model_id in model_ids:
            detail_url = self.detail_url(model_id)
            try:
                detail_html = self.http.get_text(detail_url)
            except FetchError as exc:
                LOGGER.warning(
                    "Groq: cannot confirm model type for %s; skipping: %s",
                    model_id,
                    exc,
                )
                continue
            model = self.parse_detail(model_id, detail_url, detail_html)
            if model is not None:
                models.append(model)
        return self.result(models)

    @staticmethod
    def detail_url(model_id: str) -> str:
        return "https://console.groq.com/docs/model/" + quote(model_id, safe="/")

    @staticmethod
    def parse_free_plan_ids(html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        label = soup.find(string=lambda value: value and value.strip() == "Free Plan Limits")
        if label is None:
            raise FetchError("Groq page is missing the Free Plan Limits section")
        header_table = label.find_parent("table") or label.find_next("table")
        if header_table is None:
            raise FetchError("Groq Free Plan Limits section has no table")
        header_row = next(
            (
                row
                for row in header_table.find_all("tr")
                if row.find_all(["th", "td"])
                and row.find_all(["th", "td"])[0]
                .get_text(" ", strip=True)
                .upper()
                == "MODEL ID"
            ),
            None,
        )
        if header_row is None:
            raise FetchError("Groq Free Plan Limits table headers changed")

        data_rows = [row for row in header_table.find_all("tr") if row.find("td")]
        if not data_rows:
            data_table = header_table.find_next("table")
            data_rows = data_table.find_all("tr") if data_table is not None else []
        model_ids: list[str] = []
        for row in data_rows:
            cells = row.find_all(["td", "th"])
            if cells:
                model_id = cells[0].get_text(" ", strip=True)
                if model_id and model_id.upper() != "MODEL ID":
                    model_ids.append(model_id)
        if not model_ids:
            raise FetchError("Groq Free Plan Limits table is empty")
        return model_ids

    def parse_detail(
        self, model_id: str, detail_url: str, html: str
    ) -> ModelRecord | None:
        soup = BeautifulSoup(html, "html.parser")
        strings = list(soup.stripped_strings)
        if model_id not in strings and model_id not in soup.get_text(" ", strip=True):
            LOGGER.warning("Groq: detail page does not identify %s", model_id)
            return None
        title_tag = soup.find("h1")
        title = title_tag.get_text(" ", strip=True) if title_tag else ""

        output_types: set[str] = set()
        output_index = next(
            (index for index, value in enumerate(strings) if value.strip().upper() == "OUTPUT"),
            None,
        )
        if output_index is not None:
            for value in strings[output_index + 1 : output_index + 8]:
                normalized = value.strip().lower()
                if normalized in OUTPUT_TYPE_ORDER:
                    output_types.add(normalized)
                if normalized in {"capabilities", "pricing", "limits", "input"}:
                    break

        capability_text = ""
        capability_index = next(
            (
                index
                for index, value in enumerate(strings)
                if value.strip().upper() == "CAPABILITIES"
            ),
            None,
        )
        if capability_index is not None:
            capability_text = strings[capability_index + 1] if len(strings) > capability_index + 1 else ""
        classification_text = f"{model_id} {title} {capability_text}".lower()
        if any(term in classification_text for term in EXCLUDED_TERMS):
            LOGGER.info("Groq: excluded non-generative model %s", model_id)
            return None
        if not output_types:
            LOGGER.warning("Groq: cannot confirm output type for %s", model_id)
            return None
        if not title:
            LOGGER.warning("Groq: detail page has no model name for %s", model_id)
            return None

        return ModelRecord(
            provider=self.provider,
            model_id=model_id,
            name=title,
            output_types=tuple(
                output for output in OUTPUT_TYPE_ORDER if output in output_types
            ),
            free_type=self.free_type,
            model_url=detail_url,
            api_key_url="https://console.groq.com/keys",
            docs_url="https://console.groq.com/docs/quickstart",
            source_url=self.source_url,
            last_updated=self.confirmed_on.isoformat(),
        )
