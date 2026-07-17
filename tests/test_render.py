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

    document = empty_document()
    record = model("groq", "example/model", "2026-07-17").to_dict()
    record["name"] = "Pipe | Name\\Line"
    document["models"] = [record]
    paths = (english, chinese)

    render_readmes(document, paths)
    first = (english.read_bytes(), chinese.read_bytes())
    render_readmes(document, paths)
    second = (english.read_bytes(), chinese.read_bytes())

    assert first == second
    assert check_readmes(document, paths) == []
    for content in (english.read_text(encoding="utf-8"), chinese.read_text(encoding="utf-8")):
        assert content.count("<code>example/model</code>") == 1
        assert "Pipe \\| Name\\\\Line" in content
    assert "may be stale" in english.read_text(encoding="utf-8")
    assert "可能已经过期" in chinese.read_text(encoding="utf-8")
