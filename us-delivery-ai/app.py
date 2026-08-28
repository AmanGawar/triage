"""
app.py — Streamlit UI for the Support & TAM AI Tools.

Run:
    streamlit run app.py

Task 1:
- Accept raw ticket as text or JSON
- Classify product area, issue category and urgency P1-P4
- Provide reasoning
- Match known issues from the knowledge base
- Recommend responder team
- Draft first-response message

Task 2:
- Generate TAM account health brief

Task 3:
- Run evaluation harness
"""

import json
import os
import sys

import streamlit as st


# ============================================================
# PATH SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# ============================================================
# IMPORTS
# ============================================================

from common.llm_client import USE_REAL_LLM
from task1_triage.triage import triage_ticket
from task2_summarizer.summarizer import summarize_account, _load_data
from task3_evals.run_evals import run_all


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Support & TAM AI Tools",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Support & TAM AI Tools")
st.caption(
    "AI-powered ticket triage, account health summarisation and evaluation."
)


# ============================================================
# LLM STATUS
# ============================================================

if USE_REAL_LLM:
    st.success("Real LLM mode is active.")
else:
    st.warning(
        "⚠️ Offline mock mode is active. "
        "The output is keyword-based and is not real LLM reasoning. "
        "Configure your API key for real classification."
    )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3 = st.tabs(
    [
        "🎫 Ticket Triage",
        "📊 Account Health Brief",
        "✅ Eval Report",
    ]
)


# ============================================================
# TASK 1 — TICKET TRIAGE
# ============================================================

with tab1:

    st.header("Task 1 — Intelligent Ticket Triage")

    st.markdown(
        """
        Enter a raw support ticket. The system will determine:

        - Product area
        - Issue category
        - Urgency tier (P1–P4)
        - Reasoning
        - Known issue / knowledge-base match
        - Recommended responder team
        - Draft first response
        """
    )

    # --------------------------------------------------------
    # INPUT TYPE
    # --------------------------------------------------------

    input_mode = st.radio(
        "Ticket input format",
        ["Text", "JSON"],
        horizontal=True,
    )

    ticket_input = None

    # --------------------------------------------------------
    # TEXT INPUT
    # --------------------------------------------------------

    if input_mode == "Text":

        col1, col2 = st.columns(2)

        with col1:

            subject = st.text_input(
                "Subject",
                value=(
                    "Production DataBridge Pro pipeline down, "
                    "200 users affected"
                ),
            )

            body = st.text_area(
                "Body",
                height=220,
                value=(
                    "Our main ingestion pipeline stopped processing "
                    "20 minutes ago. Getting ERR_CONNECTION_TIMEOUT "
                    "after 30s. This is production and blocking our "
                    "whole team."
                ),
            )

            ticket_input = {
                "ticket_id": "UI-DEMO",
                "subject": subject,
                "body": body,
            }

        with col2:

            st.markdown("### Example raw ticket")

            st.code(
                """Subject:
Production DataBridge Pro pipeline down, 200 users affected

Body:
Our main ingestion pipeline stopped processing 20 minutes ago.
Getting ERR_CONNECTION_TIMEOUT after 30s.
This is production and blocking our whole team.""",
                language="text",
            )

    # --------------------------------------------------------
    # JSON INPUT
    # --------------------------------------------------------

    else:

        default_json = """{
  "ticket_id": "UI-DEMO",
  "subject": "Production DataBridge Pro pipeline down, 200 users affected",
  "body": "Our main ingestion pipeline stopped processing 20 minutes ago. Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team."
}"""

        json_input = st.text_area(
            "Raw Ticket JSON",
            value=default_json,
            height=250,
        )

        try:

            parsed_ticket = json.loads(json_input)

            if not isinstance(parsed_ticket, dict):

                st.error("Ticket JSON must be a JSON object.")

            elif (
                "subject" not in parsed_ticket
                or "body" not in parsed_ticket
            ):

                st.error(
                    'Ticket JSON must contain "subject" and "body".'
                )

            else:

                ticket_input = {
                    "ticket_id": parsed_ticket.get(
                        "ticket_id",
                        "UI-DEMO",
                    ),
                    "subject": parsed_ticket["subject"],
                    "body": parsed_ticket["body"],
                }

                st.success("✅ Valid ticket JSON.")

        except json.JSONDecodeError as e:

            st.error(f"Invalid JSON: {e}")

    # --------------------------------------------------------
    # TRIAGE BUTTON
    # --------------------------------------------------------

    st.divider()

    if st.button(
        "🚀 Triage Ticket",
        type="primary",
        use_container_width=True,
    ):

        if ticket_input is None:

            st.error("Please enter a valid ticket.")

        elif (
            not ticket_input["subject"].strip()
            or not ticket_input["body"].strip()
        ):

            st.error("Both subject and body are required.")

        else:

            with st.spinner(
                "Retrieving knowledge base + classifying ticket..."
            ):

                try:

                    result = triage_ticket(ticket_input)

                    st.session_state["last_triage"] = (
                        result.model_dump()
                    )

                    st.session_state["last_triage_error"] = None

                except Exception as e:

                    st.session_state["last_triage_error"] = str(e)

    # ========================================================
    # TRIAGE RESULT
    # ========================================================

    if st.session_state.get("last_triage_error"):

        st.error(
            f"Triage failed: "
            f"{st.session_state['last_triage_error']}"
        )

    elif "last_triage" in st.session_state:

        r = st.session_state["last_triage"]

        # ----------------------------------------------------
        # MODE
        # ----------------------------------------------------

        if not USE_REAL_LLM:

            st.warning(
                "⚠️ Result generated by the offline mock classifier. "
                "This is a deterministic placeholder, not real "
                "LLM reasoning."
            )

        else:

            st.success(
                "✅ Result generated using the configured real LLM."
            )

        # ----------------------------------------------------
        # CLASSIFICATION
        # ----------------------------------------------------

        st.subheader("Triage Result")

        urgency_icons = {
            "P1": "🔴",
            "P2": "🟠",
            "P3": "🟡",
            "P4": "🟢",
        }

        urgency = r.get(
            "urgency",
            "Unknown",
        )

        icon = urgency_icons.get(
            urgency,
            "⚪",
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Urgency",
                f"{icon} {urgency}",
            )

        with c2:

            st.metric(
                "Issue Category",
                r.get(
                    "category",
                    "Unknown",
                ),
            )

        with c3:

            st.metric(
                "Product Area",
                r.get(
                    "product_area",
                    "Unknown",
                ),
            )

        # ----------------------------------------------------
        # RESPONDER TEAM
        # ----------------------------------------------------

        st.markdown("### Recommended Responder Team")

        st.info(
            r.get(
                "recommended_team",
                "Not specified",
            )
        )

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        confidence = r.get("confidence")

        if confidence is not None:

            if r.get("low_confidence_flag", False):

                st.error(
                    f"⚠️ Low confidence ({confidence:.2f}) — "
                    "recommend human review."
                )

            else:

                st.success(
                    f"Confidence: {confidence:.2f}"
                )

        # ----------------------------------------------------
        # REASONING
        # ----------------------------------------------------

        st.markdown("### Reasoning")

        st.write(
            r.get(
                "urgency_reasoning",
                "No reasoning provided.",
            )
        )

        # ----------------------------------------------------
        # AMBIGUITY
        # ----------------------------------------------------

        if r.get("unresolved_ambiguity"):

            st.warning(
                f"**Unresolved ambiguity:** "
                f"{r['unresolved_ambiguity']}"
            )

        # ----------------------------------------------------
        # DRAFT RESPONSE
        # ----------------------------------------------------

        st.markdown("### Draft First Response")

        st.info(
            r.get(
                "draft_response",
                "No draft response generated.",
            )
        )

        # ----------------------------------------------------
        # KNOWLEDGE BASE
        # ----------------------------------------------------

        st.markdown("### Known Issue / Knowledge-Base Match")

        matched_docs = r.get(
            "matched_kb_docs",
            [],
        )

        if not matched_docs:

            st.info(
                "No known issue pattern was matched "
                "in the knowledge base."
            )

        else:

            st.success(
                f"Matched {len(matched_docs)} knowledge-base document(s)."
            )

            for i, kb in enumerate(
                matched_docs,
                start=1,
            ):

                with st.expander(
                    f"📄 Evidence {i}: "
                    f"{kb.get('doc_path', 'Unknown document')}"
                ):

                    st.markdown(
                        f"**Document:** "
                        f"{kb.get('doc_path', 'Unknown')}"
                    )

                    st.markdown(
                        f"**Section:** "
                        f"{kb.get('section', 'Unknown')}"
                    )

                    st.markdown(
                        f"**Relevance score:** "
                        f"{kb.get('relevance_score', 'N/A')}"
                    )

                    st.markdown("**Relevant evidence:**")

                    st.code(
                        kb.get(
                            "snippet",
                            "",
                        ),
                        language="markdown",
                    )

        # ----------------------------------------------------
        # RAW JSON
        # ----------------------------------------------------

        with st.expander("🔍 Raw JSON Output"):

            st.json(r)

    else:

        st.info(
            "Enter a ticket and click "
            "**Triage Ticket** to generate the result."
        )


# ============================================================
# TASK 2 — ACCOUNT HEALTH BRIEF
# ============================================================

with tab2:

    st.header("Task 2 — TAM Account Health Brief")

    accounts, _ = _load_data()

    options = {
        f"{a['company']} ({aid})": aid
        for aid, a in accounts.items()
    }

    choice = st.selectbox(
        "Select an account",
        list(options.keys()),
    )

    if st.button(
        "📊 Generate Account Brief",
        type="primary",
    ):

        with st.spinner(
            "Analysing account and ticket history..."
        ):

            try:

                brief = summarize_account(
                    options[choice]
                )

                st.session_state["last_brief"] = (
                    brief.model_dump()
                )

                st.session_state["last_brief_error"] = None

            except Exception as e:

                st.session_state["last_brief_error"] = str(e)

    if st.session_state.get("last_brief_error"):

        st.error(
            f"Brief generation failed: "
            f"{st.session_state['last_brief_error']}"
        )

    elif "last_brief" in st.session_state:

        b = st.session_state["last_brief"]

        # ----------------------------------------------------
        # HEALTH STATUS
        # ----------------------------------------------------

        health_icons = {
            "Healthy": "🟢",
            "At Risk": "🟠",
            "Churning": "🔴",
            "New": "🔵",
        }

        health = b.get(
            "health_status",
            "Unknown",
        )

        health_icon = health_icons.get(
            health,
            "⚪",
        )

        st.metric(
            "Health Status",
            f"{health_icon} {health}",
        )

        # ----------------------------------------------------
        # EXECUTIVE SUMMARY
        # ----------------------------------------------------

        st.markdown("### Executive Summary")

        st.write(
            b.get(
                "executive_summary",
                "No summary generated.",
            )
        )

        # ----------------------------------------------------
        # RISK FLAGS
        # ----------------------------------------------------

        risk_flags = b.get(
            "risk_flags",
            [],
        )

        st.markdown(
            f"### Risk Flags ({len(risk_flags)})"
        )

        if risk_flags:

            for flag in risk_flags:

                severity = flag.get(
                    "severity",
                    "unknown",
                )

                severity_icon = {
                    "high": "🔴",
                    "medium": "🟠",
                    "low": "🟡",
                }.get(
                    severity.lower(),
                    "⚪",
                )

                st.markdown(
                    f"{severity_icon} "
                    f"**{severity.upper()}** — "
                    f"_{flag.get('reason', '')}_"
                )

                st.caption(
                    f"Quote ({flag.get('ticket_id', 'N/A')}): "
                    f"\"{flag.get('quote', '')}\""
                )

        else:

            st.write(
                "No risk flags identified."
            )

        # ----------------------------------------------------
        # TALKING POINTS
        # ----------------------------------------------------

        st.markdown("### Recommended Talking Points")

        for point in b.get(
            "talking_points",
            [],
        ):

            st.markdown(
                f"- {point}"
            )


# ============================================================
# TASK 3 — EVALUATION HARNESS
# ============================================================

with tab3:

    st.header("Task 3 — Evaluation Harness Results")

    st.markdown(
        """
        Run the evaluation harness to test Task 1 and Task 2
        systematically.
        """
    )

    if st.button(
        "🧪 Run Evaluation Harness",
        type="primary",
    ):

        with st.spinner(
            "Running all evaluation test cases..."
        ):

            try:

                summary = run_all()

                st.session_state["eval_summary"] = summary

                st.session_state["eval_error"] = None

            except Exception as e:

                st.session_state["eval_error"] = str(e)

    if st.session_state.get("eval_error"):

        st.error(
            f"Evaluation failed: "
            f"{st.session_state['eval_error']}"
        )

    elif "eval_summary" in st.session_state:

        s = st.session_state["eval_summary"]

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Overall Pass Rate",
                f"{s['pass_rate'] * 100:.0f}%",
            )

        with c2:

            st.metric(
                "Task 1 Pass Rate",
                f"{s['task1_pass_rate'] * 100:.0f}%",
            )

        with c3:

            st.metric(
                "Task 2 Pass Rate",
                f"{s['task2_pass_rate'] * 100:.0f}%",
            )

        # ----------------------------------------------------
        # RESULTS
        # ----------------------------------------------------

        st.markdown("### Test Case Results")

        for result in (
            s["task1_results"]
            + s["task2_results"]
        ):

            icon = (
                "✅"
                if result["pass"]
                else "❌"
            )

            with st.expander(
                f"{icon} "
                f"{result['case_id']} "
                f"(score: {result['score']:.2f})"
            ):

                if result.get("note"):

                    st.caption(
                        result["note"]
                    )

                st.json(
                    result["checks"]
                )

    else:

        st.info(
            "Click **Run Evaluation Harness** "
            "to execute all test cases."
        )
