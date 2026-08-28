"""
Test cases for the eval harness. Each case pairs an input with acceptance
criteria — either rule-based (checked in code) or llm_judge (a rubric question
answered by a separate LLM call, never the same call that produced the output).

5+ cases per task, including at least one adversarial case per task, as required.
"""

# ---------- Task 1 test cases ----------

TASK1_CASES = [
    {
        "id": "t1_case_1_clear_p1_bug",
        "input": {
            "ticket_id": "TEST-1",
            "subject": "Production DataBridge Pro pipeline down, 200 users affected",
            "body": "Our main ingestion pipeline stopped processing 20 minutes ago. "
                    "Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team.",
        },
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "urgency", "op": "in", "value": ["P1", "P2"]},
                {"field": "category", "op": "==", "value": "Bug"},
                {"field": "matched_kb_docs", "op": "min_len", "value": 1},
            ],
        },
    },
    {
        "id": "t1_case_2_billing_question",
        "input": {
            "ticket_id": "TEST-2",
            "subject": "Why are we being charged for more seats than active users?",
            "body": "We have 40 active users but the invoice shows 55 seats billed. Can you explain the discrepancy?",
        },
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "category", "op": "==", "value": "Billing"},
                {"field": "recommended_team", "op": "==", "value": "Billing Support"},
            ],
        },
    },
    {
        "id": "t1_case_3_feature_request_low_urgency",
        "input": {
            "ticket_id": "TEST-3",
            "subject": "Feature request: bulk export from AnalyticsHub",
            "body": "Would be nice to have a bulk export button for multiple dashboards at once. Not urgent, just a suggestion.",
        },
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "urgency", "op": "in", "value": ["P3", "P4"]},
            ],
        },
    },
    {
        "id": "t1_case_4_sso_integration_issue",
        "input": {
            "ticket_id": "TEST-4",
            "subject": "New employees can't log in via Okta SSO",
            "body": "Since onboarding 5 new engineers this week, they get an error when trying to log in through our Okta SSO. "
                    "Existing employees are unaffected.",
        },
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "matched_kb_docs", "op": "min_len", "value": 1},
                {"field": "category", "op": "in", "value": ["Integration", "Bug", "Onboarding"]},
            ],
        },
    },
    {
        "id": "t1_case_5_llm_judge_response_quality",
        "input": {
            "ticket_id": "TEST-5",
            "subject": "AnalyticsHub dashboard times out",
            "body": "Our main revenue dashboard has been timing out for the last 2 days. It spans about a year of data.",
        },
        "criteria": {
            "type": "llm_judge",
            "question": "Does the draft_response directly acknowledge the customer's specific problem "
                         "(dashboard timeout) rather than a generic acknowledgement? Answer strictly YES or NO.",
        },
    },
    {
        "id": "t1_case_6_adversarial_ambiguous_ticket",
        "input": {
            "ticket_id": "TEST-6-ADVERSARIAL",
            "subject": "not working",
            "body": "it doesn't work please fix",
        },
        "criteria": {
            "type": "rule",
            "checks": [
                # We don't know the "right" category for a ticket this vague —
                # the acceptance criterion is that the system recognises its own
                # uncertainty rather than confidently guessing.
                {"field": "low_confidence_flag", "op": "==", "value": True},
            ],
        },
        "note": "Adversarial: near-content-free ticket. Tests whether the system "
                "flags low confidence instead of fabricating a confident answer.",
    },
]


# ---------- Task 2 test cases ----------

TASK2_CASES = [
    {
        "id": "t2_case_1_known_account_has_output",
        "input": {"account_id": None},  # filled in at runtime with a real ID from accounts.json
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "executive_summary", "op": "min_len", "value": 20},
                {"field": "health_status", "op": "not_empty"},
            ],
        },
    },
    {
        "id": "t2_case_2_risk_flags_have_quotes",
        "input": {"account_id": None},
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "risk_flags_all_have_quotes", "op": "==", "value": True},
            ],
        },
    },
    {
        "id": "t2_case_3_determinism",
        "input": {"account_id": None},
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "deterministic_repeat", "op": "==", "value": True},
            ],
        },
    },
    {
        "id": "t2_case_4_at_risk_account_flagged",
        "input": {"account_id": None, "require_health_status": "At Risk"},
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "risk_flags", "op": "min_len", "value": 1},
            ],
        },
    },
    {
        "id": "t2_case_5_llm_judge_summary_grounded",
        "input": {"account_id": None},
        "criteria": {
            "type": "llm_judge",
            "question": "Does the executive_summary avoid inventing any fact "
                         "(numbers, names, dates) that isn't plausible given a B2B SaaS account brief? "
                         "Answer strictly YES or NO.",
        },
    },
    {
        "id": "t2_case_6_adversarial_missing_account",
        "input": {"account_id": "ACC-DOES-NOT-EXIST"},
        "criteria": {
            "type": "rule",
            "checks": [
                {"field": "raises_error", "op": "==", "value": True},
            ],
        },
        "note": "Adversarial: unknown account_id (simulates the tickets.json / "
                "accounts.json ID mismatch called out in DATA_SCHEMA.md). "
                "Tests graceful, explicit failure rather than a silent wrong answer.",
    },
]
