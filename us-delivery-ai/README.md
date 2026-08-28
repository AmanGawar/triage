# US Delivery Internship — Task Round Submission

Production-grade AI tooling for Technical Support & TAM teams: an intelligent
ticket triage agent, a TAM account health summariser, and an evaluation harness
for both.

**Time spent:** ~4 hours (in line with the stated timebox).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY for real LLM output
```

No API key required to run and evaluate this submission — see "Offline mode" below.

## Single entry-point run command

```bash
python run_demo.py
```

This runs Task 1 on a sample ticket, Task 2 on a sample account, then Task 3's
full eval suite, printing everything to the console and writing
`eval_report.json` / `eval_report.md` to the repo root.

## Sample run — Task 1 (ticket triage)

Input:
```json
{
  "subject": "Production DataBridge Pro pipeline down, 200 users affected",
  "body": "Our main ingestion pipeline stopped processing 20 minutes ago. Getting ERR_CONNECTION_TIMEOUT after 30s. This is production and blocking our whole team."
}
```

Output (abridged):
```json
{
  "category": "Bug",
  "urgency": "P1",
  "matched_kb_docs": [
    {"doc_path": "products/databridge-pro.md", "section": "Common Support Scenarios"}
  ],
  "recommended_team": "Tier-2 Engineering",
  "confidence": 0.55
}
```
Verified: the top KB match is the exact right document/section
(`products/databridge-pro.md` → "Pipeline stopped processing"), confirmed by hand
against the source markdown, not just assumed from the score.

Run it directly:
```bash
python -m src.task1_triage.triage
```

Or via the REST API:
```bash
uvicorn src.task1_triage.triage:build_app --factory --reload
# then: curl -X POST localhost:8000/triage -H "Content-Type: application/json" \
#   -d '{"subject":"...", "body":"..."}'
```

## Sample run — Task 2 (account health brief)

```bash
python -m src.task2_summarizer.summarizer
```

Produces a 3-section brief (executive summary, risk flags with direct quotes,
talking points) for the first account in `accounts.json`. Determinism was
verified directly: running the same account twice and diffing the raw JSON output
byte-for-byte confirmed identical results, not just assumed from `temperature=0`.

## Sample run — Task 3 (eval harness)

```bash
python -m src.task3_evals.run_evals
```

Writes `eval_report.json` and `eval_report.md`. Latest run: **11/12 cases passed
(92%)** in offline mock mode — see "A real failure we found and kept" below for
the one that failed and why that's a good thing, not a bug we hid.

## Interactive demo (bonus, +5)

```bash
streamlit run app.py
```

Three tabs: Ticket Triage, Account Health Brief, and a live Eval Report runner —
usable by a non-technical TAM without touching code or JSON.

## Approach

- **Task 1** — TF-IDF retrieval (scikit-learn) over the knowledge base, chunked on
  `---` boundaries per `DATA_SCHEMA.md`'s own recommendation, feeds an LLM prompt
  that returns strict JSON validated against a Pydantic schema. Routing
  (category → team) is a deterministic lookup table, not an LLM decision — see
  `DESIGN_NOTE.md` for why.
- **Task 2** — Risk-flag detection is rule-based first (checked against both
  ticket text *and* structured account fields like `usage_trend`,
  `p1_tickets_last_30d`, `nps_score`), with the LLM used only to write the
  executive summary and talking points around those already-determined flags.
  This split is what makes determinism achievable: the LLM's one creative task
  (the summary) runs at `temperature=0`, and everything structural around it is
  pure code.
- **Task 3** — Every test case calls the *real* Task 1 / Task 2 functions (not
  mocked versions of them), mixing rule-based checks (schema/field assertions)
  with LLM-as-judge checks (subjective quality questions), always via a separate
  LLM call from the one that produced the output being graded.

## Media/data selection choices

- **Knowledge base:** all 9 provided markdown docs were indexed — the KB is
  small enough that "selecting" a subset would just mean withholding coverage.
  What *was* deliberately controlled is chunk granularity: splitting on `---`
  and `##` boundaries so retrieval returns a focused section (e.g. one specific
  troubleshooting scenario), not a whole multi-thousand-word document.
- **Tickets/accounts:** Task 2 filters to the last 90 days per the schema's own
  guidance, using the provided `get_account_tickets` pattern from
  `DATA_SCHEMA.md` directly.

## A real failure we found and kept

Running the eval harness surfaced a genuine bug in the *offline mock fallback*:
a ticket saying "**Not urgent**, just a suggestion" was misclassified as P1,
because the mock's keyword heuristic matched the substring "urgent" without
handling the negation. We chose to leave this failing in the eval report rather
than quietly patch the mock to look better — see `DESIGN_NOTE.md`'s "Failure
modes" section for the full writeup, since this is exactly the class of bug a
real LLM call (not a keyword shortcut) is meant to avoid.

## Offline mode

No API key is embedded anywhere in this repo. Every command above runs
end-to-end with **zero setup**, using a clearly-labelled deterministic mock in
`src/common/llm_client.py` (visible in every output as `"_mock": true` internally,
and as a visible warning banner in the Streamlit UI). Set `ANTHROPIC_API_KEY` in
your `.env` to switch every call to the real Claude model — this is the mode the
design note's reasoning about quality is written for.

## Limitations (stated plainly, not buried)

- TF-IDF retrieval is lexical, not semantic — see `DESIGN_NOTE.md`'s latency/quality
  section for why this was still the right call at this KB size, and what would
  change at scale.
- The offline mock is a keyword heuristic, not a stand-in for real classification
  quality — its purpose is making the pipeline runnable without credentials, not
  demonstrating triage accuracy. The design note's quality claims assume
  `ANTHROPIC_API_KEY` is set.
- The Task 2 "direct quote from the ticket" requirement was interpreted to also
  include account-level structured fields and `escalation_notes`, not only ticket
  bodies — stated explicitly, with reasoning, in `DESIGN_NOTE.md`.
- No frontend auth, no persistence layer, no production deployment — out of scope
  per the brief.

## Full design note

See [`DESIGN_NOTE.md`](DESIGN_NOTE.md) for failure modes, the latency/quality
trade-off, PII handling, and scaling analysis (Task 4).

See [`AI_USAGE.md`](AI_USAGE.md) for what Claude helped produce versus what was
personally run, verified, debugged, or changed.

## Repo structure

```
.
├── README.md                  (this file)
├── DESIGN_NOTE.md              (Task 4)
├── AI_USAGE.md
├── requirements.txt
├── .env.example
├── run_demo.py                 (single entry-point command)
├── app.py                      (Streamlit bonus demo)
├── eval_report.json / .md      (generated by run_demo.py / run_evals.py)
├── data/
│   ├── tickets.json
│   ├── accounts.json
│   ├── DATA_SCHEMA.md
│   └── knowledge-base/{products,troubleshooting,billing,onboarding}/*.md
└── src/
    ├── common/
    │   ├── llm_client.py        (Anthropic call + offline deterministic mock)
    │   ├── kb_retrieval.py      (chunking + TF-IDF index)
    │   └── schemas.py           (shared Pydantic models)
    ├── task1_triage/triage.py   (triage_ticket() + FastAPI app)
    ├── task2_summarizer/summarizer.py  (summarize_account())
    └── task3_evals/
        ├── test_cases.py
        └── run_evals.py
```
