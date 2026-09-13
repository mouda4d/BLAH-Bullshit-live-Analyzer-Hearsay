# Demo and interview

Three minutes on screen, ten questions a panel will ask, and the two-sentence version.

---

## The three-minute demo

**Screen layout** — one browser window, three panes, plus a terminal. Set this up before you
start talking; fumbling with windows costs thirty of your one hundred and eighty seconds.

```
┌────────────────────────────┬──────────────────────────┐
│  Live transcript           │  Alerts                  │
│  (scrolling, speaker-      │  (cards with quotes,     │
│   tagged, confidence-      │   timestamps, ▶ audio)   │
│   shaded)                  │                          │
├────────────────────────────┴──────────────────────────┤
│  Grafana: verdict_lag_ms p95 · consumer lag · load     │
│  level · shed rate                                     │
└────────────────────────────────────────────────────────┘
   + a terminal, visible, for the breaking part
```

**Run it from a recorded fixture, not live speech.** Live microphone demos fail for reasons that
have nothing to do with your system, and a reviewer cannot tell the difference between "the room
was noisy" and "the pipeline is bad." Use `fixtures/sessions/mock-interview-01`, which you
recorded and which is in the repo.

---

### 0:00 – 0:20 · One command

**On screen:** a clean terminal.

```bash
git clone ... && cd blah && make demo
```

**Say:**

> "Clean clone, one command, no GPU, no API keys, no accounts. That is a hard constraint — if a
> reviewer can't run it, it didn't happen. Everything you're about to see runs on a laptop."

Containers come up. Move on while they do; do not narrate Docker.

---

### 0:20 – 1:05 · The thing it actually does

**On screen:** transcript scrolling. Claims appear beside it as structured records.

**Say, while it plays:**

> "This is a mock interview. On the left, streaming transcription. On the right, every factual
> claim extracted as a structured record — subject, predicate, value, time scope. Note it's
> ignoring most of what's said: opinions, hedges, filler. A cheap gate kills about 70% before
> anything expensive runs."

At **00:03:12** the candidate says *"I ran our Kafka estate for about four years at Acme."*
A claim card appears.

At **00:21:47** they say *"...to be fair I've never actually operated Kafka myself."*

**The alert fires.** Stop talking. Let it land for a beat.

**Then:**

> "Both quotes, both timestamps, and —" *(click ▶ on each)* "— the actual audio, so you can check
> us in two seconds. That is deliberate: every alert has to be falsifiable by the user in the
> moment.
>
> And look at the clock." *(point at Grafana)* **"2.8 seconds** from the end of that sentence.
> The whole point is that it arrives while the interviewer can still say 'sorry, can I go back
> to something?' — not in a report afterwards."

---

### 1:05 – 1:30 · It doesn't nag, and it doesn't guess

**On screen:** the candidate restates the claim twice more. **No new alerts.** The badge ticks to
`restated × 3`.

**Say:**

> "Said three times, alerted once. Claim identity is a canonical fingerprint, not the text —
> 'four years' and 'about 4 yrs' are the same assertion. The dedup key is the sorted pair of
> fingerprints, so the alert id is deterministic and duplicates collapse by construction rather
> than by a lock.
>
> People repeat themselves constantly under pressure. A tool that alarms three times gets turned
> off, and then it doesn't matter how good the detection is."

Then the **near-miss** at 00:24 — *"about four years... well, three and a half."*

> "And that one is a refinement, not a contradiction. **It doesn't fire.** Anything can catch a
> flat contradiction. Not firing on a self-correction is the hard part, and it's what our gold
> set is mostly made of."

---

### 1:30 – 2:10 · Break it on purpose

**On screen:** the terminal, while the session keeps playing.

```bash
docker kill blah-asr
```

**Say:**

> "Transcription just died mid-sentence."

Point at Grafana: utterance lag spikes. The UI shows a degraded banner — *"transcription
interrupted"* — rather than simply going quiet.

> "It tells the user. A pipeline that silently stops is worse than one that's honestly broken,
> because silence looks identical to 'nobody said anything checkable'."

The container restarts, resumes from its committed offset, transcript continues.

```bash
make verify-conservation
# claims_in=47  terminal_verdicts_out=47  ✓
```

> "And nothing was lost. That's SLO-4 — every admitted claim gets exactly one terminal verdict,
> including the ones we deliberately didn't check. It's a conservation law, and it's the single
> most useful monitor in the system, because it catches every silent-drop bug this architecture
> could ever develop."

---

### 2:10 – 2:40 · Overload it on purpose

```bash
make load-4x
```

**On screen:** consumer lag climbs. The load level walks `GREEN → AMBER → RED`. Some transcript
lines go grey with a *"not checked — system busy"* marker.

**Say:**

> "Four times real time. Verification is twenty to fifty times slower than transcription and
> always will be — that inequality is the design, not a bug.
>
> So it degrades in a defined order: raise the gate threshold, then drop to the deterministic
> rule-only path with no LLM, then shed by priority. **And every shed claim still gets a verdict
> record saying it was shed.** Grey means 'we didn't check this', which is a different thing from
> 'we checked and it was fine.' Most systems conflate those two and the user can't tell."

*(Point at the conservation counter, still balanced.)*

---

### 2:40 – 3:00 · The finale — prove a change made it better

```bash
make replay RUN=baseline
blah eval compare --baseline baseline --candidate HEAD
```

**On screen:**

```
verdicts changed:     12
alerts gained:         3    lost: 1
alert precision:    0.91 → 0.93
p95 verdict_lag:    3.4s → 3.3s
fairness (WER ratio): 1.38  ✓
```

**Say:**

> "That's the same recorded session replayed through a new pipeline version and diffed. It's how
> we answer 'did that change help?' with a number instead of a vibe — and it's wired into CI, so
> a pull request that drops precision below 0.90 cannot merge.
>
> That constraint is why every record carries a `run_id` and a model version, why no stage is
> allowed to read the wall clock, and why the storage layer looks the way it does. **Replay isn't
> a feature we added at the end. It's the thing the storage design was built around from day
> one.**"

**Stop.** Do not add anything. Three minutes.

---

### What to do when it breaks for real

It will. Rehearse this:

| Symptom | Say this and move on |
|---|---|
| Containers slow to start | "It's pulling images — while that happens, here's the topology." *(Show the diagram.)* |
| An alert doesn't fire | "That's a threshold call — we bias hard toward precision, so it stays quiet when it's unsure. Let me show you the annotation it did raise." *(Then move to the chaos section, which always works.)* |
| The whole thing fails | "Let me show you the recorded run instead." **Have `demo.mp4` on disk.** Record it once things work and never rely on live. |

---

## Ten questions a panel will ask

### 1. "Why Kafka? Couldn't you just use HTTP between these services?"

> "For a normal pipeline, yes — and I'd have used HTTP. Three specific requirements forced a log.
>
> First, replay is our evaluation strategy: we re-read a historical session from an arbitrary
> offset through a new pipeline version and diff the results. That's the definition of a log; with
> HTTP I'd have built a worse one inside Postgres.
>
> Second, verification can return after the speaker has moved on, so a verdict needs to attach to
> a claim that a synchronous request would have timed out on.
>
> Third, backpressure. Consumer-group lag is the metric the whole ops story runs on — it drives
> the shedding controller and the autoscaler. HTTP gives me a timeout and a 500.
>
> Redpanda rather than Kafka purely on footprint — same API, same semantics, no JVM, on a laptop
> already running Whisper and an LLM on the same GPU. Nothing I learned there wouldn't transfer."

### 2. "Isn't this just a wrapper around Whisper and an LLM?"

> "Delete every model and replace them with `input()` calls, and about 80% of the repo is still
> there and still hard: segmentation, claim identity and canonicalisation, the stateful join,
> backpressure and shedding, event-time handling for late verdicts, idempotent alerting, replay,
> the evaluation harness, and the SLOs.
>
> The proof is M0 — the first milestone contains no ML at all. `FakeASR` replays a transcript, a
> rule verifier finds contradictions, and the full system works end to end: consent gate, log,
> replay, diff, dashboards, CI. Then we swapped fakes for real models behind contract-tested
> interfaces. If Whisper vanished tomorrow the architecture wouldn't change."

### 3. "How do you know it works?"

> "Held-out gold set, alert precision ≥ 0.90, and CI blocks a merge that drops below it.
>
> The interesting half is that we bias hard toward precision and say why: a missed claim costs one
> insight and the user never knows; a false accusation gets the tool turned off permanently. So the
> gate is recall-biased — it admits into a bounded queue we can shed from — and the alarm threshold
> is precision-biased. Cheap-and-broad, then expensive-and-sharp.
>
> And the held-out set was written by one of us and never read by the other, enforced by tooling
> rather than by promising. Most of that set is hard negatives: self-corrections, scope changes,
> reported speech. Catching a flat contradiction is easy. Not firing on 'four years — well, three
> and a half' is the actual problem."

### 4. "What's the hardest part?"

> "Knowing where a claim ends. Speech is continuous; claims are discrete records that need a
> primary key. A claim can span two utterances, or contain a pronoun that only resolves against
> something said a minute earlier.
>
> We handle it with a sliding window of three utterances plus a session entity registry — but the
> decision I'd defend hardest is what happens when it *fails*. If the extractor can't resolve a
> referent it has to say so, and a claim with `subject_unresolved` set can never alert. It's
> stored, it's counted, it's on a dashboard, but it stays silent.
>
> The alternative — guessing the most recent matching entity — is exactly how Duke's Squash
> project matched a claim about the moon landing to a fact-check about road permits. A confident
> wrong subject is the worst output this system can produce."

### 5. "Why not use RAG / a vector database / an LLM to decide contradiction?"

> "Three separate answers.
>
> No vector database because we have under two thousand vectors per session. `pgvector` with an
> IVFFlat index answers in single-digit milliseconds. We did the arithmetic — adding a service for
> that would be decoration.
>
> No RAG over a general corpus because retrieval returns *topically similar* text, and topical
> similarity is not evidence. That's Squash's failure with embeddings instead of keywords.
>
> And no LLM for the contradiction decision, for a subtle reason: contradictory sentences are
> highly *similar* in embedding space. 'I ran Kafka' and 'I never ran Kafka' are nearly identical
> to a bi-encoder. So similarity is a good retrieval signal and a terrible decision signal. We
> retrieve with embeddings, then rescore the top eight with an NLI cross-encoder that outputs a
> calibrated probability we can threshold — ten times faster than an LLM, reproducible under
> replay, and actually tunable. The LLM only writes the sentence after the decision is made."

### 6. "What happens when it can't keep up?"

> "It degrades in a documented order and tells the user which rung it's on: raise the gate
> threshold, then deterministic rules only with no LLM, then shed by priority — where priority is
> check-worthiness times recency times novelty.
>
> The rule I'd defend hardest is that **nothing is ever dropped silently.** A shed candidate gets
> a terminal verdict record saying `UNVERIFIED / SHED_LOAD`. That gives us three things: the UI
> can show 'not checked' as distinct from 'checked and clear', replay and evaluation stay sound,
> and shedding becomes measurable instead of invisible.
>
> It's also a conservation law — claims in equals terminal verdicts out — which we assert in CI
> and monitor at runtime. It's the best bug-catcher in the system."

### 7. "Why no Airflow? No Flink? No Kubernetes operator?"

> "Because each would be more machinery than the problem.
>
> Airflow: six scheduled jobs, dependency graph two levels deep. An orchestrator would add a
> scheduler, webserver, metadata DB and executor to express `compact && dbt build && dbt test`. We
> wrote the retry-backoff-idempotency wrapper ourselves — about eighty lines — which makes
> explicit what an orchestrator hides. I'd add Dagster past roughly fifteen tasks or a graph
> deeper than three levels.
>
> Flink: we have no windowed aggregations and no time-range joins. Our entire watermark
> requirement is a `MIN()` over a small table of in-flight work. Importing a stream processor for
> a feature we wouldn't use is the clearest inexperience signal there is.
>
> Kubernetes we *do* use, but for a specific thing — KEDA scaling the extractor on consumer-group
> lag. CPU-based autoscaling would be actively wrong, because the extractor is GPU-bound and its
> CPU sits near idle while the queue grows."

### 8. "This is an interview screening tool. Isn't that an ethical minefield?"

> "It is, and it changed what we were willing to build.
>
> ASR word error rates differ by roughly a factor of two across demographic groups — around 35%
> versus 19% in the published comparisons, driven by acoustic modelling. Compose that with our
> pipeline and higher WER means more garbled transcripts, more spurious claims, and more false
> contradiction alerts for speakers with certain accents. That's not a tool with a bias problem;
> it's a discrimination engine with a dashboard.
>
> So the product doesn't score candidates. It emits prompts for a human interviewer — both quotes,
> both timestamps, both audio clips, 'you may want to ask about this.' And that's enforced
> structurally: there is no field in the `Alert` schema that could carry a score. Someone wanting
> to build one would have to change a co-owned schema through a two-person review.
>
> On top of that, low ASR confidence downgrades an alert to a silent annotation, and we measure
> WER *and alert rate* by group in CI with a gate at a 1.5 ratio. We expect to fail that gate
> first — that's what it's for. If we can't pass it, the documented response is to narrow the
> product, not delete the gate."

*(If pressed on the residual harm:)*

> "The gap between the two outcomes is the whole justification. A false prompt costs one
> unnecessary clarifying question, asked by someone who just listened to the audio themselves. A
> false score costs a candidate a job they never learn they lost. Those aren't the same risk, and
> the design lives entirely on one side of that line."

### 9. "What would you do differently, or what's weakest?"

> "Three things, and I'd rather say them than have you find them.
>
> The gold set is twenty scripted sessions recorded by two people and their friends. The precision
> number is real, but the confidence interval is wide and the accent coverage is limited by our
> social circle. We publish the composition rather than implying coverage we don't have.
>
> The check-worthiness gate is trained on ClaimBuster, which is US political debate speech. Our
> domain is interviews. It transfers imperfectly and we report both numbers separately instead of
> quoting the better one.
>
> And broadcast mode mostly says 'unverified', because our reference corpus is small. That's the
> honest outcome at zero budget and exactly what Squash's post-mortem predicts — which is why
> internal consistency is the core and external checking is last on the roadmap and first on the
> cut list."

### 10. "How did two of you work on this without getting in each other's way?"

> "One monorepo with a co-owned `contracts/` package that's the only interface between us, and
> `CODEOWNERS` requiring *both* approvals on it. So I can't change the `Claim` schema without him
> noticing and he can't rename a topic without me noticing. The schema registry enforces backward
> compatibility in CI on top of that, so a breaking change fails in three independent places.
>
> The thing that actually made parallel work possible is that every interface has a fake that
> passes the same contract test suite as the real implementation. He built the entire deployment,
> observability and chaos story against `FakeASR` while I was still choosing a Whisper model. In
> the whole project there are exactly four points where one of us blocks the other, and the only
> unavoidable one is writing the contracts on day one — which we did together in one session."

---

## The short versions

**CV bullet (two sentences):**

> Built **BLAH**, a real-time streaming pipeline that transcribes live speech, extracts factual
> claims as structured records, and detects when a speaker contradicts themselves — p95 under 4
> seconds end to end, on a Kafka-compatible log with replay-based evaluation, backpressure
> shedding, and SLO-driven autoscaling on consumer lag. Alert precision is gated in CI against a
> held-out gold set, and ASR fairness is measured by speaker group with a build-blocking
> threshold.

**LinkedIn version:**

> Two of us — a data engineer and a DevOps engineer, both between jobs — spent our evenings
> building **BLAH: the Bullshit Live Analysis Harness.** It listens to a conversation and tells
> you when someone contradicts something they said twenty minutes earlier, with both quotes and
> the audio, in under four seconds.
>
> The interesting part wasn't the AI. Every model in it is off-the-shelf and frozen — we trained
> nothing. The interesting part was everything around them: where do you cut a continuous speech
> stream into discrete claims? What do you drop when verification is fifty times slower than
> transcription, and how do you tell the user what you dropped? How do you make sure three
> restatements produce one alert instead of three? How do you prove a change made it better
> instead of just different?
>
> The first milestone deliberately contained **no machine learning at all** — fake transcription,
> rule-based detection, real everything else. If the plumbing doesn't work, the models don't
> matter.
>
> Two things we're proudest of are things we chose *not* to build. It doesn't score candidates,
> because ASR word error rates differ by roughly 2× across demographic groups and an automated
> screening tool built on that is a discrimination engine with a dashboard — so the `Alert` schema
> has no field that could hold a score, and our CI fails the build if the word-error-rate gap
> between speaker groups gets too wide. And there's no `FALSE` in our verdict vocabulary; the
> strongest thing it will say is that a statement conflicts with a named source, as of a date,
> with a link.
>
> Code, architecture decisions, and the honest evaluation numbers — including the ones that missed
> target — are all in the repo.

**One line, for a conversation:**

> "It's a streaming pipeline that catches people contradicting themselves in real time — the AI is
> three off-the-shelf models; the project is everything around them."
