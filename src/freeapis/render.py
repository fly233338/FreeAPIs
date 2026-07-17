from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from freeapis.constants import OUTPUT_TYPE_ORDER, PROVIDER_LABELS, PROVIDER_ORDER
from freeapis.models import ValidationError

START_MARKER = "<!-- BEGIN GENERATED MODELS -->"
END_MARKER = "<!-- END GENERATED MODELS -->"


def _escape_cell(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("|", "\\|")
    text = " ".join(text.splitlines())
    return html.escape(text, quote=False)


def _code(value: object) -> str:
    return f"<code>{html.escape(str(value), quote=False)}</code>"


def _provider_readme_paths(
    readme_paths: tuple[Path, Path],
) -> dict[str, tuple[Path, Path]]:
    root = readme_paths[0].parent
    return {
        provider: (
            root / "providers" / provider / "README.md",
            root / "providers" / provider / "README.zh-CN.md",
        )
        for provider in PROVIDER_ORDER
    }


def render_summary_region(document: dict[str, Any], *, language: str) -> str:
    chinese = language == "zh-CN"
    lines = (
        [
            "| 平台 | 状态 | 模型数 | 输出类型 | 免费类型 | 最近更新 | 完整列表 |",
            "|---|---|---:|---|---|---|---|",
        ]
        if chinese
        else [
            "| Provider | Status | Models | Outputs | Free type | Last update | Full list |",
            "|---|---|---:|---|---|---|---|",
        ]
    )
    models = document["models"]
    for provider in PROVIDER_ORDER:
        metadata = document["providers"][provider]
        provider_models = [model for model in models if model["provider"] == provider]
        output_values = {
            output for model in provider_models for output in model["output_types"]
        }
        outputs = ", ".join(
            _code(output) for output in OUTPUT_TYPE_ORDER if output in output_values
        ) or "—"
        free_types = ", ".join(
            _code(value) for value in sorted({model["free_type"] for model in provider_models})
        ) or "—"
        status = _code(metadata["status"])
        if metadata["status"] == "stale":
            status += " ⚠️"
        suffix = ".zh-CN.md" if chinese else ".md"
        directory_link = f"providers/{provider}/README{suffix}"
        browse = "[查看模型]" if chinese else "[View models]"
        label = PROVIDER_LABELS[provider]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"[{label}](<{metadata['source_url']}>)",
                    status,
                    str(len(provider_models)),
                    outputs,
                    free_types,
                    metadata["last_successful_update"] or ("从未" if chinese else "never"),
                    f"{browse}(<{directory_link}>)",
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_provider_region(
    document: dict[str, Any], *, provider: str, language: str
) -> str:
    chinese = language == "zh-CN"
    metadata = document["providers"][provider]
    provider_models = [
        model for model in document["models"] if model["provider"] == provider
    ]
    source_label = "官方来源" if chinese else "Official source"
    status_label = "状态" if chinese else "Status"
    last_label = "最近成功更新" if chinese else "Last successful update"
    last_success = metadata["last_successful_update"] or ("从未" if chinese else "never")
    lines = [
        f"{source_label}：[链接](<{metadata['source_url']}>) · "
        f"{status_label}：{_code(metadata['status'])} · {last_label}：{last_success}"
        if chinese
        else f"{source_label}: [link](<{metadata['source_url']}>) · "
        f"{status_label}: {_code(metadata['status'])} · {last_label}: {last_success}",
        "",
    ]
    if metadata["status"] == "stale":
        lines.extend(
            [
                "> ⚠️ 本平台最近一次抓取失败，所列数据可能已经过期。"
                if chinese
                else "> ⚠️ The latest fetch for this provider failed; listed data may be stale.",
                "",
            ]
        )
    lines.extend(
        [
            "| 模型 ID | 名称 | 输出 | 免费类型 | 官方链接 | 最后确认 |",
            "|---|---|---|---|---|---|",
        ]
        if chinese
        else [
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
    return "\n".join(lines)


def render_content(original: str, region: str) -> str:
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        raise ValidationError("README is missing valid generated model markers")
    before = original[: start + len(START_MARKER)]
    after = original[end:]
    return f"{before}\n{region}\n{after}"


def _artifacts(
    document: dict[str, Any], readme_paths: tuple[Path, Path]
) -> list[tuple[Path, str]]:
    artifacts = [
        (readme_paths[0], render_summary_region(document, language="en")),
        (readme_paths[1], render_summary_region(document, language="zh-CN")),
    ]
    for provider, paths in _provider_readme_paths(readme_paths).items():
        artifacts.extend(
            [
                (
                    paths[0],
                    render_provider_region(document, provider=provider, language="en"),
                ),
                (
                    paths[1],
                    render_provider_region(
                        document, provider=provider, language="zh-CN"
                    ),
                ),
            ]
        )
    return artifacts


def render_readmes(document: dict[str, Any], readme_paths: tuple[Path, Path]) -> None:
    for path, region in _artifacts(document, readme_paths):
        original = path.read_text(encoding="utf-8")
        rendered = render_content(original, region)
        path.write_text(rendered, encoding="utf-8", newline="\n")


def check_readmes(
    document: dict[str, Any], readme_paths: tuple[Path, Path]
) -> list[str]:
    errors: list[str] = []
    for path, region in _artifacts(document, readme_paths):
        original = path.read_text(encoding="utf-8")
        if render_content(original, region) != original:
            errors.append(f"{path.relative_to(readme_paths[0].parent)} is not synchronized")
    return errors
