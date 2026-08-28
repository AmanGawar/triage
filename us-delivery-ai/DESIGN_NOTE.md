# Design Note

## Failure modes (top 3)

**1. Retrieval mismatch — the LLM classifies confidently against the wrong KB doc.**
TF-IDF retrieval matches on keyword/phrase overlap, not true semantic meaning. A ticket
that describes a symptom in unusual wording (e.g. "the numbers look wrong" instead of
"data mismatch") may retrieve a low-relevance or irrelevant KB chunk, and the LLM may
still write a confident-sounding response around it.
*Detect:* log the `relevance_score` of matched docs; anything below a threshold
(e.g. 0.05, which we already filter on) should visibly warn the agent that the KB
match is weak, not hide it. *Mitigate:* surface `relevance_score` in the UI (done —
see the Streamlit "Matched knowledge-base evidence" panel) so a human agent can judge
whether to trust the citation, and consider a hybrid retriever (TF-IDF + embeddings)
at scale (see Scaling below).

**2. Ambiguous or low-content tickets get a confident, made-up classification.**
Our own eval harness caught a version of this directly: a near-empty adversarial
ticket ("it doesn't work please fix") needs the system to say "I'm not sure" rather
than fabricate a specific category/urgency. We handle this today via
`low_confidence_flag` and a `confidence` score, and test it as an explicit adversarial
eval case. *Detect:* track the rate of `low_confidence_flag=True` over time — a rising
rate might indicate ticket quality is dropping, not just that the model is being
appropriately cautious. *Mitigate:* route low-confidence tickets to a human triage
queue instead of auto-assigning them.

**3. Negation and qualifier blindness in lightweight heuristics.**
Our own offline fallback mode (used when no LLM API key is present) demonstrated this
concretely during eval: a ticket saying "**Not urgent**, just a suggestion" was
misclassified as P1 because the keyword matcher saw "urgent" without handling the
negation. A real LLM call handles this correctly because it reasons over the whole
sentence, but this is a good example of exactly the kind of silent failure a purely
keyword/rule-based layer can introduce — worth remembering before ever "simplifying"
part of the pipeline back to keyword rules for cost reasons. *Detect:* the eval
harness's `t1_case_3` case exists specifically to catch this class of bug — it failed
once already, on the mock, which is the harness doing its job. *Mitigate:* never let
a keyword-only path make the final urgency call in production; the LLM call is the
source of truth, with the mock existing purely so the rest of the pipeline is runnable
without credentials.

## Latency vs. quality trade-off

We chose TF-IDF (scikit-learn) over a hosted embedding API for knowledge-base
retrieval. This is faster (no network round-trip, no rate limit) and free, and for a
9-document KB it retrieves the right document reliably (verified in testing — see
README "Sample runs"). The trade-off: TF-IDF only catches lexical/keyword overlap, not
true paraphrase-level semantic similarity, so it will miss KB matches where the
customer's wording shares no vocabulary with the doc.

**If latency were the hard constraint** (which it already effectively is here): we'd
keep TF-IDF, since it is faster than an embedding call, not slower. If instead *quality*
were the hard constraint and latency could flex, we'd swap to a real embedding model
+ FAISS/ChromaDB (as used in prior RAG work) for genuine semantic retrieval, accepting
the added embedding-API latency per ticket.

## Data sensitivity (PII)

Ticket bodies and account escalation notes may contain customer names, account
details, and business-sensitive information (e.g. "considering competing vendor
evaluation"). Our design sends this data to an external LLM API (Anthropic) as part
of the triage/summary prompt — which is a real exposure surface worth naming
explicitly rather than glossing over.

Mitigations implemented or recommended:
- All data used in this assessment is synthetic, per the brief — no real customer
  PII is ever sent, by construction of the task.
- In a real deployment: redact or tokenize obvious PII patterns (emails, phone
  numbers, names matched against a customer directory) before constructing the
  prompt, and only send the minimum fields needed for the specific task (Task 1
  does not need `arr_usd` or `primary_contact`, for example — payload is already
  scoped to just subject/body).
- `.env.example` never contains a real key, and `ANTHROPIC_API_KEY` is read only
  from the environment, never logged or written to the eval report.
- For a regulated environment, this would call for a self-hosted or VPC-isolated
  model rather than a public API endpoint for any field containing real PII.

## Scaling: 10× ticket volume

What breaks first, in order:
1. **TF-IDF re-fitting cost** — the current implementation builds one TF-IDF matrix
   over the KB at startup (fine — KB size doesn't grow with ticket volume), so this
   specifically does *not* break with more tickets. Good — it means our retrieval
   layer already scales with ticket volume by construction.
2. **LLM API throughput/rate limits** — 10× ticket volume means 10× LLM calls
   (2 per ticket if the retry path fires). This is the real bottleneck: sequential
   calls would create a growing backlog. Fix: batch/async calls with a worker queue
   (e.g. Celery + Redis, or a simple async task queue), and cache repeated/similar
   ticket classifications where possible.
3. **The in-memory data load in `summarizer.py`** (`_accounts_cache`, `_tickets_cache`)
   — currently loads the full JSON files into memory once per process. At real
   scale (not 500 tickets but 500,000), this needs to move to an actual database
   with indexed lookups by `account_id`, not a full JSON file held in memory.

## Key assumption stated explicitly

Task 2 asks to "flag any tickets that suggest churn risk... justify each flag with a
direct quote from the ticket." We interpreted "risk signal" to also include
account-level structured fields (e.g. `usage_trend`, `p1_tickets_last_30d`, `nps_score`)
and the account's own `escalation_notes` — not only ticket bodies — since these are
explicitly part of the account data provided and the schema doc states
`escalation_notes` are "designed to test churn-risk signal detection." Where a flag
originates from a structured field rather than a ticket, the "quote" is the literal
field value (e.g. `"usage_trend = Inactive"`) rather than a ticket excerpt, and the
`ticket_id` is marked `ACCOUNT_FIELD:...` or `ESCALATION_NOTE` instead of a real
ticket ID, so it's always traceable which flags came from tickets versus account data.
