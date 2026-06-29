"""
Shared LLM Client â€” Used by all agents in SAMAS.

This module centralizes LLM access so every agent uses the same:
- Connection setup (OpenRouter gateway)
- Fallback chain (if model A fails, try model B)
- JSON response parsing (handles markdown fences, truncated output, etc.)
- Retry logic with model rotation

WHY A SHARED MODULE?
    Without this, every agent would duplicate the LLM setup, fallback logic,
    and JSON parsing. That means fixing a bug in one place doesn't fix it
    everywhere. This module is the single source of truth for LLM calls.

PRODUCTION PATTERN: MODEL FALLBACK CHAIN
    Free/cheap LLM models go down regularly â€” 504 timeouts, rate limits,
    model deprecations. A production system never depends on one model.
    We try the primary model first, then automatically rotate through
    fallbacks until one succeeds.
"""

import json
import re
import asyncio
from typing import List, Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import BaseMessage

from app.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL


# â”€â”€â”€ Fallback chain â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# These are tried in order. When one fails, the next is used.
# Update these when models change on OpenRouter.

FALLBACK_MODELS = [
    OPENROUTER_MODEL,                  # Whatever you set in .env (first choice)
    "google/gemini-2.5-flash",         # Google Gemini 2.5 Flash
    "deepseek/deepseek-chat",          # DeepSeek Chat V3
]


def get_llm(model_name: str = None, custom_api_key: str = None) -> ChatOpenAI:
    """Create an LLM client connected to OpenRouter.
    
    Args:
        model_name: Override the model. If None, uses OPENROUTER_MODEL from .env.
        custom_api_key: User-provided API key for BYOK feature.
    """
    return ChatOpenAI(
        model=model_name or OPENROUTER_MODEL,
        api_key=custom_api_key or OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
        temperature=0.1,
        request_timeout=90,
        default_headers={
            "HTTP-Referer": "https://samas.dev",
            "X-Title": "SAMAS",
        },
    )


def parse_llm_json_response(content: str) -> dict | list:
    """Extract and parse JSON from an LLM response.
    
    Handles common LLM quirks:
    1. Response wrapped in ```json ... ``` code blocks
    2. Extra text before/after the JSON
    3. Trailing commas (some models add these)
    
    Returns:
        Parsed JSON as dict or list
        
    Raises:
        ValueError: If no valid JSON found
    """
    content = content.strip()
    
    # Strategy 1: Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Remove markdown code fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', content)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Find outermost JSON object or array
    # Try object first {...}
    first_brace = content.find('{')
    last_brace = content.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(content[first_brace:last_brace + 1])
        except json.JSONDecodeError:
            pass
    
    # Try array [...]
    first_bracket = content.find('[')
    last_bracket = content.rfind(']')
    if first_bracket != -1 and last_bracket > first_bracket:
        try:
            return json.loads(content[first_bracket:last_bracket + 1])
        except json.JSONDecodeError:
            pass
    
    raise ValueError(
        f"Could not parse JSON from LLM response. "
        f"Response starts with: {content[:200]}..."
    )


from langchain_core.runnables.config import RunnableConfig

async def call_llm_with_fallback(
    messages: List[BaseMessage],
    models: Optional[List[str]] = None,
    label: str = "LLM",
    custom_api_key: Optional[str] = None,
    custom_model: Optional[str] = None,
    config: Optional[RunnableConfig] = None,
) -> dict:
    """Call an LLM with automatic model fallback and JSON parsing.
    
    Args:
        messages: List of LangChain messages to send
        models: Override the fallback chain. Defaults to FALLBACK_MODELS.
        label: Label for logging (e.g., "Question Generator")
        custom_api_key: BYOK API Key
        custom_model: BYOK Model Name
        config: LangChain RunnableConfig to preserve tracing context.
        
    Returns:
        Dict with keys:
        - "data": The parsed JSON (dict or list)
        - "model_used": Which model succeeded
        - "raw_content": The raw response text
    """
    # If a custom model is provided, prioritize it or use it exclusively
    if custom_model:
        models_to_try = [custom_model]
        # Optionally add fallbacks if custom model fails, but usually BYOK means stick to their choice
    else:
        models_to_try = list(dict.fromkeys(models or FALLBACK_MODELS))
        
    last_error = None
    
    for model_name in models_to_try:
        print(f"   [*] [{label}] Trying model: {model_name}")
        llm = get_llm(model_name, custom_api_key)
        
        try:
            # Pass the config context so LangSmith can trace the LLM as a child of the graph node
            response = await llm.ainvoke(messages, config=config)
            raw_content = response.content
            
            if not raw_content or not raw_content.strip():
                raise ValueError("LLM returned empty response")
            
            print(f"   [+] [{label}] {model_name} responded ({len(raw_content)} chars)")
            
            parsed = parse_llm_json_response(raw_content)
            return {
                "data": parsed,
                "model_used": model_name,
                "raw_content": raw_content,
            }
            
        except Exception as e:
            last_error = str(e)
            print(f"   [-] [{label}] {model_name} failed: {last_error[:120]}")
            await asyncio.sleep(1)
            continue
    
    raise RuntimeError(
        f"[{label}] All models failed. Last error: {last_error}"
    )

_EMBEDDER = None

def get_embedder(custom_api_key: str = None) -> OpenAIEmbeddings:
    """Create a singleton embedding model client (OpenRouter / OpenAI)."""
    global _EMBEDDER
    
    # If custom key is provided, always create a new instance using that key
    if custom_api_key:
        print("   Loading embedding model with custom BYOK key...")
        return OpenAIEmbeddings(
            openai_api_base=OPENROUTER_BASE_URL,
            openai_api_key=custom_api_key,
            model="openai/text-embedding-3-small"
        )
        
    if _EMBEDDER is None:
        print("   Loading embedding model (OpenRouter / OpenAI)...")
        _EMBEDDER = OpenAIEmbeddings(
            openai_api_base=OPENROUTER_BASE_URL,
            openai_api_key=OPENROUTER_API_KEY,
            model="openai/text-embedding-3-small"
        )
    return _EMBEDDER

