from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from freeapis.constants import PROVIDER_LABELS, PROVIDER_ORDER
from freeapis.models import ValidationError

START_MARKER = "<!-- BEGIN GENERATED MODELS -->"
END_MARKER = "<!-- END GENERATED MODELS -->"


def _escape_cell(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("|", "\\|")
    text = " ".join(text.splitlines())
    return html.escape(text, quote=False)


def _code(value: object) -> str:
    return f"<code>{html.escape(str(value), quote=False)}</code>"


def render_models_region(document: dict[str, Any], *, language: str) -> str:
    chinese = language == "zh-CN"
    lines: list[str] = []
    models = document["models"]
    for provider in PROVIDER_ORDER:
        metadata = document["providers"][provider]
        provider_models = [model for model in models if model["provider"] == provider]
        label = PROVIDER_LABELS[provider]
        source_label = "官方来源" if chinese else "Official source"
        last_label = "最近成功更新" if chinese else "Last successful update"
        last_success = metadata["last_successful_update"] or ("从未" if chinese else "never")
        lines.extend(
            [
                f"### {label}",
                "",
                f"{source_label}：[链接](<{metadata['source_url']}>) · "
                f"{last_label}：{last_success}"
                if chinese
                else f"{source_label}: [link](<{metadata['source_url']}>) · "
                f"{last_label}: {last_success}",
                "",
            ]
        )
        if metadata["status"] == "stale":
            lines.extend(
                [
                    "> ⚠️ 本平台最近一次抓取失败，所列数据可能已经过期。"
                    if chinese
                    else "> ⚠️ The latest fetch for this provider failed; listed data may be stale.",
                    "",
                ]
            )
        if chinese:
            lines.extend(
                [
                    "| 模型 ID | 名称 | 输出 | 免费类型 | 官方链接 | 最后确认 |",
                    "|---|---|---|---|---|---|",
                ]
            )
        else:
            lines.extend(
                [
                    "| Model ID | Name | Outputs | Free type | Official links | Last confirmed |",
                    "|---|---|---|---|---|---|",
                ]
            )
        if not provider_models:
            empty = "暂无可发布模型" if chinese else "No publishable models"
            lines.append(f"| — | {empty} | — | — | — | — |")
        for model in provider_models:
            outputs = ", ".join(_code(value) for value in model["output_types"])
            links = (
                f"[详情](<{model['model_url']}>) · [API Key](<{model['api_key_url']}>) · "
                f"[配置文档](<{model['docs_url']}>)"
                if chinese
                else f"[Details](<{model['model_url']}>) · [API key](<{model['api_key_url']}>) · "
                f"[Setup docs](<{model['docs_url']}>)"
            )
            lines.append(
                "| "
                + " | ".join(
                    [
                        _code(model["model_id"]),
                        _escape_cell(model["name"]),
                        outputs,
                        _code(model["free_type"]),
                        links,
                        model["last_updated"],
                    ]
                )
                + " |"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def render_content(original: str, document: dict[str, Any], *, language: str) -> str:
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        raise ValidationError("README is missing valid generated model markers")
    region = render_models_region(document, language=language)
    before = original[: start + len(START_MARKER)]
    after = original[end:]
    return f"{before}\n{region}\n{after}"


def render_readmes(
    document: dict[str, Any], readme_paths: tuple[Path, Path]
) -> None:
    for path, language in zip(readme_paths, ("en", "zh-CN"), strict=True):
        original = path.read_text(encoding="utf-8")
        rendered = render_content(original, document, language=language)
        path.write_text(rendered, encoding="utf-8", newline="\n")


def check_readmes(
    document: dict[str, Any], readme_paths: tuple[Path, Path]
) -> list[str]:
    errors: list[str] = []
    for path, language in zip(readme_paths, ("en", "zh-CN"), strict=True):
        original = path.read_text(encoding="utf-8")
        if render_content(original, document, language=language) != original:
            errors.append(f"{path.name} is not synchronized with models.json")
    return errors
