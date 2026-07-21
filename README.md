# FreeAPIs

[简体中文](README.zh-CN.md)

FreeAPIs is a credential-free, automatically updated directory of generative
models that can be used for free through official provider APIs. It currently
covers OpenRouter, Groq, and the Gemini Developer API.

The project publishes navigation data only. It is not a proxy, gateway, quota
tracker, or configuration generator, and it never asks users or CI to provide
provider API keys. Free availability and limits can change; always confirm the
current provider terms before relying on a model.

## Providers

<!-- BEGIN GENERATED MODELS -->
| Provider | Status | Models | Outputs | Free type | Last update | Full list |
|---|---|---:|---|---|---|---|
| [OpenRouter](<https://openrouter.ai/api/v1/models>) | <code>fresh</code> | 12 | <code>text</code> | <code>free_variant</code> | 2026-07-21 | [View models](<providers/openrouter/README.md>) |
| [Groq](<https://console.groq.com/docs/rate-limits>) | <code>fresh</code> | 7 | <code>text</code>, <code>audio</code> | <code>free_plan</code> | 2026-07-21 | [View models](<providers/groq/README.md>) |
| [Gemini](<https://ai.google.dev/gemini-api/docs/pricing>) | <code>fresh</code> | 15 | <code>text</code>, <code>audio</code> | <code>free_tier</code> | 2026-07-21 | [View models](<providers/gemini/README.md>) |
<!-- END GENERATED MODELS -->

## Selection rules

- **OpenRouter:** concrete model IDs ending in `:free`, with zero core prices.
  The `openrouter/free` router and non-generative models are excluded.
- **Groq:** models in the official Free Plan Limits table whose public model
  detail page confirms a generative text, image, audio, or video output.
- **Gemini:** models whose Standard pricing table marks both core input and
  output as `Free of charge` in the Free Tier column.

Embedding, reranking, safety/classification, and speech-recognition or
transcription-only models are excluded. If output type cannot be confirmed, a
model is logged and omitted.

`free_type` is one of `free_variant`, `free_plan`, or `free_tier`.
`output_types` is limited to `text`, `image`, `audio`, and `video`. The project
does not maintain provider-specific quota amounts.

## Usage

Python 3.12 or newer is required.

```console
python -m pip install -e .
python -m freeapis update
python -m freeapis update --provider groq
python -m freeapis render
python -m freeapis check
```

`update` fetches public official sources, merges each provider independently,
validates `data/models.json`, and rebuilds the README navigation and provider
pages. A failed provider keeps
its previous records and becomes `stale`; successful providers are still
updated. The command exits non-zero after writing valid partial results so CI
can alert maintainers.

## Data contract

`data/models.json` contains `schema_version`, `generated_at`, `providers`, and
`models`. Every model record has exactly these fields:

```text
provider, model_id, name, output_types, free_type, model_url, api_key_url,
docs_url, source_url, last_updated
```

`last_updated` is the last date on which the official source confirmed the
model as free. Git history provides change tracking; no snapshots are stored.

## Development

```console
python -m pip install -e ".[test]"
pytest
```

Unit tests use reduced official-page fixtures and do not access the network.

## License

[MIT](LICENSE)
