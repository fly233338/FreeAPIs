from __future__ import annotations

import logging
import re
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag

from freeapis.adapters.base import ProviderAdapter
from freeapis.constants import OUTPUT_TYPE_ORDER, PROVIDER_SOURCES
from freeapis.models import FetchError, ModelRecord, ProviderResult

LOGGER = logging.getLogger(__name__)
MODEL_ID_PATTERN = re.compile(
    r"\b(?:gemini|imagen|veo|lyria)-[a-z0-9][a-z0-9._-]*\b", re.IGNORECASE
)
EXCLUDED_TERMS = (
    "embedding",
    "rerank",
    "moderation",
    "classifier",
    "classification",
    "safety",
    "speech to text",
    "speech-to-text",
    "transcription",
)


class GeminiAdapter(ProviderAdapter):
    provider = "gemini"
    source_url = PROVIDER_SOURCES[provider]
    free_type = "free_tier"

    def fetch(self) -> ProviderResult:
        html = self.http.get_text(self.source_url)
        soup = BeautifulSoup(html, "html.parser")
        sections_seen = 0
        core_tables_seen = 0
        models: list[ModelRecord] = []
        for heading in soup.find_all("h2"):
            elements = self._section_elements(heading)
            model_ids = self._leading_model_ids(elements)
            if not model_ids:
                continue
            sections_seen += 1
            table = self._standard_table(elements)
            if table is None:
                LOGGER.info(
                    "Gemini: no Standard pricing table for %s", ", ".join(model_ids)
                )
                continue
            eligibility = self._core_usage_is_free(table)
            if eligibility is None:
                LOGGER.info(
                    "Gemini: no core input/output rows for %s", ", ".join(model_ids)
                )
                continue
            core_tables_seen += 1
            if not eligibility:
                continue

            title = heading.get_text(" ", strip=True)
            description = self._leading_description(elements)
            classification_text = f"{title} {description} {' '.join(model_ids)}".lower()
            if any(term in classification_text for term in EXCLUDED_TERMS):
                LOGGER.info(
                    "Gemini: excluded non-generative model(s) %s",
                    ", ".join(model_ids),
                )
                continue
            output_types = self._output_types(title, description, table)
            if not output_types:
                LOGGER.warning(
                    "Gemini: cannot confirm output type for %s", ", ".join(model_ids)
                )
                continue

            fragment = heading.get("id") or model_ids[0]
            model_url = f"{self.source_url}#{quote(str(fragment), safe='-._')}"
            for model_id in model_ids:
                models.append(
                    ModelRecord(
                        provider=self.provider,
                        model_id=model_id,
                        name=title,
                        output_types=output_types,
                        free_type=self.free_type,
                        model_url=model_url,
                        api_key_url="https://aistudio.google.com/app/apikey",
                        docs_url="https://ai.google.dev/gemini-api/docs/quickstart",
                        source_url=self.source_url,
                        last_updated=self.confirmed_on.isoformat(),
                    )
                )
        if sections_seen == 0:
            raise FetchError("Gemini pricing page has no recognizable model sections")
        if core_tables_seen == 0:
            raise FetchError("Gemini pricing page has no recognizable core pricing tables")
        return self.result(models)

    @staticmethod
    def _section_elements(heading: Tag) -> list[Tag]:
        elements: list[Tag] = []
        for element in heading.next_elements:
            if element is heading:
                continue
            if isinstance(element, Tag) and element.name == "h2":
                break
            if isinstance(element, Tag) and element.name in {"code", "p", "h3", "table"}:
                elements.append(element)
        return elements

    @staticmethod
    def _leading_model_ids(elements: list[Tag]) -> list[str]:
        code_text: list[str] = []
        for element in elements:
            if element.name in {"h3", "table"}:
                break
            if element.name == "code":
                code_text.append(element.get_text(" ", strip=True))
        ids: list[str] = []
        for text in code_text:
            for match in MODEL_ID_PATTERN.findall(text):
                model_id = match.lower()
                if model_id not in ids:
                    ids.append(model_id)
        return ids

    @staticmethod
    def _leading_description(elements: list[Tag]) -> str:
        text: list[str] = []
        for element in elements:
            if element.name in {"h3", "table"}:
                break
            if element.name == "p":
                text.append(element.get_text(" ", strip=True))
        return " ".join(text)

    @staticmethod
    def _standard_table(elements: list[Tag]) -> Tag | None:
        standard_index: int | None = None
        for index, element in enumerate(elements):
            if element.name == "h3" and element.get_text(" ", strip=True).lower().startswith(
                "standard"
            ):
                standard_index = index
                break
        start = standard_index + 1 if standard_index is not None else 0
        for element in elements[start:]:
            if element.name == "h3" and standard_index is None:
                break
            if element.name == "table":
                return element
            nested = element.find("table")
            if nested is not None:
                return nested
        return None

    @staticmethod
    def _table_rows(table: Tag) -> tuple[int, list[list[str]]]:
        header = table.find("tr")
        if header is None:
            raise FetchError("Gemini Standard pricing table has no header")
        headings = [cell.get_text(" ", strip=True) for cell in header.find_all(["th", "td"])]
        free_index = next(
            (index for index, value in enumerate(headings) if value.lower().startswith("free tier")),
            -1,
        )
        if free_index < 0:
            raise FetchError("Gemini Standard pricing table has no Free Tier column")
        rows = [
            [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            for row in table.find_all("tr")[1:]
        ]
        return free_index, [row for row in rows if row]

    @classmethod
    def _core_usage_is_free(cls, table: Tag) -> bool | None:
        free_index, rows = cls._table_rows(table)
        input_rows = [row for row in rows if "input" in row[0].lower() and "price" in row[0].lower()]
        output_rows = [row for row in rows if "output" in row[0].lower() and "price" in row[0].lower()]
        if not input_rows or not output_rows:
            return None
        core_rows = input_rows + output_rows
        return all(
            len(row) > free_index and "free of charge" in row[free_index].lower()
            for row in core_rows
        )

    @classmethod
    def _output_types(cls, title: str, description: str, table: Tag) -> tuple[str, ...]:
        _, rows = cls._table_rows(table)
        output_text = " ".join(
            " ".join(row) for row in rows if "output" in row[0].lower() and "price" in row[0].lower()
        ).lower()
        context = f"{title} {description}".lower()
        outputs: set[str] = set()
        if "audio" in output_text:
            outputs.add("audio")
        if "image" in output_text:
            outputs.add("image")
        if "video" in output_text:
            outputs.add("video")
        if "text" in output_text or "thinking token" in output_text:
            outputs.add("text")

        if not outputs:
            if any(term in context for term in ("text-to-speech", "tts", "audio-to-audio", "speech to speech")):
                outputs.add("audio")
            elif "image generation" in context or "image model" in context:
                outputs.add("image")
            elif "video generation" in context or "video model" in context:
                outputs.add("video")
            else:
                outputs.add("text")
        return tuple(output for output in OUTPUT_TYPE_ORDER if output in outputs)
