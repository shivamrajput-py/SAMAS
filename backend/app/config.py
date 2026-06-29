"""
Centralized configuration for SAMAS.

All settings are loaded from environment variables (.env file).
This module is the single source of truth for configuration â€”
no other file should read env vars directly.

Why a separate config file?
- Single place to change settings (don't hunt across files)
- Easy to swap between dev/staging/prod environments
- Makes testing easier (mock this module, not os.environ everywhere)
"""

import os
from dotenv import load_dotenv

# Load .env file into os.environ. This is a no-op if the file doesn't exist,
# which is fine in production where env vars are set differently (Docker, etc.)
load_dotenv(override=True)


# â”€â”€â”€ LLM Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# OpenRouter acts as a unified gateway to many LLM providers.
# By using their OpenAI-compatible API, we can swap models without
# changing any code â€” just update the .env file.

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nex-agi/nex-n2-pro:free")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


# â”€â”€â”€ External API Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# GitHub token is optional but recommended. Without it, you get 60 API
# requests per hour. With it, 5,000. For development, 60 is usually enough.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")

# ─── Pinecone Vector DB Configuration ────────────────────
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "samas-index")


# â”€â”€â”€ Jina Reader Configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Jina Reader is a free service that converts any URL to clean markdown.
# It's how we "browse" portfolio sites and LinkedIn profiles.
# No API key needed â€” just prepend the URL with their endpoint.

JINA_READER_BASE_URL = "https://r.jina.ai"
JINA_READER_TIMEOUT = 30  # seconds â€” some pages are slow


# â”€â”€â”€ Profile Builder Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Maximum characters of scraped content to send to the LLM per URL.
# Free models have limited context windows, so we truncate.
MAX_SCRAPED_CONTENT_LENGTH = 4000

# Maximum number of GitHub repos to include in the LLM context.
# We take the most recently updated ones.
MAX_GITHUB_REPOS = 15
