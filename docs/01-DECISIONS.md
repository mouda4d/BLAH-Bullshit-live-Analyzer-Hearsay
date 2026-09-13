# Decisions

Every hard problem, resolved as a short ADR. Format is fixed:
**Context → Decision → Alternatives rejected → Consequences → What would change our mind.**

The last section is the important one. A decision you cannot imagine reversing is not a
decision, it is a belief, and beliefs do not survive hostile questioning.

**Status legend:** `ACCEPTED` = we are building this. `PROVISIONAL` = accepted but resting
on an estimate we have not yet measured; the milestone that measures it is named.

| ADR | Title | Status |
|---|---|---|
| [001](#adr-001-scope--internal-consistency-is-the-core-external-checking-is-a-bounded-second-verifier) | Scope: internal consistency is the core | ACCEPTED |
| [002](#adr-002-from-stream-to-claim--where-we-cut) | From stream to claim: where we cut | ACCEPTED |
| [003](#adr-003-pronouns-and-claims-split-across-utterances) | Pronouns and claims split across utterances | ACCEPTED |
| [004](#adr-004-the-check-worthiness-gate) | The check-worthiness gate | ACCEPTED |
| [005](#adr-005-where-truth-comes-from--three-tiers-none-of-them-the-live-web) | Where truth comes from | ACCEPTED |
| [006](#adr-006-the-latency-budget) | The latency budget | PROVISIONAL (M1) |
| [007](#adr-007-the-transport--redpanda-not-kafka-not-nats-not-http) | The transport | ACCEPTED |
| [008](#adr-008-keys-partitions-ordering-and-run-isolation) | Keys, partitions, ordering, run isolation | ACCEPTED |
| [009](#adr-009-backpressure-and-shedding) | Backpressure and shedding | ACCEPTED |
| [010](#adr-010-event-time-processing-time-and-late-verdicts) | Event time and late verdicts | ACCEPTED |
| [011](#adr-011-claim-identity-and-idempotent-alerting) | Claim identity and idempotent alerting | ACCEPTED |
| [012](#adr-012-how-contradiction-is-actually-detected) | How contradiction is actually detected | ACCEPTED |
| [013](#adr-013-the-gold-set-and-where-the-audio-comes-from) | The gold set and the audio | ACCEPTED |
| [014](#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm) | Confidence vocabulary | ACCEPTED |
| [015](#adr-015-consent-pii-and-retention--as-code-not-as-a-paragraph) | Consent, PII and retention as code | ACCEPTED |
| [016](#adr-016-bounding-asr-bias-so-it-cannot-become-a-discrimination-engine) | Bounding ASR bias | ACCEPTED |
| [017](#adr-017-replay-is-the-evaluation-primitive) | Replay is the evaluation primitive | ACCEPTED |
| [018](#adr-018-why-there-is-a-batch-warehouse-at-all) | Why there is a batch warehouse | ACCEPTED |
| [019](#adr-019-where-the-llm-is-allowed-to-run) | Where the LLM is allowed to run | ACCEPTED |
| [020](#adr-020-slos-and-autoscaling-on-consumer-lag) | SLOs and autoscaling on lag | ACCEPTED |
| [021](#adr-021-two-people-one-co-owned-interface) | Two people, one co-owned interface | ACCEPTED |
| [022](#adr-022-no-workflow-orchestrator-yet) | No workflow orchestrator (yet) | ACCEPTED |

---

## ADR-001: Scope — internal consistency is the core, external checking is a bounded second verifier

### Context

The original framing was: *"both modes are the same pipeline with different consumers and
different reference data."* We were asked to judge that claim rather than accept it.

**It is about 70% true, and the 30% that is false is the expensive 30%.**

What genuinely is shared: audio ingest, ASR, segmentation, the check-worthiness gate,
claim extraction, the canonical `Claim` entity, alert dedup and suppression, replay,
storage layering, observability, and every SLO. That is most of the code and nearly all of
the hard engineering.

What is *not* shared is the verifier, and the two verifiers are not variations on a theme:

| | Internal consistency | External fact-check |
|---|---|---|
| Verification is... | a **join against state we own** | **retrieval against an open world** |
| Ground truth | the transcript itself — definitionally available | contested, incomplete, expensive, often does not exist |
| Latency | 30-100 ms (local kNN + NLI) | 0.5-5 s, high variance |
| Determinism | reproducible under replay | not reproducible unless the corpus is frozen |
| Cost of being wrong | an awkward follow-up question | defamation |
| Does the evidence exist? | **always** | **usually not** — this is exactly what killed Squash |

Calling those "the same pipeline with different reference data" is the kind of statement
that sounds excellent in a pitch and disintegrates in the fourth minute of a Q&A. The
honest version is stronger anyway.

### Decision

**One streaming spine, two verifier implementations behind one `Verifier` interface, and
they are explicitly not co-equal.**

- **Internal consistency (Mode A) is the core product** and is what M0-M4 build. It
  compares each new claim against (a) prior claims by the same speaker in the same
  session, and (b) claims extracted from operator-supplied reference documents (a CV, a
  product fact sheet, a briefing note).
- **External checking (Mode B) is a deliberately bounded second verifier**, built in M6
  against a frozen local corpus, and permitted to say far less than Mode A. See
  [ADR-005](#adr-005-where-truth-comes-from--three-tiers-none-of-them-the-live-web).

The shared thing is the `Claim` entity and the `Verdict` envelope. Same spine, different
organ.

### Alternatives rejected

- **"They're the same, ship both as one feature."** Rejected: it hides the fact that Mode
  B has an unsolved ground-truth problem behind Mode A's working demo. A reviewer will
  find that in minutes and everything else we said becomes suspect.
- **External checking as the core.** Rejected hard. At zero budget with no access to a
  fact-check corpus of meaningful size, this is where the project dies. Squash had Duke's
  resources, a partnership with PolitiFact, and it *still* ran out of ground truth to
  match against. We would spend three months and demo a system that says "unverified" to
  everything.
- **Drop external checking entirely.** Tempting and genuinely defensible. Rejected because
  the second verifier is what *proves* the spine is a spine — it is the thing that
  justifies the backpressure design, the late-verdict design and the `Verifier` interface.
  A pipeline with one consumer is not obviously a pipeline. But it is last in the roadmap
  and first on the [cut list](05-ROADMAP.md#the-cut-list).

### Consequences

- The `Verifier` interface must be defined in M0, before either implementation exists, and
  the fake verifier used in M0 must satisfy it. This is a contract test.
- Mode B's verdict vocabulary is a strict subset of what Mode A can emit, enforced in
  code, not in review. See [ADR-014](#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm).
- We must be able to say the sentence "these are not the same problem" out loud in an
  interview and explain why. That is a feature.
- Mode B's latency profile is 10-50x Mode A's. This is the *reason* the queueing and
  shedding design exists, and we say so.

### What would change our mind

If we found (or could cheaply build) a genuinely dense reference corpus for a narrow
domain — say, every numeric claim in a company's published quarterly reports — then
external checking in *that* domain becomes as tractable as internal consistency, and the
two really would be peers. That is the condition: **verifier tractability is a function of
corpus density, not of architecture.** If corpus density is high, promote Mode B.

---

## ADR-002: From stream to claim — where we cut

### Context

Speech is continuous. Claims are discrete records with a primary key. Something must
decide where one ends and the next begins, and getting it wrong poisons everything
downstream — a claim cut in half is a claim that cannot be verified and may be verified
*wrongly*, which is worse.

Whisper is trained on ~30 s windows and is designed for complete utterances. Feeding it
small chunks produces truncated words and lost context.

### Decision

**Two-level segmentation, with the levels owned by different stages.**

**Level 1 — token confirmation (inside the ASR stage).** We use the **LocalAgreement-2**
policy from [whisper_streaming](https://github.com/ufal/whisper_streaming): run the model
repeatedly on a growing audio buffer and emit a token as *confirmed* only once two
consecutive runs agree on it. This converts a non-streaming model into a streaming one
without retraining anything, and gives us a principled definition of "text that will not
change."

**Level 2 — utterance assembly (a separate stage).** An `Utterance` is closed when the
**first** of these fires:

1. **Silence**, detected by Silero VAD: >= 700 ms of non-speech. *(primary signal)*
2. **Terminal punctuation** emitted by Whisper on a confirmed token (`.`, `?`, `!`).
3. **Hard cap**: 15 s of continuous speech with no other cut. *(a person mid-monologue
   still needs to produce records)*
4. **Speaker change** from diarization.

The `Utterance` is the unit that flows on the log. **The `Claim` is not the `Utterance`.**
Claims are extracted from a *window* of utterances — see
[ADR-003](#adr-003-pronouns-and-claims-split-across-utterances).

### Alternatives rejected

- **Fixed-length audio windows (e.g. every 5 s).** Rejected: cuts mid-word, mid-claim, and
  produces ASR garbage at every boundary. It is the obvious thing and it is the thing that
  makes these systems produce nonsense.
- **VAD silence only.** Rejected: a speaker who does not pause for 40 s produces no records
  for 40 s, and we blow the latency budget without ever being late — we are simply absent.
  Hence the hard cap.
- **Sentence segmentation on the full transcript with a text model.** Rejected for the hot
  path: it requires text that may still change. We do run it in the *batch* layer, where
  the transcript is final, and we use the difference between batch and streaming
  segmentation as an evaluation metric.
- **Let the LLM decide the boundaries.** Rejected: puts a 1 s non-deterministic model in
  front of every audio frame, destroys the latency budget, and makes replay
  non-reproducible.

### Consequences

- The 700 ms endpoint wait is a **fixed, unavoidable cost** in the latency budget and the
  single largest tunable in it. We spend it deliberately and say so in
  [ADR-006](#adr-006-the-latency-budget).
- `Utterance` carries word-level timings (`w`, `t0`, `t1`, `conf`), because claims need to
  point at audio and the UI needs a play button.
- Cut-point behaviour is itself testable: the same fixture must produce the same utterance
  boundaries on every run. This is a golden-file test.
- LocalAgreement means the very last words a speaker says sit unconfirmed until they say
  more or stop. That is correct behaviour, but it must be visible in the UI as "listening"
  rather than silently missing.

### What would change our mind

If a streaming-native ASR model with good English accuracy and a permissive licence
becomes easy to run locally, Level 1 disappears entirely and the endpoint wait can drop
towards 200-300 ms. We would take that immediately — it is the biggest single latency win
available to us. Re-evaluate at M1 and at each subsequent milestone.

---

## ADR-003: Pronouns and claims split across utterances

### Context

Two failure shapes, both common in real speech:

1. **Split claim.** *"We ran three Kafka clusters."* ... *"For about four years."* Neither
   utterance alone is a complete claim.
2. **Unresolved reference.** *"He said it was twelve percent."* Who is "he"? What is "it"?
   Without resolution this is not a claim, it is a fragment that an eager system will
   cheerfully hallucinate a subject for.

LiveFC handles this with an LLM pass that rewrites utterances into self-contained claims.
That is the right general shape. The question is what happens when it *fails*, and LiveFC
does not say.

### Decision

**Extract over a sliding window, and make unresolved references a first-class, non-alerting
state.**

- Claim extraction runs over a window of the **last 3 utterances** by the same speaker plus
  a compact **session entity registry** (the subjects the speaker has already talked about,
  maintained as a small table). The extractor is asked to emit *self-contained* claims.
- The resulting `Claim` records `source_utterance_ids[]` — a claim may legitimately span
  two or three utterances, and the UI highlights all of them.
- **If the extractor cannot resolve a subject or referent, it must say so** by setting
  `flags.subject_unresolved = true` rather than guessing. A claim with that flag is stored,
  is counted in metrics, is visible in the warehouse — and **can never produce an alert.**
  Its terminal verdict is `UNVERIFIED` with `reason_code = UNRESOLVED_REFERENT`.
- We run **no neural coreference model in the hot path.**

### Alternatives rejected

- **A dedicated coreference resolution model** (neural coref in the pipeline). Rejected:
  another model, another 100-300 ms, another failure mode, and its errors are silent. The
  windowed extractor gets most of the benefit and, crucially, can *report its own failure*.
- **Guess the most recent matching entity.** Rejected: this is precisely the heuristic that
  produced Squash's moon-landing/road-permits match. A confident wrong subject is the worst
  output this system can produce.
- **Drop unresolved claims silently.** Rejected: silent drops are invisible in evaluation.
  Everything that enters the pipeline gets a terminal record. See
  [ADR-009](#adr-009-backpressure-and-shedding).
- **Larger window (10 utterances).** Rejected for now: more input tokens means more
  extraction latency, and the marginal claim recovered at utterance 8 is rare. Window size
  is a config value and we will tune it against the gold set, not against intuition.

### Consequences

- `subject_unresolved` rate becomes a headline quality metric and a dashboard panel. If it
  is high, the window is too small or the extractor is too weak — it is a diagnostic, not
  just a flag.
- The entity registry is session state that must be rebuilt on restart. It is derived
  purely from the claim store, so recovery is a query, not a snapshot. Deliberate.
- Extraction input is non-trivially sized (3 utterances + registry), which pushes
  extraction latency up. Accounted for in the budget.

### What would change our mind

If measurement at M3 shows `subject_unresolved` above ~15% of check-worthy utterances, the
windowed approach is not carrying its weight and a dedicated coref model earns its latency.
We would measure before adding it.

---

## ADR-004: The check-worthiness gate

### Context

Most speech is not checkable. Opinions, jokes, hedges, predictions, questions, filler,
politeness. If we run claim extraction on every utterance we spend ~1 s of GPU on
*"yeah, absolutely, that makes sense"* and the queue explodes within a minute of a real
conversation.

The gate has asymmetric costs and they run in opposite directions at different points in
the pipeline, which is the part people get wrong.

### Decision

**A two-stage cascade, recall-biased at the gate, precision-biased at the alert.**

**Stage 1 — deterministic, ~0 ms, kills the obvious.** Pure Python, no model. Rejects an
utterance if it has none of: a number, a date or duration, a named entity, a comparative,
a superlative, or a first-person past-tense experience verb. Also rejects questions,
utterances under 4 words, and known filler patterns. Expected to remove roughly 60-75% of
utterances in conversational speech at essentially zero cost. *(Estimate; measured at M2.)*

**Stage 2 — a small supervised classifier, ~30 ms.** Trained on the
[ClaimBuster dataset](https://zenodo.org/records/3609356) (23,533 sentences from US
presidential debates 1960-2016, labelled non-factual / unimportant-factual /
check-worthy, CC-BY-4.0). Emits `check_worthiness` in [0,1]. We start with logistic
regression over TF-IDF plus the Stage 1 features — **because a linear model on a 23k-row
labelled set is the correct first answer**, it trains in seconds, it is inspectable, and it
gives us a baseline that any fancier model must beat. A distilled transformer is the
upgrade path if and only if it beats the baseline on held-out data.

**Threshold policy:**

- Gate admits at `check_worthiness >= 0.35` — **deliberately low.** The gate is
  recall-biased because everything it admits lands in a *bounded, priority-ordered queue
  that we are already willing to shed from* ([ADR-009](#adr-009-backpressure-and-shedding)).
  Over-admitting costs queue depth, which we manage. Under-admitting costs a claim we never
  knew existed, which we cannot recover.
- The **alert** threshold is separate and high ([ADR-014](#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm)).
  Precision is bought there, not here.

**Every gate decision is emitted** as a `gate.decision.v1` record, including rejections with
their score. Rejections are the only way to measure gate recall.

### Cost of being wrong, in each direction

| | At the gate | At the alert |
|---|---|---|
| **False positive** (admit junk / alarm wrongly) | Costs queue depth and GPU time. Recoverable: shedding absorbs it. | **Catastrophic.** A false accusation destroys trust in the whole system permanently. |
| **False negative** (drop a real claim / stay silent) | **Unrecoverable and invisible** — we never learn the claim existed. | Costs one missed insight. The interviewer is no worse off than without us. |

This asymmetry is the whole reason the thresholds point in opposite directions, and it is
worth being able to say out loud.

### Alternatives rejected

- **LLM-as-gate.** Rejected: ~1 s and a GPU slot to decide whether to spend ~1 s and a GPU
  slot. The gate must be orders of magnitude cheaper than what it gates or it is not a gate.
- **Single-stage classifier, no rules.** Rejected: Stage 1 is free and removes most of the
  volume. Running even a 30 ms model on filler is waste at scale.
- **The hosted ClaimBuster API.** Rejected: a network call in the hot path, an external
  dependency, non-reproducible under replay, and it breaks the "clone and run with no
  accounts" constraint. We use their *dataset*, not their *service*.
- **No gate; extract from everything.** Rejected: measured against a real conversation this
  is a 3-5x increase in extraction load for near-zero additional claims.

### Consequences

- We ship a small training script and a versioned model artifact. `gate_model_version` goes
  on every `Claim`, because a gate change invalidates historical comparisons.
- ClaimBuster is US political debate speech. **Our interview-mode domain is not that
  domain**, and we must say so: the gate will transfer imperfectly and we measure the gap on
  our own gold set rather than quoting ClaimBuster accuracy as if it were ours. This is a
  known, named weakness.
- The gate is a supervised model, which means it is the one place a training-data bias can
  enter the system that is not ASR. It gets a fairness slice in evaluation too.

### What would change our mind

If Stage 1 alone achieves recall > 0.95 on our gold set at an acceptable admit rate, we
delete Stage 2 and the ML dependency with it. **We would consider that an excellent
outcome** and we will check for it explicitly at M2.

---

## ADR-005: Where truth comes from — three tiers, none of them the live web

### Context

This is the question that kills naive versions of this project. Squash is the proof: their
pipeline worked, and the system was useless because **there was not enough ground truth in
existence to match claims against.**

### Decision

**Three tiers of reference data, strictly ordered by how much we trust them and how fast
they are. No live web retrieval in the hot path, ever.**

**T0 — Session state.** *What this speaker already said, in this session.* Cost: zero.
Latency: ~30 ms. Availability: 100%. Dispute: impossible — we have the audio. This is our
core and it exists for free, which is the entire reason [ADR-001](#adr-001-scope--internal-consistency-is-the-core-external-checking-is-a-bounded-second-verifier)
went the way it did.

**T1 — Session reference documents.** Operator-supplied at session start: a CV, an approved
product fact sheet, a briefing note. Ingested through the *same* extraction pipeline into
the *same* `Claim` table, tagged `origin = REFERENCE_DOC`. Cost: near zero. Latency: same as
T0 (it is the same kNN). Trust: whatever the operator says it is (`source_tier` is set by
the operator at upload).

> **This tier is the commercially interesting one** and it is nearly free: "does what the
> adviser said contradict the approved disclosure?" is T0's machinery with a different
> document loaded.

**T2 — The Almanac.** A **frozen, versioned, locally-stored** reference corpus, built by a
batch job, never queried over the network at request time. Contents: a Wikidata subset
restricted to high-confidence numeric and date-valued properties for a bounded entity set;
a curated CSV of a few thousand hand-picked facts with sources; and published fact-check
claims via the ClaimReview schema. **Every row carries `source_url`, `source_tier`,
`as_of`, and `valid_from`/`valid_to`** — it is a slowly-changing dimension, because facts
have effective dates and "the population of X is N" is only true as of a date. See
[ADR-018](#adr-018-why-there-is-a-batch-warehouse-at-all).

**Source trust tiers** (on every Almanac row and every reference doc):

| Tier | Meaning | Example |
|---|---|---|
| `T_PRIMARY` | The subject of the claim is the source | Official statistics agency, company filing, the speaker's own CV |
| `T_REFERENCE` | Curated, editorially-controlled, citable | Wikidata with a sourced reference, published fact-checks |
| `T_WEAK` | Anything else | Never sufficient for a contradiction verdict on its own |

**When sources disagree: we do not adjudicate.** Verdict is `DISPUTED`, both sources shown
with their tiers and dates, confidence capped. Adjudicating source conflicts is a
journalism problem, not a pipeline problem, and pretending otherwise is how you end up
defending a political opinion in a job interview.

**Out-of-band deep check.** An optional, non-hot-path job may hit the live web *after* the
fact and produce a **late verdict** ([ADR-010](#adr-010-event-time-processing-time-and-late-verdicts)),
clearly rendered as "settled later." It is off by default and never blocks anything.

### Alternatives rejected

- **Live web retrieval / a search API in the hot path.** Rejected on four counts: it adds
  0.5-2 s of high-variance latency straight through the budget; it makes replay
  non-reproducible (the web changes); it requires an account, breaking the zero-signup
  constraint; and it introduces an unbounded trust problem — the first result for a
  contested claim is not evidence.
- **A vector database over a large general corpus.** Rejected: this is the "RAG will solve
  it" trap. Retrieval over a general corpus returns *topically similar* text, and topical
  similarity is not evidence. It is exactly Squash's moon-landing/road-permits failure with
  embeddings instead of keywords.
- **Rely entirely on published fact-checks.** Rejected: this is precisely what Squash did,
  and the corpus is far too sparse. It is a T2 *input*, not a strategy.
- **An LLM's parametric knowledge as the source of truth.** Rejected absolutely. No
  provenance, no `as_of` date, no citation, confidently wrong, and unreproducible. If we
  cannot show the user a source, we do not have a verdict.

### Consequences

- The Almanac is small, curated and honest about it. Coverage will be low, and **low
  coverage renders as `UNVERIFIED`, which is a correct and honest output**, not a failure.
  We report Almanac hit rate as a metric rather than hiding it.
- Building the Almanac is a real batch data engineering job: extract, normalise units,
  resolve entities, apply SCD2 effective dating, validate, publish a versioned artifact.
- Reference documents go through the claim extractor, which means **one extraction code
  path for speech and documents**. Nice property; makes the extractor's contract tests
  serve double duty.

### What would change our mind

A high-density domain corpus, freely available, with clean provenance — a company's own
filings, a regulator's product database, a sports statistics dump. In such a domain the
Almanac stops being a token gesture and Mode B becomes genuinely useful. **Corpus density
is the variable to watch.**

---

## ADR-006: The latency budget

### Context

An alert that arrives after the segment ends is worthless. But "real-time" is not a
requirement, it is a vibe. We need a number, a decomposition, and a defence of the number.

**The target is a product judgement, and we label it as such.** We are not going to invent
a cognitive-science citation. The reasoning: conversational speech runs ~150 wpm; a
sentence is ~3-5 s; a speaker typically stays on one topic for 15-30 s before moving on. If
a contradiction surfaces within ~4 s, the interviewer can still ask "sorry, can I go back —
you said earlier..." without derailing the conversation. Past ~10 s the moment is gone and
the alert becomes a post-session note, which is a different, less valuable product.

### Decision

**p95 end-to-end target: 4,000 ms**, measured from `utterance.media_end` (the moment the
speaker stopped talking) to the alert being rendered.

Decomposed budget, GPU profile. **Every number is an estimate until M1 measures it;
estimates are marked and their basis given.**

| # | Stage | p95 budget | Basis |
|---|---|---|---|
| 1 | Capture + frame buffering (500 ms frames) | 250 ms | Arithmetic: frame size plus jitter. Confident. |
| 2 | VAD endpoint wait (700 ms trailing silence) | 700 ms | Fixed by [ADR-002](#adr-002-from-stream-to-claim--where-we-cut). Deliberate spend. |
| 3 | ASR confirmed text (LocalAgreement-2) | 1,200 ms | **Weakest estimate.** whisper_streaming reports ~3.3 s average latency for English on an A40 with large-v2. We extrapolate down for a distilled/small model and a tighter minimum chunk. **Measured at M1.** |
| 4 | Check-worthiness gate (both stages) | 50 ms | Rules ~0 ms; a linear model on TF-IDF is sub-millisecond. Generous. |
| 5 | Claim extraction (LLM, constrained JSON, ~120 output tokens) | 1,000 ms | **Highest variance item.** Small quantised model on GPU with XGrammar-constrained decoding. Measured at M2. |
| 6 | Embed + kNN candidate retrieval (pgvector, n < 2,000) | 30 ms | Trivial at this scale. |
| 7 | NLI rescoring, top-8 pairs, batched | 80 ms | DeBERTa-v3-base (184 M params), batch of 8, GPU. |
| 8 | Verdict assembly, dedup, publish | 20 ms | Local Postgres write plus a produce. |
| 9 | UI delivery (SSE + render) | 100 ms | Localhost. |
| | **Total** | **3,430 ms** | **570 ms headroom (14%) against the 4,000 ms target** |

**The deterministic fast path**, where a numeric or temporal contradiction is detected by
rules and the LLM is skipped entirely: **~2,360 ms**. This path exists precisely so that the
most confident, most legible alerts are also the fastest.

### What falls out of this budget — architecturally

The budget is not a report card, it is a *constraint generator*. These decisions are
consequences of it, not independent choices:

1. **No live web retrieval anywhere in the hot path** — item 5 alone already consumes 29%
   of the budget; a 0.5-2 s network call with unbounded variance cannot fit.
   ([ADR-005](#adr-005-where-truth-comes-from--three-tiers-none-of-them-the-live-web))
2. **No LLM in the gate, and none in contradiction detection** — two more seconds we do not
   have. ([ADR-019](#adr-019-where-the-llm-is-allowed-to-run))
3. **Retrieve-then-rescore, not score-everything** — an NLI pass over all prior claims is
   O(n) model calls per new claim; at n=500 that is minutes.
   ([ADR-012](#adr-012-how-contradiction-is-actually-detected))
4. **Models are resident, never loaded per request** — model load is seconds. This forces
   long-lived services with warm processes, which forces health probes and readiness gates
   that account for warm-up, which shapes the Kubernetes deployment.
5. **The GPU is a contended resource with an explicit budget.** ASR, extraction and NLI all
   want it. VRAM allocation and process placement are a design decision, not an accident;
   if contention shows up in measurement, the gate and NLI move to CPU first.
6. **Extraction is ~20-40x slower than utterance arrival at peak speech rate.** That
   inequality *is* the backpressure requirement.
   ([ADR-009](#adr-009-backpressure-and-shedding))
7. **No synchronous HTTP chains between stages.** A 5-stage synchronous chain multiplies
   tail latency and couples availability. Log-based, at-least-once, idempotent consumers.

### Alternatives rejected

- **"Under 1 second."** Rejected as physically unavailable: item 2 plus item 3 exceed it
  before we have done any thinking at all.
- **"Under 10 seconds."** Rejected as not a product: past the topic window the alert is a
  note, and a note does not need any of this architecture.
- **No target; measure and report.** Rejected. A budget you did not commit to before
  measuring is a description, not a design, and it cannot generate constraints.

### Consequences

- Per-stage latency is instrumented from day one. Every event carries enough timestamps to
  reconstruct the full breakdown, and a Grafana panel shows this exact table live.
- CI publishes a latency report per commit on the CPU profile, so regressions are caught
  even though CI has no GPU. The GPU numbers are measured on the GPU box and committed as a
  dated report.
- **If M1 shows ASR at 2.5 s rather than 1.2 s, we move the public target to 5,500 ms and
  say so in this file.** We would rather revise a published number than quietly miss it.
  That revision, visible in git history, is a better interview artifact than having been
  right first time.

### What would change our mind

Measurement. This ADR is `PROVISIONAL` until M1 and M2 replace items 3 and 5 with measured
p95s from our own hardware.

---

## ADR-007: The transport — Redpanda, not Kafka, not NATS, not HTTP

### Context

The stages need to pass records to each other. The honest default for a five-service local
system is HTTP or a Unix socket, and if that were sufficient, adding a broker would be
exactly the tool-salad signal we are trying to avoid. So: what specifically requires a log?

### Decision

**Redpanda** (Kafka-API-compatible, single binary, no JVM, no ZooKeeper), running as one
container in Compose and one StatefulSet in k3d.

**The specific requirements that force a durable, replayable, partitioned log — and are not
satisfiable with HTTP:**

1. **Replay is our evaluation strategy** ([ADR-017](#adr-017-replay-is-the-evaluation-primitive)).
   We must re-read a historical session from an arbitrary offset and re-process it through a
   new pipeline version. That is the definition of a log. With HTTP we would build a worse
   log inside Postgres and pretend we had not.
2. **Late verdicts require re-reading history** ([ADR-010](#adr-010-event-time-processing-time-and-late-verdicts)).
   A verifier that comes back after the speaker moved on needs the claim stream, not a
   request that timed out.
3. **Backpressure needs a durable buffer with visible depth**
   ([ADR-009](#adr-009-backpressure-and-shedding)). Consumer-group lag is the metric the
   entire ops story is built on, and it is what we autoscale on
   ([ADR-020](#adr-020-slos-and-autoscaling-on-consumer-lag)). HTTP gives us a timeout and a
   500.
4. **Crash recovery without claim loss.** "Kill the ASR container mid-stream and lose
   nothing" is a demo we intend to perform live. Committed offsets make that a property, not
   a hope.
5. **One producer, many independent consumers.** The UI, the archiver, the verifier and the
   evaluation harness all read the claim stream at their own pace. Fan-out without the
   producer knowing or caring.

**Why Redpanda specifically, over Kafka:** identical API and identical semantics, so
everything we learn and demonstrate transfers to a Kafka job — but a single C++ binary with
no JVM and no ZooKeeper/KRaft quorum to babysit, on a laptop that is simultaneously running
Whisper and an LLM on the same GPU. We are trading zero conceptual fidelity for a real
memory saving. It also ships a Schema Registry, which we need
([ADR-021](#adr-021-two-people-one-co-owned-interface)).

### Alternatives rejected

- **Apache Kafka.** Rejected only on footprint and operational weight for a two-laptop dev
  environment. **We are explicit that this is not a semantics argument** — the API, the
  consumer-group model, the offset semantics and the partitioning are the same, which is the
  point. If a reviewer asks "so do you know Kafka?", the answer is yes, and the deployment
  is one image tag away.
- **NATS JetStream.** Genuinely tempting: ~10 MB binary, excellent ergonomics, and it does
  support replay. Rejected because the consumer-group/offset/partition model and its tooling
  (`rpk`, `kcat`, the Connect ecosystem) are what we want to demonstrate and what employers
  ask about, and because Kafka-compatible topics give us a much larger ecosystem of
  off-the-shelf sinks for the warehouse layer. **This is partly a portfolio decision and we
  say so honestly rather than inventing a technical reason.**
- **Redis Streams.** Rejected: consumer groups exist but replay-from-arbitrary-offset
  ergonomics, retention control and tooling are weaker, and we would spend the rest of the
  project explaining the differences.
- **HTTP / gRPC between stages.** Rejected: fails requirements 1, 2, 3 and 4 above. It is
  the right answer for a system without replay or backpressure requirements. Ours has both.
- **Postgres as a queue (`SELECT ... FOR UPDATE SKIP LOCKED`).** Rejected, though it is the
  strongest simple alternative and we would use it in a smaller system. It fails on
  independent multi-consumer fan-out at different offsets, and on making lag a first-class
  observable.

### Consequences

- One more container (~1-2 GB resident with our settings). Budgeted.
- Every consumer must be **idempotent**, because at-least-once is what we get. That is not a
  cost; it is forced discipline that shows up in
  [ADR-011](#adr-011-claim-identity-and-idempotent-alerting).
- We must not put raw audio on the log. **Audio frames go directly from capture to ASR over
  a local socket**; the log starts at `utterance.v1`. Putting 16 kB/s of PCM through the
  broker would dominate its IO and buys nothing, because the source audio is already stored
  as an immutable artifact for replay.
- We inherit Kafka's operational surface: partition counts, retention, compaction,
  consumer-group rebalancing. That is work — and it is *the* work, for a data engineer.

### What would change our mind

If at M4 the broker is the largest contributor to memory pressure on the CPU-only reviewer
profile and nothing else has fixed it, we would ship a `TRANSPORT=nats` implementation
behind the same interface. The producer/consumer boundary is abstracted in `contracts/`
partly to keep that door open.

---

## ADR-008: Keys, partitions, ordering, and run isolation

### Context

Ordering matters in exactly one place and not in others, and paying for ordering where it is
not needed costs parallelism. Separately, replay runs must not contaminate live runs.

### Decision

**Key by `session_id` on every topic.** Per-session ordering is guaranteed; different
sessions process in parallel. This is the right key because **contradiction detection is
session-scoped** — a claim never needs to be compared against another session's claim in
the hot path, which means the session is the natural unit of both state and parallelism.

**Partitions: 6** on `utterance.v1`, `candidate.v1`, `claim.v1`, `verdict.v1`. Chosen as
"comfortably more than the concurrent sessions a single box will ever run, small enough to
be trivial." Not a magic number, and we say so.

**Run isolation via a `run_id` header, not separate topics.** Every record carries a
`run_id` Kafka header. Live runs and replay runs share topics; consumers are configured with
a `RUN_ID` and filter on the header.

- *Why not per-run topics:* topic sprawl, creation/deletion lifecycle, and consumer-group
  churn for something that is genuinely a filter.
- *The cost, stated plainly:* consumers read and discard records from other runs. At laptop
  scale — a few thousand records per session — this is free. **At real scale it would not
  be, and the fix is per-run topics or a dedicated replay cluster.** Knowing which side of
  that line you are on is the actual skill.

**Retention and compaction — the stream/table distinction made concrete:**

| Topic | Cleanup | Retention | Why |
|---|---|---|---|
| `utterance.v1` | delete | 7 d | A stream of facts about what was said. |
| `gate.decision.v1` | delete | 7 d | A stream; needed for gate recall measurement. |
| `candidate.v1` | delete | 24 h | Purely an internal work queue. |
| `claim.v1` | delete | 7 d | A stream of immutable extracted claims. |
| `verdict.v1` | delete | 7 d | A stream; a claim may receive several verdicts over time. |
| `alert.v1` | **compact** | infinite | **A table.** Keyed by `alert_id`; the latest record is the current state of that alert. This is a changelog, and the UI materialises it. |

`alert.v1` being a compacted changelog while everything upstream is an append-only stream is
the cleanest illustration in the system of stream-vs-table, and it is not decoration: alerts
genuinely have mutable state (`restated_count`, confidence upgrades, suppression) and
everything else genuinely does not.

### Alternatives rejected

- **Key by `claim_id`.** Rejected for the main topics: destroys per-session ordering, which
  the verifier needs to guarantee "compare only against claims that came earlier."
- **Key by `speaker_id`.** Rejected: speaker identity is a diarization cluster label that can
  change mid-session as clustering refines. A key must be stable. This is a real trap.
- **One partition.** Rejected: it would work today and teaches nothing about the actual
  problem.
- **Per-run topics.** Rejected as above, with the conditions for reversal stated.

### Consequences

- Diarization label instability must be handled explicitly: the `speaker_id` on an utterance
  can be *revised*, and a revision is a new record, never an in-place update. Downstream must
  tolerate it.
- Replay consumers must be careful to filter before committing offsets, or they will silently
  skip live records. This is a contract test.

### What would change our mind

More than ~6 genuinely concurrent sessions, or replay volume large enough that filtering
waste shows up in consumer lag. Both are measurable; both are on a dashboard.

---

## ADR-009: Backpressure and shedding

### Context

Claim extraction is ~1,000 ms ([ADR-006](#adr-006-the-latency-budget)). At a normal speaking
rate a speaker produces an utterance roughly every 3-6 s, of which perhaps 30% pass the gate
— so in steady state we are fine. But steady state is not the interesting case. A dense
monologue full of statistics, a replay running at 4x, two sessions at once, or a GPU
contended by ASR all push arrival above service rate. **Verification is slower than
transcription and always will be.** The queue is not an accident, it is the design.

### Decision

**A bounded priority queue with an explicit, configured, observable shedding policy — and
every shed decision produces a record.**

**Priority** for each candidate, computed at admission:

```
priority = check_worthiness * w1  +  recency * w2  +  novelty * w3
```

where `novelty` is `1 - max_cosine_similarity_to_existing_claims` (a restatement of
something we already have is worth less than something new), and `recency` decays with
media time (an old claim's alert is less useful). Weights are config, tuned against the gold
set, and versioned.

**Load levels, with the controller's action at each:**

| Level | Trigger (consumer lag) | Action |
|---|---|---|
| `GREEN` | lag < 10 candidates | Normal. Full LLM extraction, all verifiers. |
| `AMBER` | lag >= 10 | Raise the gate threshold 0.35 -> 0.60. Emit `gate.decision` with `reason=LOAD_AMBER`. |
| `RED` | lag >= 30 | **Deterministic fast path only.** Skip LLM extraction; extract only rule-matchable numeric/temporal claims. Skip Mode B verification entirely. |
| `BLACK` | lag >= 60 or queue full | Shed by priority, lowest first. **Emit a terminal `verdict` with `status=UNVERIFIED, reason_code=SHED_LOAD` for every shed candidate.** |

**The non-negotiable rule: we never silently drop anything.** A shed candidate gets a
terminal verdict record exactly like a verified one. Three reasons, and the third is the one
that matters:

1. The UI can render "not checked — system was overloaded" instead of implying it checked
   and found nothing. Silence is a lie the user cannot detect.
2. Replay and evaluation stay sound: `claims_in == terminal_verdicts_out` is an invariant we
   assert in CI and monitor in production (SLO-5).
3. Shedding becomes *measurable*. `shed_rate` is a dashboard panel and an SLI. A system that
   drops work invisibly cannot be tuned.

**Who decides:** a `LoadController` component reading consumer-group lag from the broker,
with thresholds in config. **Its level transitions are themselves events on the log**, so a
replay reproduces the same degradation, and a post-mortem can answer "why did it go quiet at
14:32?"

### Alternatives rejected

- **Unbounded queue.** Rejected: converts a throughput problem into an unbounded-latency
  problem and eventually an OOM. Verdicts arriving 90 s late are worse than no verdicts,
  because they arrive labelled as if they were timely.
- **Drop oldest (FIFO eviction).** Rejected: the oldest candidate may be the most
  check-worthy. Priority is the whole point.
- **Block the producer (no shedding).** Rejected: the producer is ASR, and blocking ASR means
  losing audio, which is unrecoverable. **Backpressure must not propagate past the point
  where data can no longer be re-read.** The log absorbs it instead.
- **Autoscale only, no shedding.** Rejected: on a fixed two-laptop budget there is nothing to
  scale into. We do both — scaling first ([ADR-020](#adr-020-slos-and-autoscaling-on-consumer-lag)),
  shedding when scaling has run out of room. Having only one of the two is the common mistake.

### Consequences

- `verdict.v1` must carry `status=UNVERIFIED` with a `reason_code` enum. Designed into the
  contract from M0, not retrofitted.
- The UI has three visual states, not two: alerted, checked-and-clear, and **not checked**.
  Most systems have two and quietly conflate the third with the second.
- Overload is a **demo**, not an incident: feed a session at 4x and narrate the degradation.
  See [`07-DEMO-AND-INTERVIEW.md`](07-DEMO-AND-INTERVIEW.md).

### What would change our mind

Nothing about the shape. The thresholds are all config and will be tuned by measurement. If
we ever built this on elastic infrastructure, `BLACK` would become much rarer — but it would
still need to exist, because a spend limit is just a slower queue limit.

---

## ADR-010: Event time, processing time, and late verdicts

### Context

A claim is made at media time 00:03:12. Extraction, verification and (in Mode B) an
out-of-band deep check may deliver a verdict at wall-clock times ranging from 3 s to several
minutes later. Rendering a late verdict as though it were live is dishonest; discarding it
wastes real information.

### Decision

**Two clocks on every record, one derived metric, and a UI that distinguishes them.**

- `media_time_ms` — **event time**. Position within the session's audio. Monotonic,
  reproducible, identical across replays. This is the join key for anything temporal.
- `ingest_ts` / `decided_ts` — **processing time**. Wall clock. Used only for latency
  measurement and never for logic.
- `verdict_lag_ms = decided_ts - utterance_end_wallclock` — the derived SLI, and the number
  on the dashboard.

**Three presentation bands, by `verdict_lag_ms`:**

| Band | Lag | Rendered as |
|---|---|---|
| `LIVE` | <= 8,000 ms | A live alert in the main panel. Actionable now. |
| `SETTLED` | 8 s - 5 min | Moved to a "settled later" side panel, anchored to its transcript position, which gets a marker. Not a pop-up. |
| `ARCHIVAL` | > 5 min | Session report only. Never interrupts. |

**Watermark:** the minimum `media_time_ms` across all in-flight (admitted, unverified)
candidates. It answers exactly one question — *"is everything up to media time T fully
decided?"* — which the UI needs to draw a "checked up to here" line, and the session-close
logic needs to know when it is safe to finalise.

**We deliberately do not build windowed aggregation, and therefore do not need the heavy
watermark machinery** of a stream processor. Our watermark is a `MIN()` over a small table
of in-flight work. Saying "we did not need Flink's watermarks and here is why" is a
better answer than having imported Flink.

### Alternatives rejected

- **Processing time only.** Rejected: replay would produce different results every run, which
  destroys [ADR-017](#adr-017-replay-is-the-evaluation-primitive).
- **Discard late verdicts.** Rejected: a deep check that returns in 45 s is genuinely useful
  in the session report, and discarding it means the expensive work bought nothing.
- **Render everything the same way.** Rejected: an alert about something said two minutes ago
  popping up as "live" makes the user distrust every alert, including the good ones.
- **Apache Flink / Kafka Streams for event-time processing.** Rejected: we have no windowed
  aggregations, no session windows, no joins over time ranges. A `MIN()` query is the whole
  requirement. Importing a stream processor to get a feature we would not use is the
  clearest possible tool-salad signal.

### Consequences

- Every stage must take its clock via injection, never `datetime.now()` inline. Enforced by a
  lint rule, because it will otherwise be violated within a week.
- The UI needs a session timeline component that can anchor annotations at media positions —
  modest work, and it is what makes the "click to replay the audio" feature possible.
- Session close is a real state transition with a real condition (`watermark >= session_end`),
  not "the file ran out."

### What would change our mind

If we added any genuinely windowed feature — "claims per minute," "topic drift over a rolling
5-minute window" — the watermark story gets harder and a real stream processor starts to earn
its place. We have no such feature and no plans for one.

---

## ADR-011: Claim identity and idempotent alerting

### Context

People repeat themselves, especially under pressure, and especially when defending something
they just said. A candidate may restate "four years of Kafka" three times in ninety seconds.
Three alarms for one contradiction makes the tool unusable — and at-least-once delivery from
the broker means even a *single* claim can be processed more than once. Both must produce one
alert.

### Decision

**Three distinct identifiers, doing three distinct jobs. Conflating them is the bug.**

| Identifier | What it is | Job |
|---|---|---|
| `claim_id` | ULID, unique per extraction event | Addresses *this specific utterance of this claim*. Two restatements are two `claim_id`s. Sortable by time, which is useful. |
| `claim_fingerprint` | `sha256(canonical_form)` where canonical form is `subject \| predicate \| object \| normalised_value \| unit \| polarity \| time_scope`, lowercased and lemmatised | Answers *"is this the same assertion as that one?"* Two restatements share a fingerprint. |
| `alert_dedup_key` | `sha256(session_id \| sorted(fingerprint_a, fingerprint_b) \| verifier)` | Answers *"have we already told the user about this conflict?"* Sorted, so A-vs-B and B-vs-A collide by construction. |

`alert_id = uuid5(NAMESPACE, alert_dedup_key)` — **deterministic**, so reprocessing the same
input produces the same alert id and the compacted `alert.v1` topic collapses duplicates
naturally. Idempotency falls out of the key design rather than being enforced by a lock.

**Alert lifecycle:**

1. First time a dedup key is seen: emit alert, `version=1`, `restated_count=1`.
2. Same dedup key again: **do not alert.** Increment `restated_count`, bump `version`, emit
   the updated record to the compacted topic. The UI badge ticks; nothing pops up.
3. Confidence materially increases (crosses a band boundary): emit `version+1` with the new
   confidence and a subtle UI update. **Same `alert_id`** — an upgrade, not a new alert.
4. Suppression: `suppressed_until_ts` on the alert record. Even a version bump will not
   re-notify inside the window (default 120 s, config).

**The dedup key deliberately includes `verifier`.** If both the internal verifier and the
Almanac flag the same claim, those are two genuinely different statements to the user
("you contradicted yourself" vs "this conflicts with source X") and both should be shown.

### Alternatives rejected

- **`claim_id = hash(text)`.** Rejected: exact text matching fails on "four years" vs "4
  years" vs "about four years," and it destroys the ability to point at a *specific* moment
  in the audio — which is the feature.
- **One identifier for everything.** Rejected: it is the direct cause of either "three alarms
  for one claim" or "cannot click through to the second occurrence." The three jobs are
  genuinely different.
- **Dedup in the UI layer.** Rejected: the UI is one consumer among several. Dedup belongs
  where identity is defined, and it must survive a UI reload.
- **Time-window dedup only ("one alert per claim per 5 minutes").** Rejected as a heuristic
  standing in for identity. It also fails the opposite way: two genuinely distinct
  contradictions 30 s apart would be suppressed.

### Consequences

- Canonicalisation is real, fiddly work: number normalisation ("four" -> 4, "a couple" -> ~2
  with a range flag), unit normalisation, lemmatisation, negation detection. **It is pure
  deterministic code, fully unit-testable, and it is where a surprising amount of the
  system's quality lives.** It gets a proper test suite with a table of tricky cases.
- `claim_fingerprint` collisions are a real risk in the other direction: over-aggressive
  canonicalisation merges genuinely different claims. Measured on the gold set as a named
  metric.
- Alert versioning means the UI subscribes to a changelog, not an event feed. Correct, and
  it is why `alert.v1` is compacted ([ADR-008](#adr-008-keys-partitions-ordering-and-run-isolation)).

### What would change our mind

If fingerprint collisions turn out to dominate our error budget, we would add a cheap
embedding-similarity check as a second condition for fingerprint equality — same fingerprint
*and* cosine > 0.9. We would rather measure first.

---

## ADR-012: How contradiction is actually detected

### Context

This is the engine. Get it wrong and the system is Squash — a working pipeline producing
absurd matches, because "these two texts share words" is not "these two texts conflict."

Two hard constraints shape the answer. First, **the naive algorithm is O(n^2) model calls**:
comparing each new claim against all n prior claims with a cross-encoder at n=500 is 500
model calls per claim, which is minutes, not milliseconds. Second, our budget
([ADR-006](#adr-006-the-latency-budget)) allows **110 ms** for the entire detection step.

### Decision

**A three-stage cascade: deterministic rules first, retrieve-then-rescore second, LLM only
to explain — never to decide.**

**Stage A — deterministic contradiction rules (~5 ms, highest confidence).** Operating on the
canonical form from [ADR-011](#adr-011-claim-identity-and-idempotent-alerting). Two claims
conflict if they share `(subject, predicate)` and their values are incompatible:

- **Numeric conflict.** Same attribute, non-overlapping values accounting for stated
  precision. *"about four years"* vs *"eighteen months"* — the ranges do not intersect.
- **Polarity conflict.** Same assertion, opposite polarity. *"I ran Kafka in production"* vs
  *"I have never operated Kafka."*
- **Temporal impossibility.** Overlapping exclusive time scopes. *"I was at Acme 2019-2023"*
  vs *"I was at Globex 2020-2022"* where the role type is exclusive.
- **Cardinality conflict.** *"three clusters"* vs *"a single cluster."*

These produce the best alerts in the system: fast, explainable in one sentence, and
**reproducible under replay with zero variance**. They are also the [fast
path](#adr-006-the-latency-budget) that skips the LLM.

**Stage B — candidate retrieval, then precise rescoring (~110 ms).** This is the standard
information-retrieval two-phase pattern and it is the answer to the O(n^2) problem:

1. **Retrieve** the top 8 prior claims by cosine similarity over sentence embeddings
   (`all-MiniLM-L6-v2`, 22 M params, ~30 ms including the query embedding) from `pgvector`,
   scoped to `session_id` and `speaker_id` and restricted to `media_time < current`.
   Cheap, approximate, high recall.
2. **Rescore** those 8 pairs with an **NLI cross-encoder** (`cross-encoder/nli-deberta-v3-base`,
   184 M params, ~90% accuracy on MNLI-mismatched), batched in a single GPU call (~80 ms).
   It emits `P(contradiction) / P(entailment) / P(neutral)` per pair.

**Retrieval is recall-biased; rescoring is precision-biased.** Exactly the same asymmetry as
the gate ([ADR-004](#adr-004-the-check-worthiness-gate)), for exactly the same reason, and it
is worth noticing that the same pattern appears twice — cheap-and-broad followed by
expensive-and-sharp is the shape of nearly every latency-constrained ML pipeline.

**Stage C — explanation only.** If an alert clears the threshold, an LLM may be asked to
write the one-sentence human-readable summary. **It is given the verdict and asked to phrase
it. It is never asked whether there is a contradiction.** If the LLM is unavailable or
disabled, we fall back to a template and the alert is otherwise identical.

**Why an NLI model and not an LLM for the decision:** it is 10x faster, its output is a
calibrated probability we can threshold and tune, it is deterministic under replay, and it
does exactly one task. An LLM here would be slower, unthresholdable, non-reproducible, and
prone to agreeing with the framing of the question.

### Alternatives rejected

- **Lexical / TF-IDF overlap.** Rejected — this is literally the Squash failure mode
  (moon landing matched to road permits because both said "years").
- **Embedding similarity alone as the decision.** Rejected, and this is the subtle one:
  **contradictory sentences are highly similar in embedding space.** *"I ran Kafka"* and
  *"I never ran Kafka"* are near-identical to a bi-encoder. Similarity is a good *retrieval*
  signal and a terrible *decision* signal. That distinction is the single most important
  thing in this ADR.
- **An LLM comparing every new claim to a summary of prior claims.** Rejected: summarisation
  loses the verbatim quotes that make the alert credible, and it puts a ~1 s
  non-deterministic call in the detection path.
- **A knowledge graph with formal consistency checking.** Genuinely attractive and the
  "proper" academic answer. Rejected: it requires reliable open-domain relation extraction
  into a fixed ontology, which is a research project, and it degrades to nothing when
  extraction fails. Our canonical form is a deliberately shallow, pragmatic subset of the
  same idea.
- **Cross-encode against all prior claims.** Rejected on arithmetic. See above.

### Consequences

- We need embeddings on every claim at write time, stored in `pgvector`. At n < 2,000 per
  session this is a trivially fast IVFFlat index — **and it is why we do not need a vector
  database.**
- NLI models are trained on sentence pairs from a different distribution (SNLI/MNLI) than
  conversational claim pairs. **Expect calibration drift.** We measure `P(contradiction)`
  against our gold set and set the threshold empirically rather than trusting 0.5.
- Stage A and Stage B can disagree. Rules win — they are more precise and more explainable —
  but a disagreement is logged as a metric, because a rising disagreement rate means one of
  them is drifting.
- The whole cascade must run with `--no-llm`, and with only Stage A it still produces real,
  useful alerts. That is the honest floor of the system.

### What would change our mind

If measurement shows Stage B's contribution over Stage A is small but its false-positive
contribution is large, we would ship Stage A only and say so proudly. **"We removed the
neural component because the rules were better" is a strong result**, not a retreat.

---

## ADR-013: The gold set and where the audio comes from

### Context

Every quality claim in this project is worthless without a labelled evaluation set, and
building one is the least glamorous and most load-bearing work in the roadmap. We have no
budget for annotation and no access to real interview recordings — which are, by their
nature, confidential personal data we have no right to.

### Decision

**Three corpora with different jobs, none of them requiring us to buy or unlawfully use
anything.**

**G1 — Check-worthiness: the ClaimBuster dataset.** 23,533 sentences from US presidential
debates 1960-2016, human-labelled non-factual / unimportant-factual / check-worthy,
**CC-BY-4.0** via [Zenodo](https://zenodo.org/records/3609356). Free, real, already labelled.
Used to train and evaluate the gate ([ADR-004](#adr-004-the-check-worthiness-gate)).

> A pleasing property: **the same source events have public-domain audio.** US House and
> Senate floor coverage is public domain; C-SPAN permits non-commercial use of its coverage
> of federal government events with attribution. So G1's text labels and our real-audio
> fixtures come from the same domain, which makes the end-to-end story coherent rather than
> stitched together.

**G2 — Contradictions: scripted, recorded by us.** ~20 mock interviews of 10-15 minutes,
scripted with **deliberately planted contradictions of each rule class** from
[ADR-012](#adr-012-how-contradiction-is-actually-detected) (numeric, polarity, temporal,
cardinality), plus **planted near-misses that must NOT alert** — the hard negatives are the
valuable half. Recorded by us and by friends, with written consent, in varied accents where
we can get them. Full control, perfect labels, lawful.

The obvious objection — *"this is synthetic, you tuned the system to your own script"* — is
real and we answer it structurally: **G2 is split into `dev` and `held-out`, the held-out
half is written by one of us and never read by the other, and it is only run at milestone
boundaries.** The split is enforced by directory permissions and CI, not by good intentions.

**G3 — External checking: public political audio.** House/Senate floor and committee
coverage, where claims are dense, numeric, on the record, and about public matters of fact.
Used for Mode B and for measuring ASR on real, non-studio audio.

**Licensing rule, enforced in the repo:** we **do not redistribute third-party audio.**
`fixtures/` contains transcripts, labels, checksums and a `fetch.py` that downloads from the
original source. The repo stays clean, the licence stays respected, and `make demo` still
works offline because **G2 — which we own outright — is the default fixture.**

### Alternatives rejected

- **Hand-label real podcasts.** Rejected: murky licensing, and labelling contradictions in
  unscripted speech is extremely slow — we would get perhaps 50 labels per evening.
- **Generate the gold set with an LLM.** Rejected firmly. Evaluating an LLM-containing
  pipeline against LLM-generated ground truth measures agreement, not correctness, and it is
  the single most common way portfolio ML projects fool themselves.
- **Use only public benchmarks (FEVER, AVeriTeC, CheckThat!).** Rejected as the *primary*
  set: they are text-only, and none of them contain intra-session speaker contradictions,
  which is our core task. Used as secondary comparison points for the gate.
- **Skip the gold set; demo on vibes.** Rejected. It is the difference between this project
  and a tutorial, and it is the thing a senior reviewer will check first.

### Consequences

- Building G2 is a real chunk of the roadmap and gets its own milestone slice, not a footnote.
- Everyone recorded signs a consent form; the forms are referenced (not stored) in the repo
  and the recordings carry consent metadata — see
  [ADR-015](#adr-015-consent-pii-and-retention--as-code-not-as-a-paragraph). **We eat our own
  dog food on the consent gate from day one.**
- ClaimBuster's domain (political debate) differs from our interview domain. Named, known,
  measured — we report gate performance separately on G1 and G2 and never quote the better
  number.
- Accent diversity in G2 is limited by who we know. **We state the actual composition of the
  set in the evaluation report rather than implying coverage we do not have.** See
  [ADR-016](#adr-016-bounding-asr-bias-so-it-cannot-become-a-discrimination-engine).

### What would change our mind

If a public corpus of transcribed multi-turn interviews with annotated contradictions
appears, we would adopt it immediately as the held-out set. We searched; it does not exist
today.

---

## ADR-014: The confidence vocabulary and what is allowed to alarm

### Context

"False" is a word with legal consequences attached. So is the implication of it. Meanwhile a
system that only ever says "possibly, maybe" is useless. The vocabulary is where honesty and
usefulness are traded off, and it must be an enumerated type in code, not a tone of voice.

### Decision

**A closed enum. No free-text verdicts. Ever.**

| `status` | Meaning | May alarm? | Available to |
|---|---|---|---|
| `CONSISTENT` | Checked against available reference; no conflict found | No — quiet annotation | Both modes |
| `CONTRADICTED_INTERNAL` | Conflicts with something **this same speaker** said earlier in this session | **Yes** | Mode A only |
| `CONTRADICTED_BY_DOC` | Conflicts with an operator-supplied reference document (CV, fact sheet) | **Yes** | Mode A only |
| `CONTRADICTED_BY_SOURCE` | Conflicts with an Almanac row, shown with source and `as_of` | Annotation only | Mode B only |
| `DISPUTED` | Reference sources disagree with each other | No — annotation, both sources shown | Mode B only |
| `UNVERIFIED` | We did not or could not check. Carries a `reason_code`. | No | Both |
| `OUT_OF_SCOPE` | Not a checkable claim after all (gate false positive caught downstream) | No | Both |

**There is no `FALSE`. There is no `LIE`. The type system will not let us say it.**

`reason_code` on `UNVERIFIED` is itself an enum: `SHED_LOAD`, `UNRESOLVED_REFERENT`,
`LOW_ASR_CONFIDENCE`, `NO_REFERENCE_COVERAGE`, `EXTRACTION_FAILED`, `BELOW_THRESHOLD`.
Every one of these is a dashboard panel — **the distribution of "why we didn't check" is one
of the most diagnostic things in the system.**

**Alarm thresholds (precision-biased, per [ADR-004](#adr-004-the-check-worthiness-gate)):**

| Condition | Outcome |
|---|---|
| Stage A rule fires, `flags` clean | **ALERT.** Confidence `HIGH`. |
| Stage B NLI `P(contradiction) >= 0.85` and retrieval cosine >= 0.55 | **ALERT.** Confidence `MEDIUM`. |
| Stage B `0.60 <= P(contradiction) < 0.85` | **ANNOTATION.** Appears in the transcript margin. No pop-up, no sound. |
| `< 0.60` | Nothing user-visible. Recorded for evaluation. |
| Any of `subject_unresolved`, `low_asr_confidence`, `hedged` set | **Downgraded one level, always.** An alert becomes an annotation. |
| Mode B, any confidence | **Annotation ceiling.** Mode B can never alarm. |

The thresholds are config, tuned on G2-dev, validated on G2-held-out, and **the chosen
values are published in the evaluation report with the precision/recall they bought.**

**Sources are always shown.** An alert with no visible evidence is not shipped. For
`CONTRADICTED_INTERNAL` the evidence is both verbatim quotes with timestamps and playable
audio; for `CONTRADICTED_BY_SOURCE` it is the source URL, tier and `as_of` date.

**Phrasing is templated, never generated free-form.** *"Possible conflict — at 00:03:12 the
speaker said X; at 00:21:47 they said Y."* Neutral, attributive, quoting. It states what was
said, not what is true, and that distinction is the legal defence.

### Alternatives rejected

- **A single 0-1 "truthiness" score.** Rejected: it collapses "we checked and found a
  conflict" with "we could not check," which are opposite states. The reason code *is* the
  product.
- **Free-text LLM verdicts.** Rejected: unthresholdable, unevaluable, and the one place a
  model could generate a defamatory sentence.
- **Let Mode B alarm.** Rejected. Interrupting a human to assert that a named person's
  statement conflicts with a source, in real time, on an automated judgement, is the highest
  legal exposure in the system for the least incremental value. Annotation is enough.
- **Hide `UNVERIFIED` from the UI.** Rejected: that is the silent-failure trap again. "Not
  checked" must be visually distinct from "checked and clear."

### Consequences

- The UI needs three distinct visual treatments plus a fourth for "not checked," and the
  difference must be legible at a glance.
- Adding a status value is a schema change requiring both owners' approval
  ([ADR-021](#adr-021-two-people-one-co-owned-interface)). Deliberate friction on exactly
  the change most likely to cause harm.
- We will be asked "why not just say it's false?" in an interview. The answer — vocabulary
  is a legal control surface, not a UX preference — is a good answer.

### What would change our mind

Nothing in the portfolio context. A real deployment with a legal team and a human editorial
gate might widen Mode B's vocabulary. That gate would be a person, not a threshold.

---

## ADR-015: Consent, PII and retention — as code, not as a paragraph

### Context

Interview audio is special-category-adjacent personal data about an identifiable person who
is in a position of relative powerlessness. Recording consent law differs by jurisdiction
(two-party consent states in the US; GDPR lawful-basis requirements in the EU/UK, which is
the regime we design to per assumption A8). "We acknowledge privacy is important" in a README
is worth nothing. The mitigations have to be things a reviewer can point at in the code.

### Decision

**Five mechanisms, all enforced by the system rather than by policy.**

**1. The consent gate — the pipeline refuses to start without one.** A session cannot be
created without a `consent` block in its manifest:

```yaml
consent:
  obtained: true
  method: WRITTEN | VERBAL_RECORDED | IMPLIED_PUBLIC_BROADCAST
  jurisdiction: GB
  obtained_at: 2026-09-14T10:00:00Z
  obtained_by: operator@example.com
  subject_informed_of_automated_processing: true   # GDPR Art. 13(2)(f)
  retention_days: 30
```

Missing or malformed, the ingest service returns 422 and no audio is written to disk. **This
is the first thing M0 implements** — before any ML, before the UI. It is 40 lines of
validation and it is the single most persuasive artifact in the repository, because it
proves the ethics section is architecture rather than prose.

**2. Pseudonymisation by default.** Speakers are `SPEAKER_00`, `SPEAKER_01` — diarization
cluster labels, not identities. Mapping a cluster to a real name is a **deliberate operator
action** that writes to an append-only `audit_log` (who, when, why). Nothing in the pipeline
requires a real name to function; identity is an optional presentation-layer join.

**3. Retention with real deletion.** `retention_days` from the manifest drives a scheduled
job that hard-deletes audio, transcripts, claims and derived warehouse rows. Deletion
propagates to the Parquet lake and marts, not just Postgres — **the warehouse is the place
deletion usually silently fails, and a partitioned-by-session layout is chosen partly so that
deletion is a partition drop rather than a rewrite.** Default 30 days.

**4. Subject access and erasure as CLI commands.**
`blah subject export --session S` produces everything held about that session's subject as
JSON plus audio. `blah subject erase --session S --reason "Art. 17 request"` performs the
deletion and writes a tombstone to the audit log. Both have tests asserting that **after
erase, a full-text search over every store returns nothing.**

**5. Purpose limitation in the schema.** Every `Claim` carries `session_mode`
(`INTERVIEW` / `BROADCAST` / `COMPLIANCE`). The warehouse **physically separates** interview
data from broadcast data, and a cross-mode join is rejected by a dbt test. Interview claims
about a private individual can never leak into a public-figure analysis.

### Alternatives rejected

- **A privacy policy document.** Rejected as the *only* mechanism. Documents are not controls.
- **Encrypt everything at rest and call it done.** Rejected: encryption protects against theft,
  not against misuse, and misuse is the actual risk here.
- **Soft deletes.** Rejected: an erasure request is not satisfied by `deleted_at IS NOT NULL`.
- **Ask for consent in the UI at session start.** Rejected as insufficient: the operator is not
  the data subject. The manifest records that consent was obtained *from the subject*, by whom,
  and how — which is the thing that would matter.

### Consequences

- Deletion crossing Postgres, MinIO/Parquet and the marts is real distributed work, and it is
  the reason the lake is partitioned by `session_id`.
- The audit log is append-only and excluded from deletion (it records that deletion happened);
  it contains no claim content, only identifiers and actions.
- The consent gate will annoy us during development. We ship a `fixtures/consent/` set of
  pre-signed manifests for our own recordings rather than adding a bypass flag. **There is no
  bypass flag** — that is the point.

### What would change our mind

Nothing. If anything this is the minimum. A real deployment would add DPIA documentation and
a data processing agreement, which are paperwork we cannot meaningfully produce.

---

## ADR-016: Bounding ASR bias so it cannot become a discrimination engine

### Context

This is the most serious ethical problem in the project and it deserves a blunt statement:

> Commercial ASR systems have been measured at roughly **35% word error rate for African
> American speakers versus 19% for white speakers** on matched content, with the gap driven
> by *acoustic* rather than lexical modelling. Comparable gaps are documented for
> Scottish, Indian, Jamaican and African-accented English. Whisper is better than the 2020
> commercial systems studied but is **not free of this**.

Now compose that with our product. Higher WER means more garbled transcripts, which means
more spurious extracted claims, which means **more false contradiction alerts for speakers
with certain accents**. A hiring tool that flags candidates with some accents as
inconsistent more often than others is not a tool with a bias problem. It is a
discrimination engine with a dashboard, and it would be unlawful in most of the markets we
would want to sell it in.

**This is not a risk to mitigate. It is a constraint that determines what the product is
allowed to output at all.**

### Decision

**Four mechanisms. The first is a product limit, not a technical one.**

**1. Interview mode does not produce assessments — architecturally, not by convention.**
Mode A emits **interviewer prompts**: *"you may want to ask about X"* with both verbatim
quotes, both timestamps and both audio clips. It emits no score, no ranking, no
recommendation, no aggregate "consistency rating." There is **no field in the `Alert` schema
that could carry one** ([`03-DATA-CONTRACTS.md`](03-DATA-CONTRACTS.md)). A downstream
consumer wanting to build a score would have to extend the schema, which requires a PR
through both owners. The human decides; the system surfaces evidence and the audio to check
it against.

> Interrogate this and it holds: the residual harm from a *false* prompt is that an
> interviewer asks one unnecessary clarifying question, having heard the audio themselves.
> The residual harm from a false *score* is a rejected candidate. The distance between those
> two is the entire justification for the design.

**2. ASR confidence gates alerting.** Every `Utterance` carries per-word confidence. A claim
whose source span falls below the configured threshold gets `flags.low_asr_confidence` and is
**downgraded one severity level** ([ADR-014](#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm)):
an alert becomes a quiet annotation. **The mechanism that protects accented speakers is the
same mechanism that protects against noisy audio** — it is not a special case bolted on,
which is why it will not rot.

**3. WER by speaker group is a first-class, published metric with a CI gate.** The evaluation
harness reports WER sliced by the accent groups present in G2 and G3. The gate, in CI:

```
max_group_wer / min_group_wer <= 1.5   →  else the build fails
```

**We fully expect to fail this gate at first.** That is the point of having it — a failing
fairness gate with a published number is infinitely more honest, and more impressive, than a
passing system that never measured. If we cannot pass it, the documented response is to
**narrow the claimed scope of the product**, not to quietly delete the gate.

**4. We publish what our gold set actually contains.** Accent composition of G2 and G3 is
stated in the evaluation report, along with the explicit caveat that two unemployed engineers
recording their friends cannot construct a demographically representative corpus. **An
unmeasured group is reported as unmeasured, never as passing.**

### Alternatives rejected

- **"We acknowledge ASR has bias" in the README, and nothing else.** Rejected — this is the
  standard non-answer and a senior reviewer will read it as one.
- **Ship the assessment feature with a warning label.** Rejected: warning labels do not survive
  contact with a hiring funnel under time pressure.
- **Fine-tune ASR on diverse accents.** Out of scope by constraint (no training) and beyond our
  means; also it treats a product-design problem as a modelling problem.
- **Restrict the product to speakers the system handles well.** Rejected as obviously
  discriminatory in itself.

### Consequences

- A whole class of "impressive" features — candidate scoring, comparison, ranking — is
  permanently off the table. **We consider that a feature of the design and will say so.**
- The fairness gate can block a merge, which will occasionally be inconvenient. Correct.
- This ADR is the strongest single item in the repository for a senior interviewer, because
  it demonstrates the thing most portfolio projects cannot: **choosing not to build the
  impressive thing, for a stated reason, and enforcing that choice in the type system.**

### What would change our mind

A measured WER ratio comfortably under 1.5 across a genuinely representative set would let us
revisit *aggregate* outputs — and even then, not a hiring score. The constraint on scoring is
about the consequence of error, not only its rate.

---

## ADR-017: Replay is the evaluation primitive

### Context

"Is the new extractor better?" is unanswerable without re-running history. Every quality
claim, every threshold, every model swap depends on this, and it constrains storage design
from day one — which is why it is a decision and not a tool.

### Decision

**Two replay modes, a `run_id` on every record, and a diff tool that produces a report.**

- **`replay --from-audio`** re-runs the stored source audio through the entire pipeline
  including ASR. Slower; the only way to evaluate an ASR or segmentation change.
- **`replay --from-transcript`** re-reads `utterance.v1` from the log and re-runs everything
  downstream. Fast (no GPU-bound ASR), and the mode used for the CI evaluation gate.

**What this forces on the rest of the design — the interesting part:**

1. **Source audio is an immutable stored artifact** (MinIO), not a transient stream. This is
   the main justification for object storage.
2. **`run_id` is on every record and in every Kafka header**
   ([ADR-008](#adr-008-keys-partitions-ordering-and-run-isolation)).
3. **No stage may read the wall clock for logic.** Clocks are injected. There is a lint rule.
   Without this, replay is not reproducible and the whole scheme is theatre.
4. **Every model and prompt is version-pinned and its version is recorded on the output
   record** — `asr_model`, `gate_model_version`, `extractor_model`, `prompt_version`,
   `nli_model`, `almanac_version`. A verdict that cannot say what produced it cannot be
   compared against another verdict.
5. **Temperature 0 and fixed seeds** for every model call, so that replay variance is a bug
   rather than expected behaviour.

**`blah diff RUN_A RUN_B`** produces a report: verdicts that changed status, alerts that
appeared or vanished, precision/recall deltas against the gold labels, and per-stage latency
deltas. It is a SQL query over the warehouse ([ADR-018](#adr-018-why-there-is-a-batch-warehouse-at-all)),
which is a large part of why the warehouse exists.

### Alternatives rejected

- **Re-run from the original audio file directly, no log.** Rejected: cannot isolate a
  downstream change from ASR non-determinism, so every experiment confounds two variables.
- **Snapshot outputs as golden files and diff text.** Rejected: works for 3 fixtures, not for
  20 sessions with thousands of claims, and gives no aggregate metrics.
- **Evaluate offline on text only, never replaying the pipeline.** Rejected: it would not
  catch the integration bugs — segmentation drift, ordering, dedup — which is where the real
  defects live.

### Consequences

- Storage grows with every run. `run_id` retention policy: keep the last 10 runs plus any
  tagged `baseline`, delete the rest. A cleanup job, and a small, real data-lifecycle problem.
- The clock-injection rule must be enforced mechanically or it will be violated. Lint rule in
  CI, added in M0.
- **Replay is the demo finale** ([`07-DEMO-AND-INTERVIEW.md`](07-DEMO-AND-INTERVIEW.md)):
  change a threshold, replay, diff, show precision move. It is the most senior-looking thirty
  seconds available to us.

### What would change our mind

Nothing. This is the load-bearing evaluation decision and everything else leans on it.

---

## ADR-018: Why there is a batch warehouse at all

### Context

We have a real-time pipeline. Adding a batch analytics layer needs justification, or it is
resume padding — and "we built a claims data warehouse" is exactly the kind of phrase that
sounds like DE work while being decorative. So: what specifically cannot be answered from the
hot path?

### Decision

**A three-layer storage design, with the batch layer justified by four questions the hot path
genuinely cannot answer.**

| Layer | Technology | Holds | Why |
|---|---|---|---|
| **Hot / serving** | PostgreSQL + `pgvector` | Current session state: claims, embeddings, alerts, entity registry, audit log | Needs concurrent readers/writers, millisecond kNN, transactional dedup. |
| **Lake** | Parquet on MinIO (S3 API), partitioned `mode=/dt=/session_id=` | Every record from every topic, forever (subject to retention) | Immutable, cheap, columnar, replay source, and the partition layout makes GDPR erasure a partition drop. |
| **Marts** | dbt on DuckDB, reading Parquet | Dimensional model + metrics | Analytical queries over many runs and many sessions. |

**The four questions that force this layer to exist:**

1. **"Did this change make the system better?"** — `blah diff` is an aggregate comparison of
   two `run_id`s across thousands of claims. That is a `GROUP BY`, not a stream operation.
   ([ADR-017](#adr-017-replay-is-the-evaluation-primitive))
2. **"What is our alert precision, by pipeline version, over time?"** — the CI quality gate
   needs this as a single number, computed from labelled history.
3. **"What is WER by speaker group?"** — the fairness gate
   ([ADR-016](#adr-016-bounding-asr-bias-so-it-cannot-become-a-discrimination-engine)) is a
   batch aggregation over a labelled corpus. It cannot exist without this layer.
4. **"Has this speaker contradicted themselves across *sessions*?"** — the only genuinely
   cross-session product feature, and it is definitionally out of the hot path's scope.

**The dimensional model** (star schema, because the queries are additive metrics sliced by
descriptive attributes, which is exactly what it is for):

- **Dimensions:** `dim_session` (mode, consent metadata, duration), `dim_speaker` (pseudonymous,
  accent group where labelled), `dim_pipeline_version` (every model and prompt version as a
  single surrogate key — **this is the dimension that makes "compare versions" a join**),
  `dim_claim_type`, `dim_almanac_source` (SCD2: `valid_from`, `valid_to`, `as_of`, because a
  source's stated fact changes over time and a verdict must be judged against what the source
  said *then*).
- **Facts:** `fct_claim` (grain: one extracted claim), `fct_verdict` (grain: one verdict —
  a claim may have several), `fct_alert` (grain: one alert version), `fct_stage_latency`
  (grain: one record's transit through one stage).
- **Marts:** `mart_precision_by_version`, `mart_wer_by_group`, `mart_latency_percentiles`,
  `mart_gate_recall`, `mart_shed_rate`, `mart_unverified_reasons`.

**Data quality is enforced, not assumed.** dbt tests — `not_null`, `unique`, `relationships`,
`accepted_values` on every enum — run in CI. The `accepted_values` test on `verdict.status` is
the mechanical enforcement of [ADR-014](#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm);
if anyone ever emits `FALSE`, the build fails.

**Backfill is a supported operation:** `blah warehouse backfill --from DATE --to DATE` rebuilds
marts from the lake. Needed whenever a mart definition changes, which will be often.

### Alternatives rejected

- **No batch layer; query Postgres directly.** Rejected: mixes analytical scans with the
  serving path that has a 30 ms budget, and Postgres is not where we want thousands of runs of
  history.
- **A real warehouse (Snowflake/BigQuery).** Rejected: costs money, breaks the zero-signup
  constraint. **DuckDB over Parquet is the correct architecture at this scale, not a
  compromise** — and saying that confidently is a better signal than having reached for
  Snowflake.
- **Spark.** Rejected: a JVM cluster for gigabytes. DuckDB will outperform it here and we can
  explain every line.
- **ClickHouse.** Genuinely good for this shape and a reasonable alternative. Rejected on
  footprint — we already run a broker, Postgres, MinIO, three model services and an observability
  stack on laptops, and DuckDB is a library, not a server.
- **Skip dbt; write SQL scripts.** Rejected: we want the lineage graph, the tests and the
  documentation site, and dbt is ~a day to learn. This is the one place where the tool's
  overhead is clearly less than what it provides.

### Consequences

- An archiver consumer writes topics to Parquet. It must be idempotent and handle partial
  files — a real exactly-once-ish sink problem, solved with deterministic filenames and atomic
  rename.
- Small-file proliferation is a genuine issue with streaming writes to Parquet; a compaction
  job merges files per partition nightly. **A classic, real lakehouse problem and worth having
  solved.**
- Two SQL dialects (Postgres, DuckDB). Mild annoyance, accepted.
- The warehouse must honour deletions from
  [ADR-015](#adr-015-consent-pii-and-retention--as-code-not-as-a-paragraph) — which the
  `session_id` partitioning is designed for.

### What would change our mind

If the marts were only ever read by the CI gate and never by a human, dbt would be
over-engineering and three SQL files would do. We expect to read them constantly during
threshold tuning; if after M4 we are not, we should simplify and say so.

---

## ADR-019: Where the LLM is allowed to run

### Context

The constraint is "AI is a component, not the project," and the honest failure mode is that
an LLM quietly becomes the answer to every hard sub-problem, at which point the system is a
prompt with a Docker Compose file around it.

### Decision

**An explicit allowlist. The LLM may run in exactly two places, and the system must work
without it in both.**

| Stage | LLM? | Why |
|---|---|---|
| VAD / endpointing | **No** | Silero VAD, deterministic, 1 ms. |
| ASR | Model, but not an LLM | Whisper family. |
| Check-worthiness gate | **No** | Rules + linear model. Must be ~1000x cheaper than what it gates. ([ADR-004](#adr-004-the-check-worthiness-gate)) |
| **Claim extraction** | **Yes** | Genuinely needs language understanding: turning conversational speech into a structured subject/predicate/value tuple with resolved referents. This is the one place nothing else works. |
| Canonicalisation | **No** | Number/unit/lemma normalisation is deterministic code and must be, because `claim_fingerprint` depends on it. ([ADR-011](#adr-011-claim-identity-and-idempotent-alerting)) |
| Contradiction detection | **No** | Rules + NLI cross-encoder. Faster, thresholdable, reproducible. ([ADR-012](#adr-012-how-contradiction-is-actually-detected)) |
| **Mode B evidence adjudication** | **Yes, bounded** | Deciding whether an Almanac row actually addresses a claim. Output constrained to the enum; cannot invent a source. |
| Alert phrasing | Optional | Template fallback is always present and always sufficient. |
| Anything in the alerting/dedup path | **No** | Must be deterministic for idempotency. |

**Implementation:** Ollama with **JSON-schema-constrained decoding** (Ollama uses XGrammar
under the hood), so the extractor's output is *structurally* guaranteed to match the `Claim`
schema — the grammar makes invalid JSON unrepresentable rather than caught. Content quality
still varies with model size; **structure never does.** Temperature 0, fixed seed,
version-pinned model, `prompt_version` recorded on every output.

**`--no-llm` is a first-class, tested mode, not a degraded curiosity.** With it, extraction
falls back to deterministic pattern matching for numeric/temporal/polarity claims and
contradiction detection runs Stage A only. It catches materially fewer claims — and the ones
it catches are the highest-precision ones. **It runs in CI on every commit, which is how it
stays working.**

An optional `LLM_ENDPOINT` env var swaps Ollama for any OpenAI-compatible API (a free tier,
for demoing on the CPU laptop). **Default is local. A reviewer needs no account.**

### Alternatives rejected

- **LLM for everything ("just prompt it").** Rejected: blows the latency budget by ~4x,
  destroys replay reproducibility, produces unthresholdable outputs, and removes every
  interesting engineering problem from the project — which is to say, removes the project.
- **No LLM at all.** Seriously considered. Rejected because claim extraction with resolved
  referents from conversational speech is genuinely beyond pattern matching, and pretending
  otherwise would make the system much weaker for no gain. **But `--no-llm` exists precisely
  so we can show exactly how much the LLM buys us** — which is a measurement almost nobody
  makes.
- **A hosted API as the default.** Rejected: breaks zero-signup, adds network latency and
  variance to the hot path, and makes replay non-reproducible.

### Consequences

- We must measure and publish the `--no-llm` vs LLM delta on the gold set. **That number is
  one of the most interesting results this project can produce**, in either direction.
- Model choice is a config value. The default must fit in 8 GB VRAM alongside Whisper and
  DeBERTa — a real VRAM budgeting exercise documented in [`04-STACK.md`](04-STACK.md).
- Prompts are versioned files in the repo, reviewed like code, with their own golden tests.

### What would change our mind

If extraction quality with a small local model is poor enough to dominate our error budget,
the answer is **narrowing the extraction task** (more rules, tighter schema, smaller output)
before reaching for a bigger model. Bigger model is the last resort, not the first.

---

## ADR-020: SLOs and autoscaling on consumer lag

### Context

The brief is explicit that the DevOps half is a first-class problem: **the pipeline is the
thing to observe.** Generic container metrics (CPU, memory, restarts) tell us nothing about
whether the system is doing its job. A system can be perfectly healthy by infrastructure
metrics while producing verdicts 40 seconds late.

### Decision

**Five SLOs defined on pipeline semantics, and autoscaling driven by consumer-group lag.**

| SLO | Statement | Window | Why it is the right measure |
|---|---|---|---|
| **SLO-1 Ingest completeness** | >= 99% of speech-active seconds produce a confirmed utterance | per session | Detects ASR silently dying — the failure that looks like "a quiet speaker." |
| **SLO-2 Transcript freshness** | p95 `utterance_lag_ms` <= 1,800 ms | 5 min rolling | The upstream half of the latency budget, isolated. |
| **SLO-3 Verdict timeliness** | p95 `verdict_lag_ms` <= 4,000 ms for claims with `check_worthiness >= 0.7` | 5 min rolling | **The user-facing promise.** Scoped to claims that matter, so shedding low-priority work does not mask a real breach. |
| **SLO-4 Verdict completeness** | 100% of admitted candidates receive exactly one terminal verdict | per session | **The best one.** A conservation law: `claims_in == terminal_verdicts_out`, including `SHED`. Catches every silent-drop bug, and it is asserted in CI and monitored at runtime. |
| **SLO-5 Alert precision** | >= 0.90 on the held-out gold set | per release | A release gate, not a runtime SLO. Blocks the merge. |

**Error budget policy, automated.** When SLO-3's burn rate exceeds threshold, the
`LoadController` acts before a human does: raise the gate threshold, then switch to the
deterministic fast path, then shed
([ADR-009](#adr-009-backpressure-and-shedding)). **The error budget is wired to a control
loop rather than to a pager** — the system degrades in a documented, observable way, which is
the whole argument for having defined the degradation in advance.

**Autoscaling: KEDA, scaling the extractor and verifier on Kafka consumer-group lag.** This is
not decoration — it is the direct answer to the backpressure problem. CPU-based autoscaling
would be actively wrong here: the extractor is GPU-bound and its CPU sits near idle while the
queue grows. **Lag is the only metric that reflects the actual deficit**, and being able to
explain why CPU-based HPA fails for this workload is a better interview answer than the scaler
itself. Scale floor 1, ceiling bounded by VRAM.

**Instrumentation:** OpenTelemetry, with **trace context propagated in Kafka headers**, so a
single trace spans capture → ASR → gate → extract → verify → alert across six services and
one broker. Distributed tracing through an async streaming pipeline is the genuinely hard
version of tracing and it is what makes the per-stage budget table in
[ADR-006](#adr-006-the-latency-budget) a live dashboard rather than a document. Metrics to
Prometheus, traces to Jaeger, dashboards as JSON in the repo.

**Deliberate failure injection** (`make chaos-*`), each with a documented expected behaviour:

| Injection | Expected behaviour |
|---|---|
| Kill ASR mid-stream | Utterance lag spikes; consumer resumes from committed offset on restart; **zero claim loss, proven by SLO-4's conservation check.** |
| Kill the extractor | Candidate lag grows; KEDA scales; no data loss; verdicts arrive late and render as `SETTLED`. |
| Pause the broker | Producers buffer, then apply backpressure to the boundary that can tolerate it. |
| Inject 2 s latency into the LLM (toxiproxy) | `LoadController` moves AMBER → RED → fast path only. |
| Fill the disk | Archiver fails loudly; hot path continues. |
| Corrupt a model file | Service fails its readiness probe and never receives traffic. |

Each has a runbook entry with symptom, diagnosis and remediation, and each is rehearsed as a
**game day** ([`08-WAYS-OF-WORKING.md`](08-WAYS-OF-WORKING.md)) — one of us breaks it, the
other is on call and has not been told what broke.

### Alternatives rejected

- **CPU/memory-based autoscaling.** Rejected as described: it is the wrong signal for a
  GPU-bound queue consumer.
- **Uptime as the SLO.** Rejected: every service can be up while the system is useless.
- **Alert on every metric.** Rejected: five SLOs with burn-rate alerting, not fifty
  thresholds. Alert on symptoms the user would notice.
- **Full ELK / Loki stack.** Rejected on footprint; structured JSON logs to stdout plus traces
  cover our needs. On the [cut list](05-ROADMAP.md#the-cut-list) as an optional extra.

### Consequences

- SLO-4 requires a reconciliation job comparing admitted candidates to terminal verdicts per
  session. Cheap, and it is the highest-value monitor in the system.
- Trace context in Kafka headers must be in the contract from M0 — retrofitting tracing is
  painful.
- KEDA adds a component to the k3d deployment. Justified by the backpressure requirement, and
  cut if it ever is not.

### What would change our mind

If measurement shows the extractor never actually queues in realistic use, KEDA is solving a
hypothetical and should go — replaced by a single well-sized replica and an honest note. We
will look at the lag histogram before deciding.

---

## ADR-021: Two people, one co-owned interface

### Context

Two juniors, working evenings, in parallel, on different halves of one system, with no
manager. The default outcome is that one blocks the other for a week, or that the two halves
integrate for the first time in month three and do not fit. The organisational design is a
technical decision and belongs in this file.

### Decision

**One monorepo, a co-owned contracts package that is the only interface between the two of
us, and a schema registry that enforces it mechanically.**

```
blah/
├── contracts/          # CO-OWNED. Pydantic models, JSON Schema, enums, topic names,
│                       # the Verifier/ASR interfaces, and the contract test suite.
├── services/           # A: gate, extractor, verifier, almanac.  B: ingest, archiver, api.
├── deploy/             # B: compose/, k8s/ (Kustomize base + overlays), keda/, grafana/
├── warehouse/          # A: dbt project.   B: backfill + compaction jobs.
├── eval/               # A: harness, metrics, gold-set tooling.
├── fixtures/           # Shared. Transcripts, labels, consent manifests, fetch.py
└── docs/               # Shared. ADRs require a PR.
```

**`CODEOWNERS` makes `contracts/` require approval from *both* of us.** Everything else needs
one approval from the other person. This is the mechanism that makes the interface real: **A
cannot change the `Claim` schema without B noticing, and B cannot change topic names without
A noticing.** It is also the closest thing to a real work environment we can construct with
two people — a co-owned boundary with enforced review is exactly how platform and application
teams interact in a functioning org.

**The Redpanda Schema Registry enforces it at runtime too.** Every topic has a registered
schema; CI runs a **BACKWARD compatibility check** against the currently registered version
and fails the build on an incompatible change. Producers validate on write. So a breaking
schema change fails in three independent places — the registry check, the contract tests, and
the CODEOWNERS review — which is roughly the right amount of friction for the single most
dangerous class of change in the system.

**Contract tests are the anti-blocking mechanism.** Every interface has a fake implementation
that satisfies the same test suite as the real one: `FakeASR` replays a stored transcript with
original timings, `FakeExtractor` returns fixture claims, `FakeVerifier` returns fixture
verdicts. **Both of us develop against fakes and integrate continuously.** B can build the
entire deployment, observability and chaos story against `FakeASR` while A is still choosing a
Whisper model. This is the single most important decision for two people working in parallel,
and it is why M0 is built entirely out of fakes
([`05-ROADMAP.md`](05-ROADMAP.md)).

**Working agreements** (detail in [`08-WAYS-OF-WORKING.md`](08-WAYS-OF-WORKING.md)):
trunk-based with short-lived branches, squash merge, conventional commits, branch protection
on `main`, ADR-before-code for anything architectural, a weekly demo to each other, and
rotating on-call for game days.

### Alternatives rejected

- **Two repos, one per person.** Rejected: the integration cost is paid at the end, which is
  exactly when we have least energy. Also makes a single `make demo` impossible.
- **Informal agreement on schemas ("just tell me if you change it").** Rejected: with two
  people working different evenings and never in the same room, the schema drifts within a
  fortnight.
- **Full microservice-per-person split with API versioning.** Rejected as ceremony for a
  two-person system. CODEOWNERS plus a registry is the right weight.
- **One person writes contracts, the other consumes.** Rejected: it makes one of us a
  bottleneck and the other a passenger, and in a portfolio both of us need to be able to
  defend the schema in an interview.

### Consequences

- Both of us must understand the whole data model. That is a cost in ramp-up and a large
  benefit in interviews.
- `contracts/` PRs will sometimes wait a day for the other person's evening. Acceptable, and
  it is realistic — this is what working with a co-owned interface actually feels like.
- Fakes must be maintained alongside real implementations or they rot. The contract test suite
  runs against both, so rot fails CI.

### What would change our mind

Nothing at two people. At five or more, `contracts/` would become a versioned published
package with its own release cycle rather than a directory.

---

## ADR-022: No workflow orchestrator (yet)

### Context

There is a batch layer ([ADR-018](#adr-018-why-there-is-a-batch-warehouse-at-all)) with
scheduled jobs: archive compaction, mart builds, Almanac refresh, retention deletion,
evaluation runs. The reflex is to reach for Airflow, Dagster or Prefect — and "orchestrated
with Airflow" is a good line on a CV.

### Decision

**No orchestrator. Plain Python CLI jobs, invoked by a scheduler container in Compose and a
`CronJob` in Kubernetes.**

The honest arithmetic: we have **six jobs and a dependency graph two levels deep**. Airflow
would add a scheduler, a webserver, a metadata database and an executor — more moving parts
than the pipeline it orchestrates — to express `compact && dbt build && dbt test`.

**We would rather be asked "why no Airflow?" and have this answer than be asked "why Airflow?"
and not.** A junior who adds an orchestrator to six cron jobs signals they reach for tools
before thinking; a junior who can state the threshold at which the tool becomes correct
signals the opposite. The threshold is named below, and naming it is the whole point.

### Alternatives rejected

- **Airflow.** Rejected on footprint and complexity-vs-benefit at this scale. Genuinely the
  right tool at ~20+ interdependent tasks with backfill windows, SLA tracking and multiple
  owners.
- **Dagster.** The closest call — its asset-oriented model genuinely fits a lineage graph like
  ours, and its footprint is lighter. Rejected because we get the lineage we actually need
  from dbt, and the second scheduler would still be redundant. **This is the one we would add
  first** if the condition below is met.
- **Prefect.** Same reasoning as Dagster, weaker asset model for our case.
- **Make + cron with no retry logic.** Rejected as the *whole* answer — our jobs need retry
  with backoff, idempotency and failure alerting. We implement those in the job wrapper,
  deliberately and visibly, which is about 80 lines and demonstrates that we know what an
  orchestrator provides.

### Consequences

- The job wrapper (retry, backoff, idempotency key, structured logging, metric emission,
  failure alert) is ours to write and to test. Good: it makes explicit what an orchestrator
  would hide.
- No DAG UI. Job status is a Grafana panel fed by job metrics, which is adequate for six jobs.
- If a job fails at 03:00, we find out from an alert, not from a web UI — which is how it
  would work in production anyway.

### What would change our mind

Stated as a concrete threshold: **more than ~15 scheduled tasks, or any dependency graph
deeper than three levels, or the need for windowed backfill over arbitrary date ranges with
per-task retry state.** At that point Dagster goes in, and this ADR gets superseded rather
than edited.
