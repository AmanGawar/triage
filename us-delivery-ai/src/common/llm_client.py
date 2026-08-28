"""
Thin LLM client wrapper.

Design decision (see DESIGN_NOTE.md): a single client is shared by Task 1 and Task 2
so temperature/seed/retry behaviour is controlled in one place, not duplicated.

If ANTHROPIC_API_KEY is set, calls the real Claude API with temperature=0 for
determinism. If no key is present, falls back to a deterministic, rule-based
mock so the rest of the pipeline (retrieval, schema validation, evals, Streamlit
UI) can be run and demoed end-to-end without any credentials. This is flagged
loudly wherever it happens — never silently.
"""
from __future__ import annotations
import os
import json
import hashlib
from typing import Optional

USE_REAL_LLM = bool(os.environ.get("ANTHROPIC_API_KEY"))

if USE_REAL_LLM:
    import anthropic
    _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL_NAME = os.environ.get("LLM_MODEL", "claude-sonnet-4-5")


def _deterministic_seed(prompt: str) -> int:
    """Turn a prompt into a stable integer so the mock's 'randomness' is reproducible."""
    return int(hashlib.sha256(prompt.encode()).hexdigest(), 16) % (10 ** 8)


def call_llm(system: str, user: str, max_tokens: int = 1200) -> str:
    """
    Returns raw text from the model. Callers are responsible for parsing/validating
    (see task modules — they ask for JSON matching a Pydantic schema and validate it).

    temperature=0 everywhere: Task 2 requires deterministic output for the same
    input, and there is no reason Task 1 shouldn't also be reproducible for the
    same ticket.
    """
    if USE_REAL_LLM:
        resp = _client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text
    else:
        return _mock_response(system, user)


def _mock_response(system: str, user: str) -> str:
    """
    Deterministic offline fallback — NOT a substitute for the real model's
    reasoning quality. Exists purely so `python run_demo.py` works out of the box
    for a reviewer with no API key, and so the eval harness has something to test
    against in CI without secrets. Swap in ANTHROPIC_API_KEY for real triage
    quality — see README.

    Uses simple keyword heuristics to produce schema-valid, plausible-looking
    output. This is intentionally simple; it is not the graded logic.
    """
    seed = _deterministic_seed(user)
    lower = user.lower()

    urgency = "P3"
    if any(w in lower for w in ["critical", "down", "outage", "urgent", "production", "data loss", "cannot log in", "all users"]):
        urgency = "P1"
    elif any(w in lower for w in ["error", "fail", "broken", "timeout", "blocked"]):
        urgency = "P2"
    elif any(w in lower for w in ["feature request", "would like", "nice to have", "cosmetic"]):
        urgency = "P4"

    category = "How-To"
    for cat, kws in {
        "Bug": ["error", "bug", "broken", "crash", "unexpected"],
        "Performance": ["slow", "timeout", "latency", "lag"],
        "Billing": ["invoice", "charge", "seat", "billing", "payment"],
        "Integration": ["salesforce", "snowflake", "connector", "webhook", "oauth", "integration"],
        "Onboarding": ["onboarding", "new user", "invite", "setup"],
        "Data Loss": ["data loss", "missing data", "deleted", "corrupted"],
        "Feature Request": ["feature request", "would like", "please add"],
    }.items():
        if any(k in lower for k in kws):
            category = cat
            break

    return json.dumps({
        "_mock": True,
        "category": category,
        "urgency": urgency,
        "reasoning": f"[offline mock] keyword heuristic matched on seed {seed}",
        "confidence": 0.55,
    })
