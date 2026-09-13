# Evaluation and risk

The evaluation harness is a **component of the system**, not a script we ran once. It has an
owner, a schema, CI integration, and the power to block a merge.

The risk half of this file follows one rule: **every mitigation must name the place in the
architecture where it lives.** "We acknowledge that ASR has bias" is not a mitigation. A
severity-downgrade rule keyed on `flags.low_asr_confidence`, enforced in `alerter` and tested in
CI, is.

---

## Part 1 — Evaluation

### The bias that determines everything: precision over recall

> **A false accusation destroys trust far faster than a missed claim.**

This is the premise of the whole project, and it has to show up as an asymmetry in the numbers,
not as a sentiment.

If BLAH misses a contradiction, the interviewer is exactly as well off as they were without us —
they take their own notes and use their own judgement. Cost: one lost insight, and the user
never knows.

If BLAH raises a false contradiction, the interviewer challenges a candidate over something they
did not say, in front of them, while the tool sits on screen asserting it. The candidate is
treated unfairly, the interviewer is embarrassed, and **every subsequent alert is discounted**.
One false positive poisons the fifty true positives that follow it.

So:

| Decision point | Bias | Why |
|---|---|---|
| Check-worthiness gate | **Recall** | Admits into a bounded queue we can shed from. Over-admitting costs queue depth, which we manage. Under-admitting loses a claim invisibly and forever. |
| kNN candidate retrieval | **Recall** | Cheap. A missed candidate cannot be rescored. |
| NLI / rule threshold | **Precision** | Hard. This is where precision is bought. |
| Alert vs annotation | **Precision** | Harder still. Ambiguity becomes a quiet margin note, never an alarm. |

Cheap-and-broad followed by expensive-and-sharp, twice, in the same pipeline. **Precision is
purchased at exactly one place — the alarm threshold — and everything upstream is tuned for
recall so that there is something to be precise about.**

### The gold sets

| Set | Purpose | Size | Source | Cost |
|---|---|---|---|---|
| **G1** | Check-worthiness | 23,533 labelled sentences | [ClaimBuster](https://zenodo.org/records/3609356), CC-BY-4.0 — US presidential debates 1960-2016 | **Free** |
| **G2-dev** | Contradiction: tuning | ~12 sessions, 10-15 min each | Scripted and recorded by us | Our evenings |
| **G2-held-out** | Contradiction: the honest number | ~8 sessions | **Written by one of us, never read by the other** | Our evenings |
| **G3** | External checking + real-audio ASR | ~10 clips | US House/Senate floor (public domain); C-SPAN federal coverage, non-commercial with attribution | Free |

**G2 is the expensive one and it is the one that matters.** Building it cheaply:

1. **Script contradictions by rule class.** Each session plants at least one of each: numeric
   (*"four years"* vs *"eighteen months"*), polarity (*"I ran it"* vs *"I never operated it"*),
   temporal (overlapping exclusive roles), cardinality (*"three clusters"* vs *"a single
   cluster"*). Labels are known before recording, so **annotation cost is zero** — the script
   *is* the label file.
2. **Plant hard negatives deliberately.** Near-misses that must **not** alert: refinement
   (*"about four years — well, three and a half"*), scope change (*"I ran Kafka"* / *"I never ran
   Kafka at Globex"*), reported speech (*"my manager said it was twelve percent"*), and
   hypotheticals. **The hard negatives are the valuable half of the set** — anything can find a
   flat contradiction; not alerting on a refinement is the hard part.
3. **Vary delivery, not just content.** Same script read by different people, at different
   speeds, with hesitations and self-corrections. This is where accent coverage comes from, and
   where it is limited by who we know.
4. **Record in one sitting per session.** 15 minutes of recording produces a labelled session.
   Twenty sessions is about ten evenings between us, spread across M1-M3.

**The obvious objection is real: this is synthetic, and we tuned on our own script.** Answered
structurally rather than with a promise — G2-held-out is authored by one person, stored in a
directory the other does not read, **and CI refuses to run it outside a milestone boundary.**
The split is enforced by tooling, not by good intentions, because good intentions do not survive
a frustrating Tuesday evening.

**What we will not do:** generate the gold set with an LLM. Evaluating an LLM-containing
pipeline against LLM-generated ground truth measures agreement, not correctness, and it is the
most common way portfolio ML projects fool themselves.

### Metrics

Every one is a column in a mart ([ADR-018](01-DECISIONS.md#adr-018-why-there-is-a-batch-warehouse-at-all)),
sliced by `dim_pipeline_version` so any two runs are comparable.

**Quality**

| Metric | Definition | Target | Gate? |
|---|---|---|---|
| **Alert precision** | true alerts / all alerts, on G2-held-out | **≥ 0.90** | **Blocks the merge** |
| Alert recall | alerts raised / planted contradictions | Reported, not gated | No |
| Gate recall | check-worthy utterances admitted | ≥ 0.95 | Warn |
| Gate admit rate | fraction of utterances admitted | Monitored (queue cost) | No |
| Extraction validity | schema-valid claims | 100% (by construction) | Yes |
| Extraction fidelity | claims whose canonical form matches the label | Reported | No |
| `subject_unresolved` rate | fraction of claims flagged | < 15% | Warn ([ADR-003](01-DECISIONS.md#adr-003-pronouns-and-claims-split-across-utterances)) |
| Fingerprint collision rate | distinct claims sharing a fingerprint | Reported | Warn |
| **LLM delta** | claims + precision, LLM vs `--no-llm` | **Published** | No |

**Latency** — p50/p95/p99 per stage and end to end, per profile. Gate: **p95 `verdict_lag_ms`
regression > 20% fails the build.**

**Operational** — shed rate, `UNVERIFIED` reason distribution, **SLO-4 conservation
(`claims_in == terminal_verdicts_out`, asserted)**, consumer lag, Almanac hit rate.

**Fairness** — WER by accent group, **alert rate by accent group**, and `low_asr_confidence`
rate by accent group. Gate: `max_group_wer / min_group_wer ≤ 1.5`.

> The second of those — **alert rate by group** — is the one that actually matters and the one
> almost nobody measures. Equal WER with unequal alert rates would still be a discriminatory
> system, because the harm is in the output, not the transcript.

### The harness

```bash
blah eval run --set G2-held-out --run-id $(git rev-parse --short HEAD)
blah eval compare --baseline main --candidate HEAD
blah eval gate --min-precision 0.90 --max-wer-ratio 1.5 --max-latency-regression 0.20
```

`eval run` replays every session in the set from stored transcripts
([ADR-017](01-DECISIONS.md#adr-017-replay-is-the-evaluation-primitive)) under a fresh `run_id`,
lands the output in the lake, rebuilds the marts, and computes every metric above.
`eval gate` exits non-zero on a regression, and CI runs it on every PR touching
`services/`, `contracts/` or `eval/`.

**Replay is what makes any of this possible.** Without it, "did this change help?" is answered by
running the demo and squinting.

---

## Part 2 — Risk

Each item: the risk, the **mitigation**, and **where in the architecture it lives**.

### R1 — ASR accuracy varies by accent and dialect

**The risk, stated without softening.** Commercial ASR has been measured at roughly **35% WER for
African American speakers versus 19% for white speakers** on matched content, with the gap driven
by acoustic rather than lexical modelling; comparable gaps are documented for Scottish, Indian,
Jamaican and African-accented English. Whisper is better than the systems in those studies but is
not free of it.

Compose that with our product: higher WER → more garbled transcripts → more spurious claims →
**more false contradiction alerts for speakers with certain accents.** An interview screening tool
built on that is not a tool with a bias problem. It is a discrimination engine with a dashboard,
and unlawful in most markets we would want to sell into.

**This is not a risk to mitigate. It is a constraint that determines what the product may output
at all.**

| Mitigation | Where it lives |
|---|---|
| **Interview mode emits interviewer prompts, never assessments.** No score, no ranking, no recommendation. | **There is no field in the `Alert` schema that could carry one** — [`03-DATA-CONTRACTS.md`](03-DATA-CONTRACTS.md#alert). Adding one requires a `contracts/` PR approved by both owners. |
| Low ASR confidence downgrades severity one level (alert → annotation) | `alerter`; `flags.low_asr_confidence`; [ADR-014](01-DECISIONS.md#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm) |
| **WER and alert rate by group are measured, published, and gated in CI** | `mart_wer_by_group`; `blah eval gate --max-wer-ratio 1.5` |
| The gold set's actual composition is published, and unmeasured groups are reported as unmeasured — never as passing | `docs/reports/fairness-*.md` |

**We expect to fail the fairness gate initially.** That is what it is for. A failing gate with a
published number is more honest, and more impressive, than a passing system that never measured.
**If we cannot pass it, the documented response is to narrow the claimed scope of the product —
not to delete the gate.**

The design holds up under interrogation because of the distance between two outcomes: the residual
harm from a false *prompt* is one unnecessary clarifying question, asked by a human who has just
listened to the audio themselves. The residual harm from a false *score* is a rejected candidate
who never knows why. **That distance is the entire justification.**

### R2 — Recording consent

**Risk.** Jurisdictions differ; two-party consent is real; GDPR requires a lawful basis and
disclosure of automated processing (Art. 13(2)(f)).

| Mitigation | Where it lives |
|---|---|
| **The pipeline refuses to start without a valid consent block.** 422, and no audio written. | `ingest`; `SessionManifest.consent` |
| `consent.obtained: Literal[True]` — **a non-consenting session does not type-check and cannot be constructed** | `contracts/` |
| Jurisdiction, method, who obtained it, and explicit confirmation the subject was informed of automated processing are all required fields | `Consent` model |
| **No bypass flag exists**, including for our own development — we use pre-signed fixture manifests instead | `fixtures/consent/` |

Forty lines of validation, and the most persuasive artifact in the repository, because it proves
the ethics section is architecture rather than prose.

### R3 — Candidate data is personal data

| Mitigation | Where it lives |
|---|---|
| Pseudonymous by default — `SPEAKER_00`, a diarization cluster, never an identity. **Nothing in the pipeline needs a real name to function.** | `Utterance.speaker_id` |
| Name↔cluster mapping is a deliberate operator action written to an append-only audit log | `api`; `audit_log` |
| Retention from the manifest drives real deletion across **all three** storage layers | Retention CronJob |
| **Lake partitioned by `session_id` specifically so erasure is a partition drop, not a rewrite** | [Partitioning](03-DATA-CONTRACTS.md#partitioning-and-why-it-is-shaped-that-way) |
| Subject access and erasure as CLI commands, **with a test asserting post-erase full-text search returns nothing** | `blah subject export` / `erase` |
| Purpose limitation: `mode=` is the first partition level; a cross-mode join fails a dbt test | Lake layout + dbt |

The warehouse is where deletion usually silently fails. Ours is partitioned for it.

### R4 — Calling a named public figure a liar in real time

| Mitigation | Where it lives |
|---|---|
| **There is no `FALSE` in the verdict enum.** The type system will not let us say it. | `VerdictStatus` |
| The strongest Mode B statement is `CONTRADICTED_BY_SOURCE`, always with source, tier and `as_of` | `Evidence` |
| **Mode B has an annotation ceiling — it can never alarm.** A test asserts no `CONTRADICTED_BY_SOURCE` verdict can carry `severity == ALERT`. | `alerter`; M6 done-means |
| Sources disagree → `DISPUTED`, both shown, **we do not adjudicate** | `hearsay` / `almanac` |
| Headlines are **templated**, attributive, quoting: *"at {t} the speaker said {quote}"* — stating what was said, not what is true | `alerter` |
| An LLM never decides a verdict and never writes free-form user-facing text about a person | [ADR-019](01-DECISIONS.md#adr-019-where-the-llm-is-allowed-to-run) |
| A second enforcement at the warehouse boundary: dbt `accepted_values` on `fct_verdict.status` | `warehouse/` |

Two independent enforcement points for the same constraint, because it is the one where being
wrong is a lawsuit.

### R5 — The system is confidently wrong and the user believes it

| Mitigation | Where it lives |
|---|---|
| Four visible states, not two: alert / annotation / checked-clear / **not checked (with reason)** | UI + `ReasonCode` |
| **Nothing is dropped silently.** Every admitted candidate gets a terminal verdict, including `SHED_LOAD`. | SLO-4 conservation check |
| Every alert shows verbatim quotes and playable audio — **the user verifies us in two seconds** | `Evidence.media_time_ms` |
| Ambiguity becomes an annotation, never an alarm | Threshold table, [ADR-014](01-DECISIONS.md#adr-014-the-confidence-vocabulary-and-what-is-allowed-to-alarm) |
| The degradation ladder is displayed — the user always knows which rung we are on | UI banner + `load.level.v1` |

The audio play button is the most important honesty feature in the system. It makes every alert
falsifiable by the user in the moment.

### R6 — Diarization mislabels speakers

The quietest serious failure: attribute two speakers' claims to one cluster and you manufacture
contradictions that nobody said.

| Mitigation | Where it lives |
|---|---|
| `speaker_stability` on every utterance | `Utterance` |
| A claim may not alert across a speaker boundary unless the cluster has been stable for N utterances | `hearsay` |
| Speaker revisions are **new records** (`revises`), never in-place updates, so replay is exact | `Utterance.revises` |
| Speaker-churn rate is a monitored metric | Dashboard |

### R7 — We fool ourselves about quality

The failure mode of every portfolio ML project.

| Mitigation | Where it lives |
|---|---|
| Held-out set authored by one person, unread by the other, **enforced by tooling** | `eval/`, CI |
| Gold set is **never** LLM-generated | [ADR-013](01-DECISIONS.md#adr-013-the-gold-set-and-where-the-audio-comes-from) |
| Precision gate blocks the merge; it is not advisory | CI |
| G1 and G2 numbers reported separately — **the better one is never quoted as if it were both** | Eval reports |
| Every report is dated and committed, including the bad ones | `docs/reports/` |

### R8 — Licensing of source audio

| Mitigation | Where it lives |
|---|---|
| **We redistribute no third-party audio.** `fixtures/` holds transcripts, labels and checksums; `fetch.py` downloads from source. | `fixtures/` |
| The default demo fixture is **G2 — recorded by us, owned by us** — so `make demo` works offline with nothing to download | `make demo` |
| C-SPAN attribution where used; non-commercial use only | `fixtures/ATTRIBUTION.md` |
| Model licences recorded (Whisper MIT, faster-whisper MIT, Silero MIT, ClaimBuster CC-BY-4.0) | `docs/LICENCES.md` |

### R9 — The project is abandoned half-built

The most probable risk of all, and it gets a mitigation like any other.

| Mitigation | Where it lives |
|---|---|
| **Every milestone is independently demo-able**, starting with M0 | [`05-ROADMAP.md`](05-ROADMAP.md) |
| M0 contains no ML at all, so the highest-risk work is never on the critical path to a demo | M0 |
| An ordered cut list, written in advance, so cutting is a decision rather than a collapse | [Cut list](05-ROADMAP.md#the-cut-list) |
| Six things that are never cut, because a version without them is a tutorial | Same |

---

## What we would tell a sceptic, unprompted

Three real weaknesses, stated before anyone finds them. Volunteering these is worth more than
defending them under questioning.

1. **G2 is synthetic and small.** Twenty scripted sessions recorded by two people and their
   friends is not a representative corpus. Our precision number is real but its confidence
   interval is wide, and the accent coverage is limited by our social circle. We state the
   composition rather than implying coverage we do not have.
2. **ClaimBuster is political debate speech; our domain is interviews.** The gate will transfer
   imperfectly. We measure the gap and report both numbers separately.
3. **Mode B will mostly say "unverified."** The Almanac is small. That is the honest outcome at
   zero budget and it is exactly what Squash's post-mortem predicts — **which is why internal
   consistency is the core and Mode B is last on the roadmap and first on the cut list.**
