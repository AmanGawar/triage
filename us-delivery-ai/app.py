"""
Bonus (+5): thin Streamlit UI a non-technical TAM or support lead could use.

Run with: streamlit run app.py
"""
import json
import os
import sys
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from common.llm_client import USE_REAL_LLM
from task1_triage.triage import triage_ticket
from task2_summarizer.summarizer import summarize_account, _load_data
from task3_evals.run_evals import run_all

st.set_page_config(page_title="Support & TAM AI Tools", layout="wide")

st.title("Support & TAM AI Tools")
if not USE_REAL_LLM:
    st.warning(
        "Running in **offline mock mode** — no ANTHROPIC_API_KEY found in the environment. "
        "Outputs use a simple keyword-based fallback, not real model reasoning. "
        "Set ANTHROPIC_API_KEY to see real triage/summary quality.",
        icon="⚠️",
    )

tab1, tab2, tab3 = st.tabs(["🎫 Ticket Triage", "📊 Account Health Brief", "✅ Eval Report"])

with tab1:
    st.subheader("Task 1 — Intelligent Ticket Triage")
    col1, col2 = st.columns(2)
    with col1:
        subject = st.text_input("Subject", "Production DataBridge Pro pipeline down, 200 users affected")
        body = st.text_area(
            "Body", height=180,
            value="Our main ingestion pipeline stopped processing 20 minutes ago. "
                  "Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team."
        )
        if st.button("Triage ticket", type="primary"):
            with st.spinner("Retrieving knowledge base + classifying..."):
                result = triage_ticket({"ticket_id": "UI-DEMO", "subject": subject, "body": body})
            st.session_state["last_triage"] = result.model_dump()

    with col2:
        if "last_triage" in st.session_state:
            r = st.session_state["last_triage"]
            urgency_color = {"P1": "🔴", "P2": "🟠", "P3": "🟡", "P4": "🟢"}.get(r["urgency"], "⚪")
            st.metric("Urgency", f"{urgency_color} {r['urgency']}")
            st.metric("Category", r["category"])
            st.metric("Routed to", r["recommended_team"])
            if r["low_confidence_flag"]:
                st.error(f"⚠️ Low confidence ({r['confidence']:.2f}) — recommend human review")
            else:
                st.success(f"Confidence: {r['confidence']:.2f}")
            st.write("**Reasoning:**", r["urgency_reasoning"])
            st.write("**Draft response:**")
            st.info(r["draft_response"])
            with st.expander(f"Matched knowledge-base evidence ({len(r['matched_kb_docs'])})"):
                for kb in r["matched_kb_docs"]:
                    st.markdown(f"**{kb['doc_path']}** — *{kb['section']}* (score: {kb['relevance_score']})")
                    st.code(kb["snippet"], language="markdown")
        else:
            st.info("Enter a ticket and click 'Triage ticket' to see results here.")

with tab2:
    st.subheader("Task 2 — TAM Account Health Brief")
    accounts, _ = _load_data()
    options = {f"{a['company']} ({aid})": aid for aid, a in accounts.items()}
    choice = st.selectbox("Select an account", list(options.keys()))
    if st.button("Generate brief", type="primary"):
        with st.spinner("Analysing account + ticket history..."):
            brief = summarize_account(options[choice])
        st.session_state["last_brief"] = brief.model_dump()

    if "last_brief" in st.session_state:
        b = st.session_state["last_brief"]
        health_color = {"Healthy": "🟢", "At Risk": "🟠", "Churning": "🔴", "New": "🔵"}.get(b["health_status"], "⚪")
        st.metric("Health status", f"{health_color} {b['health_status']}")
        st.write("### Executive Summary")
        st.write(b["executive_summary"])
        st.write(f"### Risk Flags ({len(b['risk_flags'])})")
        if b["risk_flags"]:
            for f in b["risk_flags"]:
                sev_color = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(f["severity"], "⚪")
                st.markdown(f"{sev_color} **{f['severity'].upper()}** — _{f['reason']}_")
                st.caption(f"Quote ({f['ticket_id']}): \"{f['quote']}\"")
        else:
            st.write("No risk flags identified.")
        st.write("### Talking Points")
        for tp in b["talking_points"]:
            st.markdown(f"- {tp}")

with tab3:
    st.subheader("Task 3 — Evaluation Harness Results")
    if st.button("Run eval harness now"):
        with st.spinner("Running all test cases..."):
            summary = run_all()
        st.session_state["eval_summary"] = summary

    if "eval_summary" in st.session_state:
        s = st.session_state["eval_summary"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall pass rate", f"{s['pass_rate']*100:.0f}%")
        c2.metric("Task 1 pass rate", f"{s['task1_pass_rate']*100:.0f}%")
        c3.metric("Task 2 pass rate", f"{s['task2_pass_rate']*100:.0f}%")
        for r in s["task1_results"] + s["task2_results"]:
            icon = "✅" if r["pass"] else "❌"
            with st.expander(f"{icon} {r['case_id']} (score: {r['score']:.2f})"):
                if r["note"]:
                    st.caption(r["note"])
                st.json(r["checks"])
    else:
        st.info("Click 'Run eval harness now' to execute all test cases live.")
