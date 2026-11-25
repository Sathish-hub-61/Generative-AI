"""LLM module – uses FreeLLM API (OpenAI-compatible).

Core rule (non-negotiable): undocumented fields are NEVER sent to the LLM.
Only documented fields with a DocEntry are eligible for describe_field().
Responses are cached to cache.json so repeated runs skip the API.
If the API fails, the raw source text is used as the description.
"""

import os
import json
import requests
from pathlib import Path
from typing import Any, Dict, List

CACHE_PATH = Path(__file__).parent / "cache.json"
ENV_PATH = Path(__file__).parent / ".env"


def _load_env():
    """Load key=value pairs from .env into os.environ if not already set."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# API call counter (for testing the code gate)
# ---------------------------------------------------------------------------
_api_call_count = 0


def get_api_call_count() -> int:
    return _api_call_count


def reset_api_call_count():
    global _api_call_count
    _api_call_count = 0


# ---------------------------------------------------------------------------
# describe_field  –  called ONLY for documented fields
# ---------------------------------------------------------------------------

def describe_field(field_name: str, doc_entry: Any, stats: Any) -> Dict[str, Any]:
    """Generate a plain-language description using ONLY the supplied source text.

    Parameters
    ----------
    field_name : str – column name
    doc_entry  : DocEntry – must not be None (caller enforces this)
    stats      : Stats object from profiler

    Returns
    -------
    dict with keys: plain_description, uses_only_source
    """
    global _api_call_count

    cache = _load_cache()
    cache_key = f"describe::{field_name}"
    if cache_key in cache:
        return cache[cache_key]

    api_key = os.getenv("FREELLMAPI_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # No key – fall back to raw source text (no API call)
        result = {"plain_description": doc_entry.description, "uses_only_source": True}
        cache[cache_key] = result
        _save_cache(cache)
        return result

    # Build the strict prompt
    system_prompt = (
        "You are a documentation assistant. "
        "Use ONLY the SOURCE_TEXT provided below. "
        "If it is insufficient, return {\"plain_description\": \"INSUFFICIENT\", \"uses_only_source\": false}. "
        "Do NOT use outside knowledge about banking or this dataset. "
        "Do NOT infer meaning from the field name or sample values. "
        "Return valid JSON only with keys: plain_description (string), uses_only_source (boolean)."
    )
    user_prompt = f"SOURCE_TEXT:\n{doc_entry.description}\n\nDescribe the field '{field_name}' in one plain sentence."

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 200,
    }

    base_url = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
    if base_url:
        api_url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    else:
        api_url = os.getenv("FREELLMAPI_URL", "https://api.freellm.com/v1/chat/completions")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        _api_call_count += 1
        resp = requests.post(api_url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        if "plain_description" not in result:
            raise ValueError("Missing plain_description")
    except Exception:
        # Fallback to raw source text
        result = {"plain_description": doc_entry.description, "uses_only_source": True}

    cache[cache_key] = result
    _save_cache(cache)
    return result


# ---------------------------------------------------------------------------
# narrate  –  reword findings into markdown; may NOT add findings or numbers
# ---------------------------------------------------------------------------

def narrate(findings: List[Dict[str, Any]]) -> str:
    """Convert findings list into a readable Markdown report.
    Deterministic rewrite – no LLM needed for the prototype.
    """
    if not findings:
        return "### No Limitations Detected\n\nThe dataset passed all quality checks."

    lines = ["# Limitations Report\n"]
    for i, f in enumerate(findings, 1):
        sev = f.get("severity", "low").upper()
        lines.append(f"### {i}. {f['title']}")
        lines.append(f"- **Severity:** {sev}")
        lines.append(f"- **Rule:** {f.get('rule_id', 'N/A')}")
        lines.append(f"- **Evidence:** {f['evidence']}")
        lines.append("")
    return "\n".join(lines)
