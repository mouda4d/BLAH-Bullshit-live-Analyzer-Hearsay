# Stack

Every tool, with: what it does **here**, the two obvious alternatives and why they lost, what
complexity it costs us, and how we would run without it.

**Fewer, more boring tools is a virtue.** A list of fashionable technologies with no
justification is the clearest signal of an inexperienced engineer, so the last column —
*"how we'd run without it"* — is the honest one. If we cannot answer it, the tool is load-bearing
and we had better be able to explain why. If the answer is easy, the tool is probably
unnecessary.

The tools we **deliberately did not adopt** are at the bottom, and that list is at least as
important as this one.

---

## Summary

| Layer | Choice | Load-bearing? |
|---|---|---|
| Language | Python 3.12 + Pydantic v2 | Yes |
| Transport | Redpanda (Kafka API) + Schema Registry | Yes — replay, backpressure, fan-out |
| ASR | faster-whisper (CTranslate2) + Silero VAD + LocalAgreement-2 | Yes |
| Check-worthiness | scikit-learn logistic regression on ClaimBuster | No — replaceable by rules |
| Extraction | Ollama + small instruct model, JSON-schema-constrained | **No — `--no-llm` must work** |
| Retrieval | sentence-transformers `all-MiniLM-L6-v2` | Yes |
| Contradiction | `cross-encoder/nli-deberta-v3-base` + deterministic rules | Rules yes, NLI no |
| Serving store | PostgreSQL 16 + `pgvector` | Yes |
| Object store | MinIO (S3 API) | No — replaceable by a volume |
| Lake | Parquet | Yes |
| Marts | dbt-core + DuckDB | Yes for evaluation |
| API/UI | FastAPI + SSE + vanilla JS | Yes |
| Observability | Prometheus + Grafana + OpenTelemetry + Jaeger | Yes |
| Dev orchestration | Docker Compose | Yes |
| Prod orchestration | k3d (k3s) + Kustomize + KEDA | No — the demonstration |
| CI | GitHub Actions | Yes |

---

## Python 3.12 + Pydantic v2

**Here:** every service. Pydantic generates the JSON Schema that is registered with the Schema
Registry, so [`03-DATA-CONTRACTS.md`](03-DATA-CONTRACTS.md) and the running code cannot
diverge — CI regenerates and fails on a diff.

**Alternatives rejected:** *Go* — better for the throughput-oriented services and genuinely
tempting for `archiver` and `loadctl`, but every ML library we need is Python, and two juniors
splitting attention across two languages on evenings is a bad trade. *Rust* — same, more so.

**Costs:** GIL-bound; each stage is a separate process, which we wanted anyway. Slower than the
alternatives at the margins we do not operate at.

**Without it:** we would not do this project. Load-bearing.

---

## Redpanda + Schema Registry

**Here:** the durable, replayable, partitioned log that every stage communicates over, and the
registry that enforces schema compatibility in CI. Consumer-group lag is the metric that drives
both the `LoadController` and KEDA autoscaling.

**Alternatives rejected:** *Apache Kafka* — identical API and semantics; lost purely on JVM +
quorum footprint on laptops already running Whisper and an LLM. **This is not a semantics
argument and we say so** — everything demonstrated here transfers to Kafka, and switching is an
image tag. *NATS JetStream* — ~10 MB binary, genuinely lovely, does support replay; lost because
the consumer-group/offset/partition model and its tooling (`rpk`, `kcat`) are what employers ask
about and what the warehouse sinks expect. **Partly a portfolio decision, stated honestly rather
than dressed up as a technical one.**

**Costs:** ~1-2 GB resident. Partition counts, retention, compaction and rebalancing to
understand — which is the work, for a data engineer.

**Without it:** Postgres as a queue with `SELECT ... FOR UPDATE SKIP LOCKED`. It is the
strongest simple alternative and would genuinely work for the hot path — but it fails on
independent multi-consumer fan-out at different offsets, and on making lag a first-class
observable. Since replay and backpressure are the two things this project is *about*, that
failure is disqualifying. See
[ADR-007](01-DECISIONS.md#adr-007-the-transport--redpanda-not-kafka-not-nats-not-http).

---

## faster-whisper (CTranslate2) + Silero VAD + LocalAgreement-2

**Here:** speech to confirmed text with word-level timings and confidences. Silero VAD (MIT,
~1 MB, CPU, deterministic) does endpointing. LocalAgreement-2 — emit a token only once two
consecutive decoding passes agree — converts a non-streaming model into a streaming one without
retraining anything.

**Model profiles:**

| Profile | Model | Precision | Why |
|---|---|---|---|
| `gpu` (our demo box) | `distil-large-v3` or `large-v3-turbo` | int8_float16 | Turbo cuts decoder layers 32→4 for substantially faster inference at minor accuracy cost — the right trade for a latency-sensitive stream. |
| `cpu` (reviewer, CI) | `base.en` | int8 | Must work with no GPU. Slower and less accurate; **we report both numbers rather than only the good one.** |

**Alternatives rejected:** *whisper.cpp* — excellent and lighter, and a reasonable swap for the
CPU profile; lost on Python integration ergonomics and word-level confidence access, which the
[ASR-confidence gate](01-DECISIONS.md#adr-016-bounding-asr-bias-so-it-cannot-become-a-discrimination-engine)
depends on. *A hosted ASR API* — breaks zero-signup, adds network latency to the hot path, costs
money, and makes replay non-reproducible.

**Costs:** the largest single latency item in the budget and the weakest estimate in it. GPU
VRAM contention with the extractor.

**Without it:** `FakeASR`, which replays a stored transcript with original timings — and **that
is not a hypothetical fallback, it is how M0 is built and how CI runs on every commit.**

---

## Ollama + a small instruct model, JSON-schema-constrained

**Here:** claim extraction only, plus optional Mode B evidence adjudication and alert phrasing.
Ollama's `format` parameter takes a JSON Schema and constrains decoding (XGrammar underneath),
so output **structurally cannot** violate the `Claim` schema. Content quality varies with model
size; structure never does. Temperature 0, fixed seed, version-pinned.

**Alternatives rejected:** *vLLM / SGLang* — faster and the right production answer; lost on
setup weight and VRAM overhead for a single-user laptop. *llama.cpp directly* — fewer layers,
but we would rebuild model management and the HTTP interface ourselves.

**Costs:** ~4-6 GB VRAM. The highest-variance item in the latency budget. An extra container.

**Without it:** `--no-llm` is a **first-class, CI-tested mode**, not a degraded curiosity. Rule
based extraction of numeric/temporal/polarity claims, Stage A contradiction detection only.
Fewer claims, all of them high-precision. Publishing the measured delta between the two modes is
one of the more interesting results this project can produce. See
[ADR-019](01-DECISIONS.md#adr-019-where-the-llm-is-allowed-to-run).

`LLM_ENDPOINT` optionally swaps in any OpenAI-compatible API for demoing from the CPU laptop.
**Default is local; a reviewer needs no account.**

---

## sentence-transformers `all-MiniLM-L6-v2` + `cross-encoder/nli-deberta-v3-base`

**Here:** the two halves of retrieve-then-rescore. MiniLM (22 M params) embeds every claim for
kNN candidate retrieval; DeBERTa-v3-base (184 M params, ~90% MNLI-mismatched) scores the top-8
pairs for `P(contradiction)`.

**Alternatives rejected:** *`nli-deberta-v3-large`* — ~0.5 pp better on MNLI for several times
the latency; not worth it inside an 110 ms budget. *An LLM for the comparison* — 10x slower,
unthresholdable output, non-reproducible under replay, and prone to agreeing with the framing of
the question.

**Costs:** ~1 GB VRAM combined. **Calibration drift** — these are trained on SNLI/MNLI sentence
pairs, not conversational claim pairs, so we set the threshold empirically against our gold set
rather than trusting 0.5.

**Without it:** Stage A rules alone. Materially lower recall, marginally higher precision, and
**a completely honest system.** "We removed the neural component because the rules were better"
would be a good result, not a retreat.

---

## PostgreSQL 16 + pgvector

**Here:** session claim store, embeddings and kNN, entity registry, alert state, audit log.

**Alternatives rejected:** *Qdrant / Weaviate / Milvus* — **rejected specifically and on
principle.** At n < 2,000 vectors per session, an IVFFlat index in Postgres answers in
single-digit milliseconds. Adding a dedicated vector database at this scale is the single
clearest tool-salad signal available, and being able to say *"we did the arithmetic and it did
not justify a service"* is worth more than having the service. *SQLite* — no concurrent writers
across processes.

**Costs:** one container, ~300 MB. The `pgvector` extension image rather than stock Postgres.

**Without it:** SQLite plus a numpy brute-force kNN. Genuinely fine at this n, and it is the
fallback if the container budget gets tight. Load-bearing only because of concurrency.

---

## MinIO + Parquet

**Here:** immutable source audio (the replay substrate) and the Parquet lake.

**Alternatives rejected:** *A plain Docker volume* — simpler and would work; lost because the
S3 API means the production story is one env var away and costs us one small container.
**A borderline call, and it is first on the [cut list](05-ROADMAP.md#the-cut-list).**
*A real cloud bucket* — costs money, breaks zero-signup.

**Costs:** ~200 MB, one more service, one more credential to configure.

**Without it:** a local filesystem path behind the same interface. Genuinely a ten-line change,
which is exactly why it is on the cut list.

---

## dbt-core + DuckDB

**Here:** the dimensional model and marts over the Parquet lake — `mart_precision_by_version`,
`mart_wer_by_group`, `mart_latency_percentiles`, `mart_shed_rate`. The **CI quality gate and the
fairness gate are SQL queries against these.** dbt's `accepted_values` tests enforce the closed
verdict vocabulary at the warehouse boundary — a second, independent place where emitting
`FALSE` fails the build.

**Alternatives rejected:** *Snowflake / BigQuery* — cost money, break zero-signup. **DuckDB over
Parquet is the correct architecture at this scale, not a compromise**, and saying that with
confidence is a better signal than having reached for a warehouse. *Spark* — a JVM cluster for
gigabytes; DuckDB will beat it here and we can explain every line. *ClickHouse* — genuinely good
for this shape; lost on footprint, since DuckDB is a library rather than a server and we are
already running eight services.

**Costs:** a second SQL dialect. dbt is ~a day to learn — the one place where the tool's overhead
is clearly less than what it provides (lineage, tests, docs).

**Without it:** three SQL scripts. If after M4 we find we only ever read the marts from CI and
never by hand, we should do exactly that and say so. See
[ADR-018](01-DECISIONS.md#adr-018-why-there-is-a-batch-warehouse-at-all).

---

## FastAPI + SSE + vanilla JS

**Here:** the operator UI. SSE (not WebSockets) because the data flow is server→client only.

**Alternatives rejected:** *React / Next.js* — a reviewer is here for the pipeline; 5,000 lines
of front-end is 5,000 lines of not-the-point, and it would be the worst code in the repo.
*Streamlit* — fast to write, but it cannot express a live-updating multi-panel view with audio
seek, and it is what LiveFC used, which is part of why LiveFC reads as a demo.

**Costs:** the UI will be plain. Deliberate; stated in the [non-goals](00-PITCH.md#non-goals).

**Without it:** a CLI that prints alerts. The pipeline is unaffected — and `make demo` would
still prove the system works.

---

## Prometheus + Grafana + OpenTelemetry + Jaeger

**Here:** per-stage latency, consumer lag, queue depth, shed rate, verdict staleness, SLO burn
rates. **Trace context propagated in Kafka headers** so a single OTel trace spans capture → ASR →
gate → extract → verify → alert across six services and a broker. Dashboards are JSON in the
repo.

**Alternatives rejected:** *Loki / ELK for logs* — structured JSON to stdout plus traces covers
our needs at a fraction of the footprint; Loki is on the cut list as optional. *Datadog / Grafana
Cloud* — cost money, break zero-signup.

**Costs:** four containers, ~1.5 GB combined. The largest non-ML footprint in the stack.

**Without it:** structured logs and a `/metrics` endpoint you curl. But **the pipeline being
observable is half the project**, so this is as load-bearing as the pipeline itself. See
[ADR-020](01-DECISIONS.md#adr-020-slos-and-autoscaling-on-consumer-lag).

---

## Docker Compose → k3d + Kustomize + KEDA

**Here:** Compose is the default and the reviewer's path — one command, no GPU, no accounts.
k3d (k3s in Docker) is the orchestration demonstration: readiness probes that account for model
warm-up, resource limits, PodDisruptionBudgets, CronJobs for the batch layer, and **KEDA scaling
the extractor on consumer-group lag.**

KEDA is not decoration: it is the direct answer to the backpressure problem, and **CPU-based
autoscaling would be actively wrong here** because the extractor is GPU-bound and its CPU sits
near idle while the queue grows. Being able to explain why HPA-on-CPU fails for this workload is
worth more than the scaler itself.

**Alternatives rejected:** *Helm* — Go templating for six services across three overlays buys
nothing and costs readability. **We would reach for Helm when distributing this for others to
configure** — that is the stated condition. *Full k8s (kubeadm, or a cloud cluster)* — cost and
setup weight; k3d is a real Kubernetes API. *Nomad* — fine, but employers ask about Kubernetes.

**Costs:** a second deployment target to keep in sync. Mitigated by identical images and one
`make` target per target.

**Without it:** Compose only. The system is complete; the DevOps story is thinner. k3d is the
demonstration, not the product.

---

## GitHub Actions

**Here:** lint → type-check → unit → **contract tests** → **schema-registry BACKWARD
compatibility** → integration (`compose up`, run a fixture, assert) → **eval gate (precision must
not regress)** → **fairness gate (WER ratio ≤ 1.5)** → image build + Trivy scan → k3d smoke test.
**Runs CPU-only**, which is what keeps the no-GPU reviewer path honest.

**Alternatives rejected:** *GitLab CI / Drone* — the repo is on GitHub and the free tier is
sufficient. *No CI* — the quality and fairness gates are a large part of what distinguishes this
from a tutorial; they have to block a merge to mean anything.

**Without it:** `make ci` locally, run by discipline. Which is to say, eventually not run.

---

## VRAM budget — the GPU is a contended resource

Three models want the same 8 GB, and pretending otherwise is how the latency budget quietly
fails. Measured at M2; this is the plan.

| Component | Model | Est. VRAM | Resident? |
|---|---|---|---|
| `asr` | distil-large-v3, int8_float16 | ~2.0 GB | **Yes** — load time is seconds |
| `extractor` | small instruct model, 4-bit | ~4.5 GB | **Yes** |
| `hearsay` | nli-deberta-v3-base, fp16 | ~0.5 GB | **Yes** |
| `hearsay` | all-MiniLM-L6-v2 | ~0.1 GB | Yes |
| Headroom | activations, fragmentation | ~0.9 GB | — |
| **Total** | | **~8.0 GB** | Tight by design |

**If contention shows up in measurement, the eviction order is: MiniLM to CPU (negligible), then
DeBERTa to CPU (+~150 ms, affordable), then a smaller extraction model.** ASR never leaves the
GPU — it is the one stage where CPU fallback breaks the budget outright. Having this order
decided in advance is the point.

---

## Deliberately not adopted

At least as important as the list above. Each is a question we expect to be asked.

| Tool | Why not | What would change our mind |
|---|---|---|
| **Apache Airflow / Dagster / Prefect** | Six jobs, dependency graph two levels deep. An orchestrator would add more moving parts than the pipeline it orchestrates. We write the retry/backoff/idempotency wrapper ourselves — ~80 lines — which makes explicit what an orchestrator hides. | **>15 scheduled tasks, or a graph deeper than 3 levels, or windowed backfill with per-task retry state.** Then Dagster. ([ADR-022](01-DECISIONS.md#adr-022-no-workflow-orchestrator-yet)) |
| **Apache Flink / Kafka Streams / Spark Streaming** | We have **no windowed aggregations, no session windows, no time-range joins.** Our entire watermark requirement is a `MIN()` over a small table of in-flight work. Importing a stream processor for a feature we would not use is the clearest tool-salad signal there is. | Any genuinely windowed feature. We have none planned. |
| **A vector database (Qdrant, Weaviate, Milvus)** | n < 2,000 vectors per session. `pgvector` IVFFlat answers in milliseconds. We did the arithmetic. | n in the millions — i.e. cross-session retrieval over a large corpus. |
| **Kubernetes operators / service mesh** | Six services on one node. A mesh would be more infrastructure than application. | Multi-cluster, mTLS requirements, or traffic-splitting needs. |
| **A feature store** | We have no features shared between training and serving, because we train nothing. | If we ever trained anything. We do not. |
| **Airbyte / Fivetran / Kafka Connect** | Our only sink is Parquet and our only source is audio. A 200-line archiver beats a connector framework. | More than ~3 external sources or sinks. |
| **Elasticsearch** | Postgres full-text is sufficient for a session's transcript. | Cross-session search over thousands of sessions. |
| **A message queue *and* a log** (e.g. RabbitMQ alongside Kafka) | One transport. Two would be two failure modes and two mental models. | Nothing at this scale. |
| **Terraform** | There is no cloud infrastructure to provision. Writing Terraform against nothing is theatre. | Deploying to a real cloud — at which point it goes in immediately, and this becomes a different project. |
