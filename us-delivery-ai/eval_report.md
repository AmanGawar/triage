# Eval Report

Generated: 2026-08-27T09:20:59.518783+00:00
Using real LLM: False

**Overall: 11/12 passed (92%)**
- Task 1 pass rate: 83%
- Task 2 pass rate: 100%

| Case | Pass | Score | Note |
|---|---|---|---|
| t1_case_1_clear_p1_bug | ✅ | 1.00 |  |
| t1_case_2_billing_question | ✅ | 1.00 |  |
| t1_case_3_feature_request_low_urgency | ❌ | 0.00 |  |
| t1_case_4_sso_integration_issue | ✅ | 1.00 |  |
| t1_case_5_llm_judge_response_quality | ✅ | 1.00 |  |
| t1_case_6_adversarial_ambiguous_ticket | ✅ | 1.00 | Adversarial: near-content-free ticket. Tests whether the system flags low confidence instead of fabricating a confident answer. |
| t2_case_1_known_account_has_output | ✅ | 1.00 |  |
| t2_case_2_risk_flags_have_quotes | ✅ | 1.00 |  |
| t2_case_3_determinism | ✅ | 1.00 |  |
| t2_case_4_at_risk_account_flagged | ✅ | 1.00 |  |
| t2_case_5_llm_judge_summary_grounded | ✅ | 1.00 |  |
| t2_case_6_adversarial_missing_account | ✅ | 1.00 | Adversarial: unknown account_id (simulates the tickets.json / accounts.json ID mismatch called out in DATA_SCHEMA.md). Tests graceful, explicit failure rather than a silent wrong answer. |