from pathlib import Path

SCHEMA_VERSION = "1.0"
PROVIDER_ORDER = ("openrouter", "groq", "gemini")
PROVIDER_LABELS = {
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "gemini": "Gemini",
}
PROVIDER_SOURCES = {
    "openrouter": "https://openrouter.ai/api/v1/models",
    "groq": "https://console.groq.com/docs/rate-limits",
    "gemini": "https://ai.google.dev/gemini-api/docs/pricing",
}
FREE_TYPES = ("free_variant", "free_plan", "free_tier")
OUTPUT_TYPE_ORDER = ("text", "image", "audio", "video")
PROVIDER_STATUSES = ("fresh", "stale")

ROOT = Path.cwd()
DATA_PATH = ROOT / "data" / "models.json"
README_PATHS = (ROOT / "README.md", ROOT / "README.zh-CN.md")
