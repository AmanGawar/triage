"""
Single entry-point script: runs Task 1, Task 2, and Task 3 end-to-end and prints
results, then writes eval_report.json / eval_report.md to the repo root.

Usage:
    python run_demo.py

Works with zero setup (offline deterministic mock). Set ANTHROPIC_API_KEY in your
environment (or a .env file — see .env.example) beforehand for real LLM output.
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from common.llm_client import USE_REAL_LLM
from task1_triage.triage import triage_ticket
from task2_summarizer.summarizer import summarize_account, _load_data
from task3_evals.run_evals import run_all, write_reports


def line(char="-", n=70):
    print(char * n)


def main():
    print(f"Running with {'REAL Anthropic LLM' if USE_REAL_LLM else 'OFFLINE MOCK (no ANTHROPIC_API_KEY set)'}")
    line("=")

    print("\nTASK 1 — Ticket Triage (sample ticket)\n")
    sample_ticket = {
        "ticket_id": "TKT-DEMO-1",
        "subject": "Production DataBridge Pro pipeline down, 200 users affected",
        "body": "Our main ingestion pipeline stopped processing 20 minutes ago. "
                "Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team.",
    }
    triage_result = triage_ticket(sample_ticket)
    print(triage_result.model_dump_json(indent=2))
    line()

    print("\nTASK 2 — Account Health Brief (first account in accounts.json)\n")
    accounts, _ = _load_data()
    demo_account_id = next(iter(accounts))
    brief = summarize_account(demo_account_id)
    print(brief.model_dump_json(indent=2))
    line()

    print("\nTASK 3 — Eval Harness (all test cases)\n")
    summary = run_all()
    repo_root = os.path.dirname(os.path.abspath(__file__))
    json_path, md_path = write_reports(summary, repo_root)
    print(f"Overall: {summary['passed']}/{summary['total_cases']} passed "
          f"({summary['pass_rate']*100:.0f}%)")
    print(f"  Task 1 pass rate: {summary['task1_pass_rate']*100:.0f}%")
    print(f"  Task 2 pass rate: {summary['task2_pass_rate']*100:.0f}%")
    print(f"Full report written to: {json_path} and {md_path}")
    line("=")

    print("\nTo try the interactive UI: streamlit run app.py")
    print("To try the API: uvicorn src.task1_triage.triage:build_app --factory --reload")


if __name__ == "__main__":
    main()
