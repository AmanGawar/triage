"""
Task 1 — Intelligent ticket triage agent.

Public entry point: triage_ticket(ticket_text_or_dict) -> TriageResult

Pipeline:
  1. Parse raw input (free text, or {"subject":..., "body":...})
  2. Retrieve top-matching KB chunks (TF-IDF) as grounding context
  3. Prompt the LLM for classification + reasoning + draft response,
     constrained to JSON matching TriageResult
  4. Validate against the Pydantic schema (retry once on invalid JSON)
  5. Route to a responder team based on category (deterministic mapping,
     not left to the LLM — routing rules are business logic, not a judgement call)
"""
from __future__ import annotations
import json
import re
import sys
import os
from typing import Union, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.llm_client import call_llm, USE_REAL_LLM
from common.kb_retrieval import KBIndex
from common.schemas import TriageResult, KBMatch

# Deterministic routing table — kept out of the LLM's hands on purpose.
# Product/category -> team. This is the kind of business rule that should not
# drift between LLM calls.
ROUTING_TABLE = {
    "Billing": "Billing Support",
    "Onboarding": "Customer Success",
    "Data Loss": "Tier-2 Engineering (Data Loss — expedited)",
    "Integration": "Integrations Team",
    "Performance": "Tier-2 Engineering (Performance)",
    "Bug": "Tier-2 Engineering",
    "Feature Request": "Product Team",
    "How-To": "Tier-1 Support",
}

_KB_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "knowledge-base")
_kb_index: Optional[KBIndex] = None


def _get_kb_index() -> KBIndex:
    global _kb_index
    if _kb_index is None:
        _kb_index = KBIndex(_KB_ROOT)
    return _kb_index


def _parse_input(ticket: Union[str, Dict]) -> Dict[str, str]:
    if isinstance(ticket, dict):
        subject = ticket.get("subject", "")
        body = ticket.get("body", "")
        ticket_id = ticket.get("ticket_id", "UNSPECIFIED")
    else:
        # free text: treat first line as subject if it looks like one
        lines = ticket.strip().split("\n", 1)
        subject = lines[0][:120]
        body = ticket
        ticket_id = "UNSPECIFIED"
    return {"ticket_id": ticket_id, "subject": subject, "body": body}


SYSTEM_PROMPT = """You are a support-ticket triage assistant for a B2B SaaS company with five \
products: DataBridge Pro, CloudSync, AnalyticsHub, SecureVault, WorkflowEngine.

Given a ticket and relevant knowledge-base excerpts, respond with ONLY a JSON object \
(no markdown fences, no commentary) with these exact keys:
{
  "product_area": string,
  "category": one of ["Bug","Feature Request","How-To","Performance","Billing","Integration","Onboarding","Data Loss"],
  "urgency": one of ["P1","P2","P3","P4"],
  "urgency_reasoning": string (1-2 sentences),
  "draft_response": string (a short, professional first-response message to the customer),
  "confidence": number between 0 and 1,
  "low_confidence_flag": boolean (true if the ticket is ambiguous or under-specified)
}

Urgency guide: P1 = business-stopping/production down/data loss affecting many users.
P2 = major impact, workaround exists but painful. P3 = moderate, workaround available.
P4 = cosmetic/minor/feature request.
Be conservative: if unsure between two tiers, and the ticket mentions production impact
or many affected users, lean toward the more urgent tier and say so in the reasoning."""


def _build_user_prompt(parsed: Dict, kb_matches) -> str:
    kb_context = "\n\n".join(
        f"[KB: {c.doc_path} — {c.heading}]\n{c.text[:500]}" for c, _ in kb_matches
    ) or "(no relevant KB documents found)"
    return f"""TICKET SUBJECT: {parsed['subject']}

TICKET BODY:
{parsed['body']}

RELEVANT KNOWLEDGE BASE EXCERPTS:
{kb_context}

Respond with the JSON object only."""


def _extract_json(raw: str) -> Dict:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return json.loads(raw)


def triage_ticket(ticket: Union[str, Dict]) -> TriageResult:
    parsed = _parse_input(ticket)
    kb = _get_kb_index()
    query = f"{parsed['subject']} {parsed['body']}"
    kb_matches = kb.search(query, k=3)

    user_prompt = _build_user_prompt(parsed, kb_matches)
    raw = call_llm(SYSTEM_PROMPT, user_prompt)

    try:
        data = _extract_json(raw)
    except json.JSONDecodeError:
        # one retry with a stricter reminder — real-world LLM calls occasionally
        # wrap JSON in prose despite instructions
        raw_retry = call_llm(
            SYSTEM_PROMPT + "\n\nIMPORTANT: output raw JSON only, nothing else.",
            user_prompt,
        )
        data = _extract_json(raw_retry)

    # Mock-mode responses use a smaller key set — normalise so schema validation still passes
    if data.get("_mock"):
        data = {
            "product_area": parsed["subject"][:60] or "Unknown",
            "category": data["category"],
            "urgency": data["urgency"],
            "urgency_reasoning": data["reasoning"],
            "draft_response": (
                f"Hi, thanks for reaching out about \"{parsed['subject']}\". "
                f"We've logged this as a {data['category']} issue and are looking into it."
            ),
            "confidence": data["confidence"],
            "low_confidence_flag": data["confidence"] < 0.6,
        }

    category = data["category"]
    recommended_team = ROUTING_TABLE.get(category, "Tier-1 Support")

    result = TriageResult(
        ticket_id=parsed["ticket_id"],
        product_area=data.get("product_area", "Unknown"),
        category=category,
        urgency=data["urgency"],
        urgency_reasoning=data["urgency_reasoning"],
        matched_kb_docs=[
            KBMatch(doc_path=c.doc_path, section=c.heading, snippet=c.text[:300], relevance_score=round(score, 3))
            for c, score in kb_matches
        ],
        recommended_team=recommended_team,
        draft_response=data["draft_response"],
        confidence=data.get("confidence", 0.5),
        low_confidence_flag=data.get("low_confidence_flag", False),
    )
    return result


# ---------- Optional FastAPI wrapper ----------
# TicketIn is module-level (not nested in build_app) because some FastAPI/Pydantic
# version combinations fail to detect a locally-scoped class as a request body
# and silently treat it as a query parameter instead — moving it to module scope
# avoids that trap entirely.
from pydantic import BaseModel as _BaseModel


class TicketIn(_BaseModel):
    ticket_id: Optional[str] = "UNSPECIFIED"
    subject: Optional[str] = ""
    body: str


def build_app():
    from fastapi import FastAPI

    app = FastAPI(title="Ticket Triage API")

    @app.post("/triage", response_model=TriageResult)
    def triage_endpoint(ticket: TicketIn):
        return triage_ticket(ticket.model_dump())

    @app.get("/health")
    def health():
        return {"status": "ok", "using_real_llm": USE_REAL_LLM}

    return app


if __name__ == "__main__":
    sample = {
        "ticket_id": "TKT-DEMO-1",
        "subject": "Production DataBridge Pro pipeline down, 200 users affected",
        "body": "Our main ingestion pipeline stopped processing 20 minutes ago. "
                "Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team.",
    }
    result = triage_ticket(sample)
    print(result.model_dump_json(indent=2))
