"""
Shared structured-output schemas for Task 1 (triage) and Task 2 (account brief).
Using Pydantic means the LLM's output is validated against a strict schema instead
of trusting free-form JSON the model might drift on.
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ---------- Task 1: Ticket Triage ----------

Category = Literal[
    "Bug", "Feature Request", "How-To", "Performance",
    "Billing", "Integration", "Onboarding", "Data Loss"
]
Urgency = Literal["P1", "P2", "P3", "P4"]


class KBMatch(BaseModel):
    doc_path: str = Field(..., description="Relative path of the matched knowledge-base file")
    section: Optional[str] = Field(None, description="Heading/section within the doc that matched")
    snippet: str = Field(..., description="The retrieved chunk text used as evidence")
    relevance_score: float = Field(..., ge=0, le=1)


class TriageResult(BaseModel):
    ticket_id: str
    product_area: str = Field(..., description="Best-guess product / module the ticket concerns")
    category: Category
    urgency: Urgency
    urgency_reasoning: str = Field(..., description="Short justification for the assigned urgency")
    matched_kb_docs: List[KBMatch] = Field(default_factory=list)
    recommended_team: str
    draft_response: str = Field(..., description="Draft first-response message for the support agent")
    confidence: float = Field(..., ge=0, le=1)
    low_confidence_flag: bool = Field(
        default=False,
        description="True when the model itself is unsure (e.g. ambiguous ticket) — surfaced for human review"
    )


# ---------- Task 2: Account Health Brief ----------

class RiskFlag(BaseModel):
    ticket_id: str
    quote: str = Field(..., description="Direct quote from the ticket body or escalation note justifying the flag")
    reason: str = Field(..., description="Why this quote indicates churn risk / escalation")
    severity: Literal["low", "medium", "high"]


class AccountBrief(BaseModel):
    account_id: str
    company: str
    executive_summary: str = Field(..., description="3-5 sentence overview")
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    talking_points: List[str] = Field(default_factory=list)
    health_status: str
    generated_deterministically: bool = True
