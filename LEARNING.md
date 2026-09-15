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

```
LEVEL 0  Two scripts and a pipe          [░░░░░]  0/5    ← you are here
         A pipeline before any infrastructure exists.

LEVEL 1  Why a broker                    [░░░░░]  0/5
         Break the pipe. Feel the loss. Earn Redpanda.

LEVEL 2  Identity, alerts, and honesty   [░░░░]   0/4
         Three restatements, one alert. ═══ M0 COMPLETE ═══

LEVEL 3  Seeing inside it                [░░░░]   0/4
         Metrics, lag, dashboards. B's lane takes the lead.

LEVEL 4  Real ears                       [░░░░]   0/4
         Swap FakeASR for Whisper. Measure. Publish the bad numbers too.

LEVEL 5  Real claims                     [░░░░░]  0/5
         The gate, extraction, canonicalisation.

LEVEL 6  Real contradictions             [░░░░]   0/4
         kNN, NLI, thresholds. ═══ THE PRODUCT WORKS ═══

LEVEL 7+ Warehouse · k8s · chaos · eval gates
         Scoped once we get there. No point planning it now.
```

**Roughly 27 steps to a working product.** At two or three evenings a week that is a real
number of months — and the point is that you can stop at the end of any level and the thing
still runs, still demos, and still has a story.

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
