# The route

`docs/` is the **destination** — the finished reasoning, written to survive an interview.
This file is the **route** — one evening at a time, learning first.

If you are lost in `docs/`, that is expected. Do not read it front to back. It is an answer
key, and answer keys are miserable to learn from. Read a piece of it **after** the step that
earns it.

---

## The one rule

> **Never introduce a tool before you have felt the problem it solves.**

Every step follows the same shape:

```
feel the pain  →  build the smallest fix  →  read the ADR that names what just happened
```

You cannot defend "we chose Kafka because we needed replay" in an interview if you have never
lost data without it. You *can* defend it if you spent an evening piping two scripts together,
killed one mid-run, and watched forty records vanish. Same sentence, completely different
answer, and a panel can tell the difference in about nine seconds.

This is also why `docs/01-DECISIONS.md` has a "What would change our mind" section in every
ADR. Those are the questions you will be able to answer once you have felt the trade-off from
both sides.

---

## Calibration — who you are, and what this project is actually for

Assessed from your CVs (September 2026). Neither of you is as junior as you think, and that
changes the route.

### Mahmoud — DE

| | |
|---|---|
| **Already strong** | Dimensional modeling, SCD 0–3, dbt (incremental models, snapshots, check-strategy SCD2, point-in-time joins), T-SQL incl. dynamic SQL, Medallion, Azure/Snowflake, Airflow, Power BI |
| **Best CV item** | The inventory ETL — it has a *consequence* ("still in use, they asked for a maintainer"). Lead with it. |
| **Gap 1 — the big one** | **100% batch. Zero streaming.** No events, no offsets, no consumers anywhere. Streaming on top of your existing modeling skill is a different salary band. |
| **Gap 2** | **Python as an analyst, not an engineer.** No pytest, no services, no packaging, no type-driven design. This is what loses take-homes. |
| **So your lane is** | Stream semantics and Python service craft. **Not the warehouse** — see below. |

### Abdelrahman — DevOps

| | |
|---|---|
| **Already strong** | K8s, Helm, Kustomize, Terraform, Ansible, GitHub Actions, ArgoCD, Prometheus/Loki — and unusually, supply-chain security (OpenSSF Scorecard, Semgrep, Terrascan, SARIF, Dependabot, seccomp/read-only rootfs/dropped caps) |
| **Also** | You already write FastAPI with unit **and** integration pytest suites. That is exactly the skill Mahmoud lacks. |
| **Gap 1** | **No employment history**, so projects carry all the weight — which raises the bar on them being *yours*, not a roadmap's. |
| **Gap 2** | **Everything you have built is request/response.** Stateful streaming ops is a different animal and a rarer skill. |
| **So your lane is** | Streaming-specific operations, plus mentoring Mahmoud on software craft. |

### The HiveBox rule

HiveBox is mid-flight and currently covers MinIO, Helm, Kustomize, Grafana/Loki and Terraform.
BLAH asks for MinIO, Kustomize, Grafana and k3d. **That is the same work twice and the same CV
bullets twice.**

> **Do not re-derive anything HiveBox already proves.** Lift the patterns wholesale —
> Dockerfiles, CI workflow structure, security jobs. Then spend the saved evenings on the four
> things HiveBox structurally cannot teach: **consumer-group lag as an SLI**, **KEDA scaling on
> lag rather than CPU**, **backpressure and shedding**, and **chaos + tracing across a stateful
> pipeline with a broker in the middle.**

### Lanes follow gaps, not strengths

`docs/08-WAYS-OF-WORKING.md` splits the work along your strengths. **That is right for shipping
and wrong for learning**, so while we are learning, we invert it:

- **Mahmoud does not touch the warehouse layer until Level 7.** dbt marts and star schemas are
  already on your CV. Building them again teaches you nothing and costs you months.
- **Abdelrahman teaches software craft** — pytest, FastAPI, packaging, type hints — as part of
  PR review, not as a separate exercise. This is what real teams do and it is good for both of
  you: teaching it is how you find out whether you actually know it.

We switch back to strength-based lanes at Level 7, when the goal changes from learning to
finishing.

---

## How a step works

1. **One concept.** Named at the top. If a step teaches two things, it is two steps.
2. **One small thing to build.** Target: 30–90 minutes. If it is taking three evenings, tell
   me and I will split it.
3. **You build it. I do not.** I describe the shape and the trap to avoid. You write the code.
   The typing is where the learning is.
4. **You show me.** Paste it, or tell me it works. I review it like a colleague would — what
   breaks, what you would not be able to debug at 2am, what is simpler than you made it.
5. **Then you read the ADR.** It will land differently than it did today.

Progress is tracked at the top of each level. You can stop after any level and still have
something honest to show.

---

## The ladder

Levels 0–2 add up to **M0** — a complete, working, demo-able system with **no machine learning
in it at all**. That is not a warm-up. It is the milestone, and it is the one most projects
skip.

**M** = Mahmoud leads · **A** = Abdelrahman leads · **BOTH** = you both do it, separately, then
compare. Comparing two solutions to the same small problem is the cheapest learning in the plan.

```
LEVEL 0  Two scripts and a pipe          [░░░░░]  0/5   BOTH   ← you are here
         A pipeline before any infrastructure exists.
         M: ~1 evening per step.  A: collapse steps 1–3 into one evening.

LEVEL 1  Why a broker                    [░░░░░]  0/5   M leads, A reviews
         Break the pipe. Feel the loss. Earn Redpanda.

LEVEL 2  Identity, alerts, and honesty   [░░░░]   0/4   M leads, A reviews
         Three restatements, one alert.      ═══ M0 COMPLETE ═══

LEVEL 3  Seeing inside it                [░░░░]   0/4   A leads
         Lag as an SLI. Not CPU. The rarest thing in this project.

LEVEL 4  Real ears                       [░░░░]   0/4   M leads
         Swap FakeASR for Whisper. Measure. Publish the bad numbers too.

LEVEL 5  Real claims                     [░░░░░]  0/5   M leads
         The gate, extraction, canonicalisation.

LEVEL 6  Real contradictions             [░░░░]   0/4   M leads, A on load
         kNN, NLI, thresholds.               ═══ THE PRODUCT WORKS ═══

LEVEL 7+ Warehouse · k8s · chaos · eval gates        ← lanes flip to strengths here
         M finally gets to use dbt. A gets KEDA and game days.
         Scoped once we get there. No point planning it now.
```

**Roughly 27 steps to a working product.** At two or three evenings a week that is a real number
of months — and the point is that you can stop at the end of any level and the thing still runs,
still demos, and still has a story.

**Abdelrahman, on being ahead:** Levels 0–2 will feel slow to you, and you should still do them.
Not for the Python — for the semantics. Offsets, event time vs processing time, and why a
restatement is not a duplicate are things you will otherwise be operating without understanding,
and Level 3 is unbuildable if you skip them. Your compensation is that Level 3 is yours alone and
it is the most distinctive thing either of you will build.

---

## Level 0 — Two scripts and a pipe

**Goal of the level:** build BLAH's entire architecture in about sixty lines of Python, with no
Docker, no broker, no models, nothing to install but Python. By the end you will have a
producer, a consumer, a contract between them, and a real contradiction detected.

Everything after Level 0 is *replacing pieces of this with sturdier pieces*, and knowing that
is worth more than any diagram in `docs/`.

---

### Step 1 — A stream is just records with timestamps

**Concept.** "Streaming" sounds like infrastructure. It is not. A stream is records that arrive
one at a time, in order, with a time attached — and the time is part of the *data*, not the
clock on the wall. That distinction is the whole of event time vs processing time, and you can
learn it tonight with `print()`.

**Build:** `labs/01/play.py`

A script that reads a JSON file of transcript lines and prints them **paced as if someone were
speaking them** — line at 3.2s appears 3.2 seconds after start.

Make the fixture yourself, `labs/01/fixture.json`. Typing it out is two minutes and you will
read it properly, which is the point:

```json
[
  {"t_ms": 1000,  "speaker": "S0", "text": "So tell me about your Kafka experience."},
  {"t_ms": 4200,  "speaker": "S1", "text": "I ran our Kafka estate for about four years at Acme."},
  {"t_ms": 9000,  "speaker": "S1", "text": "Three clusters, I was the one paged when it broke."},
  {"t_ms": 15000, "speaker": "S0", "text": "What was the hardest incident?"},
  {"t_ms": 19000, "speaker": "S1", "text": "Honestly I've never actually operated Kafka myself."},
  {"t_ms": 23000, "speaker": "S1", "text": "We had a platform team that owned all of that."}
]
```

**Two traps, both deliberate:**

1. **Do not `sleep(t_ms)` per record.** You want the *gap* between records, not the absolute
   time. Get this wrong and the last line appears 72 seconds in instead of 23. Fixing it
   yourself is the exercise.
2. **Print `t_ms` alongside the text.** You will be tempted to print just the words. The
   timestamp is the part that matters — it is the field the entire system is built around.

**Done when:** `python labs/01/play.py` prints six lines over ~23 seconds, each tagged with its
media time, and the last line lands about 23 seconds after you hit enter.

**Then notice:** you just wrote a producer. It has a pacing policy, an ordering guarantee, and
a record schema that only exists in your head so far. Step 3 will put that schema somewhere
real.

**Read after:** nothing yet. Genuinely — do not open `docs/`. Step 2 first.

---

### Step 2 — A pipeline is stages with a boundary

*(Unlocked when you show me Step 1. Preview so you can see where this is going: a second
script that reads `play.py`'s output and shouts when it sees a contradiction, connected with
`python play.py | python detect.py` — a Unix pipe, which is a real stream with real
backpressure and will teach you more about both than a week of Kafka tutorials.)*

---

## What I need from you

- **Your CVs**, so I can calibrate where each of you starts, split the two lanes sensibly, and
  aim some of the steps at gaps that keep appearing in the roles you want. They will not be
  committed to this repo or quoted in any doc.
- **Step 1**, when it runs.
- **"This is too slow" or "this is too fast"**, whenever it is true. The step size is a guess
  until you tell me otherwise.
