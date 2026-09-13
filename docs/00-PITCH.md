# BLAH — Bullshit Live Analysis Harness

> *"It is impossible for someone to lie unless he thinks he knows the truth. Producing
> bullshit requires no such conviction."*
> — Harry G. Frankfurt, **On Bullshit** (Princeton University Press, 2005)

**The name is a thesis, not a joke.** Frankfurt's distinction is the one this system is
built on: a **liar** tracks the truth in order to move away from it; a **bullshitter** is
simply indifferent to whether what they are saying is true. That second category is far
larger, far more common in interviews and on television, and — critically for us — far more
*detectable*, because someone indifferent to truth does not bother to stay consistent with
themselves. **Self-contradiction is the observable signature of indifference to truth.**

That is why this system's core is not "is this statement false?" (an open-world problem with
no ground truth and a defamation lawsuit attached) but "does this speaker's account hold
together?" (a closed-world problem we can actually solve). We are not building a lie
detector. We are building a **consistency detector**, and Frankfurt is the reason that is
the more interesting instrument.

**On the name.** *Blah* already means speech emptied of content — the word arrived at
Frankfurt's category on its own, centuries earlier. The acronym is deliberate and the pun is
the argument.

The system is **BLAH**; its internal-consistency engine — the component that actually detects
contradiction — is called **`hearsay`**, after the evidentiary rule (*a statement made outside
of court, offered for the truth of the matter asserted; inadmissible, because nobody checked
it*) and after **Hearsay-II**, the 1970s CMU speech-understanding system built as a blackboard
of cooperating knowledge sources. Same shape, fifty years later, with better ears.

So: **BLAH** is the harness, **`hearsay`** is the engine, and both names mean something.

---

## One-line pitch

**BLAH is a streaming data pipeline that turns live speech into tracked, addressable claims,
and raises an alert when a speaker contradicts themselves — with both quotes, both
timestamps, and the audio, fast enough to matter while they are still talking.**

## The pitch in one paragraph

Every recorded conversation that matters — a job interview, a compliance call, a
broadcast panel — produces dozens of factual assertions that nobody tracks. A human
listener holds maybe the last thirty seconds in working memory. Ninety seconds later the
speaker says something that flatly contradicts what they said at the start, and nobody
notices, because noticing requires holding every prior claim in mind and comparing each
new one against all of them. That is not a human task. It is a **stateful stream join**,
and it is the single most useful thing you can do to a transcript that transcription
alone does not give you.

---

## The specific pain

Concretely, the moment this product exists for:

> **00:03:12** — *"I ran our Kafka estate for about four years at Acme — three clusters,
> I was the one paged when it broke."*
>
> **00:21:47** — *"...to be fair I've never actually operated Kafka myself, we had a
> platform team that owned all of that."*

Today: the interviewer wrote down "4 yrs Kafka" at 00:03, was thinking about their next
question at 00:21, and the contradiction is discovered never. The hire is made or lost on
vibes, and the one piece of hard signal in the whole hour evaporated.

With BLAH: at **00:21:50** — three seconds later, while the sentence is still in the
air — the interviewer's second screen shows both quotes side by side, with a play button
on each, and the note *"possible conflict: direct operational experience — Kafka."* The
interviewer asks a follow-up. That is the entire product.

The same mechanism, pointed at different reference data:

- **Compliance / call QA.** An adviser says something that contradicts the approved
  product fact sheet, or contradicts what they said four minutes earlier in the same
  call. Regulated firms already pay people to listen to recordings after the fact.
- **Broadcast.** A guest states something that conflicts with a cited reference source.
  The correction has to arrive while the claim is still on screen, because a wrong fact
  that sticks is worse than no fact at all.

## Who would plausibly pay for it

Answered honestly, in descending order of realism:

1. **Regulated-industry call QA (financial advice, insurance, healthcare intake).** This
   is the real market and it is boring, which is why it is real. These firms already
   employ people to sample-listen to recorded calls against a script and a fact sheet.
   "Did the adviser contradict the approved disclosure?" is *exactly* our
   internal-consistency engine with the fact sheet loaded as a reference document. The
   buyer has a budget line for it today.
2. **Interview intelligence platforms** (BrightHire, Metaview and similar already sell
   recording, transcription, summaries and scorecards to talent teams). Claim-level
   contradiction tracking is a feature none of them ship. It would be sold to them, not
   against them. **With a hard caveat we take seriously — see [Non-goals](#non-goals) and
   [`06-EVALUATION-AND-RISK.md`](06-EVALUATION-AND-RISK.md): we do not believe an
   automated screening score built on this is defensible, and we designed the output so
   it cannot be used as one.**
3. **Newsrooms doing live coverage.** Real need, famously small budgets, and the Duke
   Reporters' Lab already tried and wrote up why it is hard. We treat this as the *third*
   use case, not the first.

**We are not claiming this repository is a business.** It is a portfolio project. The
question "who would pay" is here because a system designed with no buyer in mind makes
architecture decisions that cannot be defended, and we want ours to be defensible.

---

## Why this is a data engineering problem, not an AI demo

Every model in this system is off-the-shelf, downloaded, and frozen. We train nothing. If
you deleted every model and replaced them with `input()` calls, **the interesting 80% of
this repository would still be here and would still be hard.** That 80% is:

| The actual work | Why it is hard |
|---|---|
| **A discretisation problem.** Speech is a continuous signal; claims are discrete records. Something has to decide where one ends. | Claims split across utterances; pronouns that only resolve against earlier context; no natural key anywhere in the source data. |
| **A stateful stream join.** Every new claim must be compared against every prior claim by the same speaker in the same session. | O(n^2) if done naively. Requires candidate retrieval, then precise scoring. Requires session state that survives a pod restart. |
| **A backpressure problem.** Verification is 20-50x slower than transcription and always will be. | Bounded queues, priority shedding, and a policy for what happens when you cannot keep up — decided in advance, not at 2am. |
| **An event-time problem.** A verdict about something said at 00:03 may arrive at 00:09. | Event time vs processing time, verdict staleness as a first-class metric, and a UI that does not lie about when it knew things. |
| **An idempotency problem.** People repeat themselves. Three restatements must not produce three alarms. | Claim identity, canonical fingerprints, dedup keys, alert versioning and suppression. |
| **A replay problem.** "Did the new extractor make things better?" is only answerable if you can re-run a stored session and diff. | Constrains storage design from day one: immutable inputs, `run_id` on every record, no wall-clock dependence anywhere in the pipeline. |
| **An evaluation problem.** A false accusation is far more expensive than a missed claim. | A gold set, precision-biased thresholds, and a CI gate that blocks a merge which regresses precision. |
| **An operability problem.** Per-stage lag, queue depth, p99, verdict staleness, SLOs, failure injection. | The pipeline is the thing being observed, not the thing doing the observing. |

The models are **stages**. The pipeline is **the project**.

---

## Prior art, and where we actually differ

We are not the first people to think of this. Pretending otherwise in an interview is
fatal; knowing the field cold is a large, cheap advantage. Read these before writing code.

### Closest to broadcast mode

- **[LiveFC](https://arxiv.org/html/2408.07448v2)** (TU Delft / Factiverse, WSDM 2025) is
  near-identical in topology: Whisper Live + VAD, online diarization, an LLM pass that
  rewrites utterances into self-contained claims, a check-worthiness classifier,
  decomposition into search queries, multi-source retrieval, NLI for supported/refuted.
  **No public code, hosted as a Streamlit app, and — this is the important part — the
  paper claims "within seconds" and publishes no latency numbers, no throughput numbers,
  and no failure behaviour.** It is a research demo of an idea, not an operable system.
- **[Squash](https://reporterslab.org/2021/06/28/the-lessons-of-squash-our-groundbreaking-automated-fact-checking-platform/)**
  (Duke Reporters' Lab, 2019-2021) is the one to actually study, because they shipped it,
  it failed, and they wrote an honest post-mortem. Audio, Google STT, ClaimBuster, match
  against a database of already-published fact-checks, on-screen card. What killed it was
  **not the plumbing**: ASR mangled speech into nonsense; the matcher linked a claim about
  the moon landing to a fact-check about road permits because both contained the word
  "years"; and above all **there were not enough published fact-checks in existence to
  match against**, so the system sat silent while checkable claims went by. They had to
  bolt on a human gate ("Gardener") to make the output usable.
- **[Factiverse Live](https://www.factiverse.ai/solutions/live)** and
  **[Full Fact AI](https://fullfact.org/ai/)** are the shipping commercial products.
  **[ClaimBuster](https://idir.uta.edu/claimbuster)** offers a free check-worthiness API
  and, more usefully to us, a free labelled dataset.

**Squash's post-mortem is load-bearing for our design.** Every failure they hit maps onto
a decision in [`01-DECISIONS.md`](01-DECISIONS.md):

| Squash failure | Our response |
|---|---|
| ASR errors poisoned downstream matching | [ADR-016](01-DECISIONS.md#adr-016-bounding-asr-bias-so-it-cannot-become-a-discrimination-engine) — low-ASR-confidence claims are extracted but may never alert |
| Lexical matcher produced absurd matches | [ADR-012](01-DECISIONS.md#adr-012-how-contradiction-is-actually-detected) — retrieve-then-rescore with an NLI cross-encoder plus deterministic numeric rules; never lexical overlap alone |
| Not enough ground truth existed to match against | [ADR-001](01-DECISIONS.md#adr-001-scope--internal-consistency-is-the-core-external-checking-is-a-bounded-second-verifier) / [ADR-005](01-DECISIONS.md#adr-005-where-truth-comes-from--three-tiers-none-of-them-the-live-web) — internal consistency needs **no external ground truth at all**; that is precisely why it is our core |
| Needed a human gate to be usable | [ADR-015](01-DECISIONS.md#adr-015-consent-pii-and-retention--as-code-not-as-a-paragraph) — the human gate is the *design*, not a patch: we output prompts to a human, never judgements |

### Closest to interview mode

**Nothing.** [BrightHire](https://brighthire.com/) and [Metaview](https://www.metaview.ai/)
record, transcribe, summarise and score interviews. Neither tracks claims as entities or
detects intra-session contradiction. We searched and could not find a product or paper
that does "at 00:03 you said four years of Kafka; at 00:21 you said you had never operated
it." **That gap is real, and it is the half of the idea with genuine novelty — which is
the half we made the core.**

### Things we assemble rather than build

[WhisperLiveKit](https://github.com/QuentinFuxa/WhisperLiveKit) and
[whisper_streaming](https://github.com/ufal/whisper_streaming) (the LocalAgreement policy)
for streaming ASR; the [ClaimBuster dataset](https://zenodo.org/records/3609356)
(CC-BY-4.0) for check-worthiness labels; the ClaimReview schema and
[CLEF CheckThat!](https://ceur-ws.org/Vol-4038/paper_60.pdf) / AVeriTeC for labelled data;
[Loki](https://github.com/Libr-AI/OpenFactVerification) as a reference open verification
pipeline.

### So what is left for us?

That the architecture is settled prior art is **good news**. It means we cannot be accused
of naive invention, and it moves the conversation to where two pipeline engineers win:

> LiveFC is a research demo with no published latency budget and no code. Squash died of
> data problems while its pipeline worked fine. **Not one system in this space has
> published a replay harness, per-stage lag SLOs, a backpressure and shedding policy, a
> failure-injection story, or an idempotent alerting model. And none of them do
> intra-session contradiction tracking.**
>
> That is our entire differentiation, and it is a data engineering and SRE
> differentiation, not a machine learning one.

---

## Non-goals

Stated loudly so a reviewer does not go looking for them and conclude we failed.

1. **We do not produce a hiring score, ranking, or recommendation.** Not "cannot yet" —
   *will not.* Interview mode emits **prompts for a human interviewer** ("you may want to
   ask about X"), never assessments. This is a deliberate design limit imposed by ASR
   accuracy disparities across accents and dialects; see
   [`06-EVALUATION-AND-RISK.md`](06-EVALUATION-AND-RISK.md). An automated screening tool
   built on an ASR system with a measured ~2x word-error-rate gap between demographic
   groups is a discrimination engine with a dashboard.
2. **We never emit the label "false" about a named person.** Our verdict vocabulary has no
   such value. The strongest thing broadcast mode can say is `CONTRADICTED_BY_SOURCE`,
   always rendered with the source and its `as_of` date. See
   [ADR-014](01-DECISIONS.md#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm).
3. **No contested-domain adjudication.** If sources disagree, the verdict is `DISPUTED`
   and we show both. We do not resolve political, moral, or scientific controversies.
4. **English only.** Multi-language is a data problem we cannot evaluate honestly with two
   people and no budget — we would have no gold set in the second language, and shipping
   an unevaluated language is worse than shipping one.
5. **No speaker identification.** Diarization (*who spoke, as a cluster*) is in scope
   because contradiction detection is per-speaker and needs it. **Identification** (*that
   cluster is Jane Smith*) is out: it is a biometric, it triggers a much heavier legal
   regime, and an operator can supply the mapping manually in two clicks.
6. **No polished consumer UI.** The UI is a functional operator view. Effort spent on
   design is effort not spent on the pipeline, and a reviewer is here for the pipeline.
7. **No live TV ingest.** Broadcast mode ingests files and public streams we are permitted
   to use. We are not acquiring rights to anything.
8. **No model training, fine-tuning, or research.** Off-the-shelf weights, frozen,
   version-pinned. If a step can be done with deterministic code, it is.
9. **Not multi-tenant, not authenticated, not internet-facing.** It is a single-operator
   local system. Adding auth would be a weekend of work that demonstrates nothing.

---

## Assumptions

Recorded here because we made them without asking, and a reviewer should be able to see
and challenge every one.

| # | Assumption | If wrong |
|---|---|---|
| A1 | One of our two machines has an NVIDIA GPU (>=8 GB VRAM); the other is CPU-only. | The GPU box is the dev/demo target; the CPU box must still run the whole system on smaller models, because a reviewer will have no GPU. Enforced by CI, which runs CPU-only. |
| A2 | A reviewer cloning the repo has Docker, ~16 GB RAM, no GPU, and no accounts anywhere. | The default profile must work for them. Anything needing a GPU or an API key is opt-in via env var and has a local default. |
| A3 | "Real-time" here means **a verdict within 4 s of the end of the utterance that triggered it, p95**. | This is a product judgement, not a research finding — see [ADR-006](01-DECISIONS.md#adr-006-the-latency-budget) for the reasoning and the fallback if we cannot hit it. |
| A4 | Sessions are <= 90 minutes and contain <= ~2,000 claims. | Bounds the state problem: a session's claim set fits comfortably in memory and in one Postgres table with `pgvector`. A vector database would be unjustified at this scale. |
| A5 | English, one or two speakers, reasonable audio (not a noisy street). | Scopes the ASR problem. We measure and publish where this breaks rather than pretending it does not. |
| A6 | We can lawfully use: US House/Senate floor video (public domain), C-SPAN federal-event coverage under its non-commercial licence with attribution, ClaimBuster (CC-BY-4.0), and our own recordings. | We do **not** redistribute third-party audio in the repo. Fixtures ship as transcripts plus a download script. See [ADR-013](01-DECISIONS.md#adr-013-the-gold-set-and-where-the-audio-comes-from). |
| A7 | Both of us can commit several evenings a week, indefinitely, with no deadline. | Milestones, not weeks. Every milestone is independently demo-able and we can stop after any of them. |
| A8 | Target job market is Europe/UK, so GDPR is the governing regime we design to. | Drives the consent gate, retention defaults and the subject-access/erasure tooling in [ADR-015](01-DECISIONS.md#adr-015-consent-pii-and-retention--as-code-not-as-a-paragraph). |

---

## Where to look next

- The most important file is [`01-DECISIONS.md`](01-DECISIONS.md). Everything else is
  downstream of it.
- If you have four minutes, read the [README](../README.md) instead.
- If you are about to attack the design, start with
  [ADR-001](01-DECISIONS.md#adr-001-scope--internal-consistency-is-the-core-external-checking-is-a-bounded-second-verifier)
  (scope) and [ADR-006](01-DECISIONS.md#adr-006-the-latency-budget) (latency budget) —
  those are the two load-bearing ones, and if either is wrong the project is wrong.
