from __future__ import annotations

from freeapis.pipeline import empty_document
from freeapis.render import check_readmes, render_readmes
from tests.test_pipeline import model


def test_bilingual_readmes_are_consistent_escaped_and_idempotent(tmp_path):
    english = tmp_path / "README.md"
    chinese = tmp_path / "README.zh-CN.md"
    seed = "# Test\n\n<!-- BEGIN GENERATED MODELS -->\nold\n<!-- END GENERATED MODELS -->\n"
    english.write_text(seed, encoding="utf-8")
    chinese.write_text(seed, encoding="utf-8")
    provider_files = []
    for provider in ("openrouter", "groq", "gemini"):
        directory = tmp_path / "providers" / provider
        directory.mkdir(parents=True)
        for name in ("README.md", "README.zh-CN.md"):
            path = directory / name
            path.write_text(seed, encoding="utf-8")
            provider_files.append(path)

    document = empty_document()
    record = model("groq", "example/model", "2026-07-17").to_dict()
    record["name"] = "Pipe | Name\\Line"
    document["models"] = [record]
    paths = (english, chinese)
    all_files = [english, chinese, *provider_files]

    render_readmes(document, paths)
    first = [path.read_bytes() for path in all_files]
    render_readmes(document, paths)
    second = [path.read_bytes() for path in all_files]

    assert first == second
    assert check_readmes(document, paths) == []
    root_english = english.read_text(encoding="utf-8")
    root_chinese = chinese.read_text(encoding="utf-8")
    assert "<code>example/model</code>" not in root_english
    assert "<code>example/model</code>" not in root_chinese
    assert "providers/groq/README.md" in root_english
    assert "providers/groq/README.zh-CN.md" in root_chinese

    groq_english = (tmp_path / "providers/groq/README.md").read_text(encoding="utf-8")
    groq_chinese = (tmp_path / "providers/groq/README.zh-CN.md").read_text(
        encoding="utf-8"
    )
    for content in (groq_english, groq_chinese):
        assert content.count("<code>example/model</code>") == 1
        assert "Pipe \\| Name\\\\Line" in content
    assert "may be stale" in groq_english
    assert "可能已经过期" in groq_chinese
    assert "example/model" not in (
        tmp_path / "providers/openrouter/README.md"
    ).read_text(encoding="utf-8")
