# Ways of working

Two people, no manager, different evenings, indefinite timeline. **The process is part of the
portfolio.** A reviewer reading the git history and the PR record learns more about whether we
can work on a team than any bullet point claims to.

The goal is to reproduce what a functioning engineering organisation actually feels like at the
smallest scale it can exist at: a **co-owned interface between two teams**, review that is not a
formality, decisions written down before code, and operational practice that is rehearsed rather
than improvised.

We are deliberately not cargo-culting Scrum. No story points, no sprints, no burndown. Those
exist to coordinate groups larger than two.

---

## Repository layout

One monorepo. The directory boundaries *are* the team boundaries.

```
blah/
├── contracts/          # ★ CO-OWNED — both approvals required
│   ├── events.py           # Pydantic models: Envelope, Utterance, Claim, Verdict, Alert
│   ├── enums.py            # VerdictStatus, ReasonCode, ClaimType, SourceTier
│   ├── topics.py           # topic names, keys, partition counts, cleanup policy
│   ├── protocols.py        # ASRStage, Extractor, Verifier
│   ├── fakes/              # FakeASR, FakeExtractor, FakeVerifier
│   ├── schemas/            # generated JSON Schema — CI fails if stale
│   └── tests/              # the contract suite: fakes AND reals run it
├── services/
│   ├── ingest/         # B   consent gate, capture, framing
│   ├── asr/            # A   whisper + VAD + LocalAgreement
│   ├── gate/           # A   check-worthiness
│   ├── extractor/      # A   claims
│   ├── hearsay/        # A   the contradiction engine
│   ├── almanac/        # A   external verifier
│   ├── alerter/        # A   dedup, suppression, versioning
│   ├── loadctl/        # B   the degradation controller
│   ├── archiver/       # B   topics → Parquet
│   └── api/            # B   SSE + UI
├── warehouse/          # A models, B jobs
├── eval/               # A   harness, metrics, gates
├── deploy/             # B   compose/, k8s/, keda/, grafana/, chaos/
├── fixtures/           # shared — transcripts, labels, consent manifests, fetch.py
├── docs/               # shared — ADRs need a PR
└── Makefile            # the only interface a reviewer needs
```

### CODEOWNERS

```
*                     @person-a @person-b     # one approval from the other
/contracts/           @person-a @person-b     # ★ BOTH approvals
/docs/01-DECISIONS.md @person-a @person-b     # ★ BOTH — ADRs are decisions, not notes
/docs/03-DATA-CONTRACTS.md @person-a @person-b # ★ BOTH
/services/asr/ /services/gate/ /services/extractor/ /services/hearsay/ /services/almanac/ /services/alerter/ @person-a
/services/ingest/ /services/loadctl/ /services/archiver/ /services/api/ @person-b
/deploy/              @person-b
/eval/                @person-a
```

**This is the mechanism that makes the interface real.** A cannot change the `Claim` schema
without B noticing; B cannot rename a topic without A noticing. It is the closest thing to a
platform-team/application-team relationship that two people can construct, and it is the thing
that will still be working in month five when enthusiasm has worn off.

---

## Branching and pull requests

**Trunk-based, short-lived branches, squash merge.** No long-running feature branches — with two
people working alternate evenings, a branch alive for a week is a merge conflict with a timer on
it.

```
main                    ← protected, always green, always demo-able
  ├── feat/claim-fingerprint
  ├── fix/asr-endpoint-wait
  └── docs/adr-023-diarization
```

**Branch protection on `main`:** no direct pushes, CI must pass, one approval required (two on
`contracts/`), branches must be up to date before merge.

**A PR should be reviewable in under twenty minutes.** If it is bigger than that, it is two PRs.
This matters more for us than for a normal team: the reviewer is reading it at 10pm after their
own day, and a 900-line PR gets rubber-stamped, which means the review was theatre.

**Conventional commits**, because they generate the changelog and make `git log` a readable
project history — which a reviewer *will* read:

```
feat(hearsay): add numeric range comparison to rule detector
fix(asr): correct media_time offset after LocalAgreement confirm
perf(extractor): batch NLI pairs, p95 240ms → 80ms
docs(adr): ADR-023 diarization stability gating
chore(deploy): pin redpanda to v25.x
```

### What a review is for

Not style — the formatter handles that. A reviewer is asking:

1. Does this match the contract, and if it changes one, is that change in an ADR?
2. Can I run it? Is there a test that would fail if it broke?
3. Will I be able to debug this at 2am? Is there a metric or a log line when it goes wrong?
4. Is this the simplest thing that works, or does it import a tool we do not need?

**"I don't understand this" is a valid and important review comment.** Both of us have to be able
to explain every part of this system in an interview, including the parts we did not write. That
is a real constraint and it should block a merge.

---

## The ADR process

**Architectural decisions get written before the code, not after.**

1. Someone opens a PR adding an ADR to [`01-DECISIONS.md`](01-DECISIONS.md), status
   `PROPOSED`, in the standard format: **Context → Decision → Alternatives rejected →
   Consequences → What would change our mind.**
2. The other reviews it as a decision, not as prose. The most valuable comment is *"what about
   X?"* against the alternatives section.
3. Merged as `ACCEPTED`, or `PROVISIONAL` when it rests on an unmeasured estimate — in which case
   it names the milestone that will measure it.
4. Implementation PRs reference the ADR.
5. **Superseded ADRs are marked superseded, never deleted.** The history of a decision being
   revised is more valuable than the decision looking correct from the start — and it is visible
   in git, which is the point.

**When we disagree and cannot resolve it:** write both positions into the ADR's *Alternatives*
section, pick one explicitly, and state what evidence would flip it. Then build the one we
picked. A disagreement converted into a falsifiable condition is worth more than a disagreement
won. `01-DECISIONS.md` is full of these — every "What would change our mind" is one.

---

## CI — what actually blocks a merge

Ordered fastest-to-slowest, so failures surface early. **Runs CPU-only**, which is what keeps the
no-GPU reviewer path honest.

| # | Gate | Blocks? | Catches |
|---|---|---|---|
| 1 | `ruff` + `mypy --strict` | Yes | The usual |
| 2 | **No-wall-clock lint** — no `datetime.now()` in stage logic | **Yes** | Silently breaking replay reproducibility |
| 3 | Unit tests, incl. the canonicalisation case table | Yes | Core logic |
| 4 | **Contract tests — fakes AND reals, same suite** | **Yes** | A fake that has rotted; an implementation that drifted |
| 5 | **Schema Registry BACKWARD compatibility** | **Yes** | An incompatible schema reaching the broker |
| 6 | Generated JSON Schema is not stale | Yes | Docs and code disagreeing |
| 7 | Integration: `compose up`, run a fixture, assert an alert | Yes | Wiring |
| 8 | **`--no-llm` mode integration** | **Yes** | The deterministic floor rotting unnoticed |
| 9 | **Eval gate: held-out alert precision ≥ 0.90** | **Yes** | A change that made quality worse |
| 10 | **Fairness gate: `max_group_wer / min_group_wer` ≤ 1.5** | **Yes** | The discrimination risk, [R1](06-EVALUATION-AND-RISK.md#r1--asr-accuracy-varies-by-accent-and-dialect) |
| 11 | Latency: p95 regression > 20% | Yes | Slow creep |
| 12 | dbt tests, incl. `accepted_values` on `verdict.status` | Yes | `FALSE` ever being emitted |
| 13 | Image build + Trivy scan | Warn | CVEs |
| 14 | k3d smoke test | Yes on `main` | Deployment drift |

Gates 9 and 10 are the ones that make this more than a tutorial. **A quality gate that does not
block is a suggestion**, and suggestions do not survive a tired Tuesday.

---

## Definition of done

A change is done when **all** of these are true. It is a checklist in the PR template, not a
sentiment.

- [ ] Tests exist that would fail if this broke
- [ ] If it touches a contract, the ADR is merged and both owners approved
- [ ] It emits a metric or a structured log line when it goes wrong
- [ ] The failure mode is in the table in [`02-ARCHITECTURE.md`](02-ARCHITECTURE.md#failure-modes)
- [ ] `make demo` still works on a clean clone
- [ ] `--no-llm` still works
- [ ] The other person can explain it

That last box is unusual and it is the most important one. **We are both going to be interviewed
about all of this.**

---

## Cadence

No sprints. A rhythm.

| When | What | Why |
|---|---|---|
| **Weekly, 30 min** | **Demo day.** Each of us demos what we built to the other. Working software, not a status update. | Forces integration to be continuous. You cannot demo a branch you never merged. |
| Weekly, same call | **Next-up.** Pick the next few issues each. No estimates, no points. | Two people do not need a planning ceremony. |
| Per milestone | **Milestone review.** Walk the "done means" checklist honestly. Run the held-out eval. Update the ADRs whose estimates were measured. | Stops a milestone from being "basically done" for three weeks. |
| Per milestone | **Game day.** One breaks something without telling the other; the other diagnoses from dashboards alone. | Below. |
| Ad hoc | **Pairing**, for `contracts/` and anything neither of us understands | Day-one contracts are the only truly serialised work in the project. |

**Issues live on a GitHub Projects board** with four columns — Backlog, Next, In progress, Done —
and every issue is labelled with its milestone and owner. Not because two people need a kanban
board, but because a reviewer opening the repo can see how the work was actually broken down,
and that is genuinely informative about how we think.

---

## Game days and on-call

The most valuable practice in the whole process, and it costs an hour.

**The exercise:** one of us picks a failure from the table in
[`02-ARCHITECTURE.md`](02-ARCHITECTURE.md#failure-modes) and injects it — without saying which.
The other is "on call", starts from a dashboard alert, and has to diagnose and remediate using
only the runbook and the observability stack. **Reading the source is not allowed.** Roles swap
each milestone.

**Afterwards, a write-up, committed to `docs/incidents/`:**

```markdown
# INC-003 — Verdict lag breached SLO-3 for 4 minutes
**Injected:** 2s latency added to the Ollama endpoint (toxiproxy)
**Detected:** SLO-3 burn-rate alert, 45s after injection
**Time to diagnosis:** 6m 20s
**What worked:** loadctl walked AMBER→RED as designed; no claims lost (conservation held)
**What did not:** the dashboard showed extractor lag but not *why*; we had no panel for
  LLM call latency specifically, so 4 of those 6 minutes were spent guessing.
**Action:** add `blah_llm_call_latency_ms` panel — #47
```

> **A junior portfolio with committed incident write-ups is unusual enough to be memorable.** It
> demonstrates the thing that is hardest to claim on a CV: that you have operated something, not
> just built it. The write-ups that say *"our dashboards were not good enough"* are worth more
> than the ones that went smoothly.

---

## How the two roles actually split

Not "A does data, B does infra" — that is too vague to prevent collisions.

| | **A — data engineer** | **B — DevOps engineer** |
|---|---|---|
| **Owns** | Correctness of the data | Correctness of the system |
| **Answers** | "Is this claim right? Is this alert justified?" | "Is it running? Is it fast? Did we lose anything?" |
| **Artifacts** | Schemas, extraction, verification, dbt models, eval harness, gold set | Transport, deployment, observability, CI, chaos, replay tooling |
| **Interview story** | Streaming semantics, claim modelling, evaluation design, precision/recall trade-offs | SLOs, backpressure, autoscaling on lag, failure injection, incident response |
| **Gets paged for** | The precision gate failing | The latency gate failing |

**Both** own: `contracts/`, the ADRs, the demo, and being able to explain the entire system.

The deliberate overlap — the replay harness is built by B but exists to serve A's evaluation
work; the load controller is B's but its priority function is A's — is where the interesting
conversations happen, and it is realistic. **Real teams have seams, and the seams are where
people learn.**

---

## Things we will do that feel like overkill at two people, and why

| Practice | Why it is not overkill |
|---|---|
| PR review with a required approval | The point is the record of it, and the discipline. Both of us have to defend code we did not write. |
| CODEOWNERS requiring both on `contracts/` | Schema drift between two people on alternate evenings takes about a fortnight. |
| ADRs before code | The ADRs *are* the portfolio. [`01-DECISIONS.md`](01-DECISIONS.md) is the most valuable file in the repo. |
| Schema registry compatibility checks | It is the mechanism, not the ceremony. Three independent enforcement points for the most dangerous change class. |
| Incident write-ups | They demonstrate operation, not just construction. Almost no junior portfolio has them. |
| A changelog | A reviewer can see the project's actual history in ninety seconds. |

## Things we deliberately will not do

Story points. Sprints. Burndown charts. Stand-ups. A RACI matrix. Retrospectives with sticky
notes. **All of these exist to coordinate more than two people, and performing them at two would
be exactly the kind of unexamined cargo-culting this project is otherwise arguing against.**
