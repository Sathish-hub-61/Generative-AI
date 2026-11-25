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


# ---------------------------------------------------------------------------
# answer_dataset_query  –  AI assistant grounded in dataset stats & findings
# ---------------------------------------------------------------------------

def _fallback_answer(question: str, context: Dict[str, Any]) -> str:
    """Deterministic fallback when LLM API is unavailable."""
    q = question.lower()
    summary = context.get("summary", {})
    dictionary = context.get("dictionary", [])
    findings = context.get("findings", [])

    # Check if user asked about specific columns
    mentioned = [r for r in dictionary if r["Field"].lower() in q]
    if mentioned:
        parts = []
        for r in mentioned:
            line = (
                f"- **{r['Field']}** (`{r['Observed type']}`): "
                f"{r['Distinct']} distinct, {r['Missing %']} missing. "
                f"Status: {r['Status']} ({r['Documented meaning']}). "
                f"Examples: {r['Example values']}."
            )
            if r.get("min") is not None:
                line += f" Range: [{r['min']}, {r['max']}], mean: {r['mean']}."
            if r.get("top_values"):
                tops = ", ".join(f"{k}: {v}" for k, v in list(r["top_values"].items())[:3])
                line += f" Top values: {tops}."
            parts.append(line)
            col_findings = [
                f for f in findings
                if r["Field"].lower() in f.get("title", "").lower() or r["Field"].lower() in f.get("evidence", "").lower()
            ]
            for cf in col_findings:
                parts.append(f"  - [{cf['rule_id']}] {cf['title']}: {cf['evidence']}")
        return "\n".join(parts)

    if any(k in q for k in ("limitation", "issue", "gap", "problem", "outlier", "placeholder", "duplicate", "missing")):
        if not findings:
            return "No limitations or quality issues were detected in the dataset."
        lines = [f"Found **{len(findings)}** limitations/issues:"]
        for f in findings[:10]:
            lines.append(f"- **[{f['rule_id']}] {f['title']}** ({f['severity'].upper()}): {f['evidence']}")
        return "\n".join(lines)

    if any(k in q for k in ("numeric", "stat", "min", "max", "mean", "average")):
        num_rows = [r for r in dictionary if r.get("min") is not None]
        if not num_rows:
            return "No numeric columns found in this dataset."
        lines = ["Numeric column statistics:"]
        for r in num_rows:
            lines.append(f"- **{r['Field']}**: min={r['min']}, max={r['max']}, mean={r['mean']}, distinct={r['Distinct']}")
        return "\n".join(lines)

    # Default overview
    cols = ", ".join(r["Field"] for r in dictionary)
    return (
        f"Dataset has **{summary.get('total_rows', '?'):,} rows** and **{summary.get('total_fields', '?')} columns** "
        f"({summary.get('documented', 0)} documented, {summary.get('undocumented', 0)} undocumented, "
        f"{summary.get('issues', 0)} issues).\n\n"
        f"**Columns:** {cols}"
    )


def answer_dataset_query(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Answer a user query using ONLY the grounded dataset context."""
    api_key = os.getenv("FREELLMAPI_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"answer": _fallback_answer(question, context), "source": "local"}

    base_url = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
    if base_url:
        api_url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    else:
        api_url = os.getenv("FREELLMAPI_URL", "https://api.freellm.com/v1/chat/completions")

    system_prompt = (
        "You are Verity, a strictly data-driven dataset documentation assistant. "
        "Answer the user's question using ONLY the DATASET_CONTEXT JSON provided below. "
        "Rules: "
        "1. Never invent numbers, row counts, percentages, or column meanings. "
        "2. If a column is marked Undocumented, state that it is Undocumented and do NOT infer its meaning. "
        "3. Cite exact column names, counts, and row numbers from the context when answering about issues or locations. "
        "4. If the context does not contain enough information to answer, say so clearly."
    )

    # Keep context compact so it fits cleanly in prompt
    compact_context = json.dumps(context, ensure_ascii=False)
    if len(compact_context) > 12000:
        compact_context = compact_context[:12000] + "..."

    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"DATASET_CONTEXT:\n{compact_context}\n\nQUESTION: {question}"},
        ],
        "temperature": 0,
        "max_tokens": 500,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=25)
        resp.raise_for_status()
        answer = resp.json()["choices"][0]["message"]["content"].strip()
        if not answer:
            raise ValueError("Empty response")
        return {"answer": answer, "source": "llm"}
    except Exception:
        return {"answer": _fallback_answer(question, context), "source": "local-fallback"}
