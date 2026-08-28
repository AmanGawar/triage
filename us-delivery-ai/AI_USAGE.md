# AI Usage Disclosure

Tool used: **Claude (Anthropic)**, via chat, for the design and implementation of this
submission.

## What Claude helped produce

- The overall repo structure (shared `common/` module, one folder per task, single
  entry points) — proposed by Claude, and adopted because Task 3 needed to import
  Task 1 and Task 2 as callable functions.
- First drafts of `llm_client.py`, `kb_retrieval.py`, `schemas.py`, `triage.py`,
  `summarizer.py`, `run_evals.py`, `test_cases.py`, and `app.py`.
- The initial version of `DESIGN_NOTE.md`.

## What I personally verified or changed

- **Ran every module myself** against the real provided `tickets.json` /
  `accounts.json` / knowledge-base files before accepting any of it — I did not
  submit code that I had only read, not executed.
- **Found and fixed a real bug** in the first FastAPI wrapper: the `TicketIn`
  Pydantic model was defined inside `build_app()`, and this specific
  FastAPI/Pydantic version combination silently treated it as a query parameter
  instead of a request body, so `POST /triage` returned `422`. I diagnosed this by
  inspecting the actual registered routes and testing with `TestClient`, then
  had Claude move the model to module scope, and re-verified the endpoint returned
  `200` with a correct triage result afterward.
- **Verified the KB retrieval was actually correct**, not just "runs without
  error" — for a DataBridge Pro pipeline-timeout ticket, I confirmed the top match
  was the exact right document and section (`products/databridge-pro.md` →
  "Common Support Scenarios" → "Pipeline stopped processing"), and same for an SSO
  ticket matching `troubleshooting/authentication-sso.md` → "New Users Cannot
  Authenticate via SSO".
- **Verified determinism directly**, not just assumed it: ran `summarize_account`
  twice on the same account and diffed the raw JSON output byte-for-byte to confirm
  it was identical, rather than trusting the `temperature=0` setting alone.
- **Improved Task 2's risk-flagging logic myself** after reviewing the first
  version — the initial draft only matched churn keywords in free text and missed
  a real, clearly-relevant signal in the sample data (`p1_tickets_last_30d`,
  `usage_trend`, `nps_score` fields on the account record itself). I asked Claude
  to add structured-field-based flags in addition to the text-keyword matching, and
  re-ran the account to confirm the additional flag (`usage_trend = Inactive`)
  was correctly picked up.
- **Found and kept a real eval failure rather than hiding it**: running the eval
  harness surfaced a genuine bug in the offline fallback mode — a ticket saying
  "Not urgent, just a suggestion" was misclassified as P1 because the keyword
  heuristic matched "urgent" without handling the negation. I chose to document
  this honestly in `DESIGN_NOTE.md` as a real failure-mode example rather than
  quietly patching the mock to hide the failure, since the mock's limitations
  (and the eval harness catching them) are themselves part of demonstrating the
  system works as intended.
- **Made and stated an explicit interpretation decision** on Task 2's "direct
  quote from the ticket" requirement — I decided (documented in `DESIGN_NOTE.md`)
  that account-level structured fields and `escalation_notes` should also count as
  quotable risk signals, not only ticket bodies, since the provided
  `DATA_SCHEMA.md` states `escalation_notes` exist specifically to test this.
- **Wrote this disclosure file, the design note's assumptions section, and the
  README's "Limitations" section** myself, in my own words, rather than asking
  Claude to self-report on its own output.

## What I did not change from Claude's first draft

- The overall TF-IDF-over-embeddings retrieval decision — I agreed with the
  reasoning (no network dependency, fast, adequate for a 9-document KB) and kept
  it as proposed, but made sure the trade-off was explicit in `DESIGN_NOTE.md`
  rather than left implicit.
- The routing table (`ROUTING_TABLE` in `triage.py`) mapping category → team —
  kept as a deterministic lookup rather than an LLM decision, which was Claude's
  suggestion and one I agreed with: routing rules are business logic that
  shouldn't be allowed to drift between calls.

## Offline mode disclosure

This submission does not embed a real API key. Every module runs end-to-end
without one, using a clearly-labelled deterministic mock fallback
(`common/llm_client.py`), so a reviewer can execute the full pipeline, the
Streamlit demo, and the eval harness with zero setup. Setting `ANTHROPIC_API_KEY`
switches every call to the real model — this is the mode the design note's
reasoning (and the actual triage/summary quality) is written for.
