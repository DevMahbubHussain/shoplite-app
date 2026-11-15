# Phase 1 Edge Hardening: Order Lifecycle, Queue Resilience & Trace Propagation — Deep Dive & Interview Guide

> **Module:** ShopLite Cloud-Native E-Commerce Platform
> **Repository:** `shoplite-app`
> **Phase:** 1 — Local Foundations & Containerization (edge-hardening increment)
> **Branch:** `feature/order-lifecycle-hardening` (merged to `main`)

---

## Increment 1: Full Order Lifecycle State Machine (`worker/processor.py`, `app/models/order.py`, `app/services/order_service.py`)

### 1. What Was Implemented

Before this increment, the worker jumped straight from `PENDING` to `COMPLETED`, the `FAILED` status was unreachable, and `completed_at` did not exist. We implemented the complete four-state contract (`PENDING → PROCESSING → COMPLETED | FAILED`):

- **`PROCESSING` transition:** `OrderProcessor._fulfill_order` writes `status = 'PROCESSING'` before fulfillment begins, then `'COMPLETED'` on success. `worker/database.py` stamps `completed_at = :updated_at` only on the `COMPLETED` transition via a SQL `CASE` guarded by an explicit boolean parameter (`is_completed`), avoiding asyncpg's ambiguous type inference when one parameter serves both `SET status = $1` and a `CASE WHEN $1 = 'COMPLETED'` comparison.
- **Typed processing outcome:** `ProcessingResult` enum — `SUCCESS`, `RETRY`, `DISCARD` — returned by `process_payload`. The consumer drives queue bookkeeping from the result type instead of a bare boolean:
  - `SUCCESS` → `LREM orders:processing 1 <payload>`.
  - `RETRY` (transient: DB connection lost, timeout) → `LPUSH` the payload back to `orders:pending` **first**, then `LREM` from `orders:processing` (at-least-once ordering), followed by a configurable backoff sleep (`RETRY_DELAY_SECONDS`).
  - `DISCARD` (permanent: unparseable JSON, missing `order_id`, order row absent) → remove the payload; no infinite requeue loop.
- **`FAILED` producer path:** `OrderService.create_order` wraps the `LPUSH` in `try/except`; on enqueue failure it marks the persisted order `FAILED` and returns `503 Service Unavailable`, so no committed row lingers as `PENDING` forever.
- **Schema completion:** `Order.completed_at` (nullable `TIMESTAMPTZ`), `price` migrated `Float` → `Numeric(10,2)` (exact decimal money), `OrderOut.order_id` exposed via Pydantic `@computed_field` alongside `id` to satisfy the documented response contract.
- **Live probes passed:** order observed `COMPLETED` with `completed_at` set; Redis-down order persisted as `FAILED` with `503` to client; a live transient SQL failure was auto-recovered by the retry loop with zero data loss.

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Reliability Pillar (REL06, REL07) & Operational Excellence (OPS03)**
1. **Failure classification is the core of queue semantics.** Treating every exception as "retry forever" produces poison-message livelocks (the message cycles until the queue is unbounded or the worker burns CPU); treating every exception as "discard" silently destroys revenue during transient outages. Production systems must distinguish *transient* (retry with backoff) from *permanent* (dead-letter / discard with telemetry).
2. **`FAILED` must be a real terminal state, not documentation.** An order stuck in `PENDING` forever is a support incident with no signal. A `FAILED` state gives customer service, dashboards, and compensating workflows (refunds, retries) a queryable anchor.
3. **Client-visible degradation beats silent loss.** Returning `503` (retryable) rather than `500`/`200` when the queue is unavailable lets clients and load balancers apply correct retry policy — matching how AWS ALB targets report health and how SQS producers react to `ThrottlingException`.
4. **`NUMERIC(10,2)` for money.** Binary floats cannot represent `0.01` exactly; currency arithmetic in floats accumulates rounding drift — a known root cause of billing incidents. AWS financial workloads standardize on exact decimals end-to-end (and typically `Decimal` + minor-unit integers).

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Explain at-least-once vs at-most-once vs effectively-exactly-once delivery. Which does the ShopLite queue provide, and why is "exactly-once" a misnomer?
**Model Answer:**
- **At-most-once:** fire-and-forget; the message may be lost but never duplicated (e.g. `RPOPLPUSH`-less plain `LPOP` before processing — crash after pop = lost order).
- **At-least-once:** the message is retained until the work is *confirmed* (ack/LREM after commit); a crash between work and ack causes redelivery → duplicates are possible.
- **Effectively-exactly-once:** at-least-once delivery + idempotent processing (dedup key, natural idempotency like `UPDATE ... WHERE id=`, or idempotency keys), so duplicates don't corrupt state.
ShopLite implements at-least-once: the payload is only removed from `orders:processing` (`LREM`) **after** the PostgreSQL commit succeeds. Redis never gives true exactly-once (ack and crash windows are not atomic across systems), and neither does SQS (FIFO gives dedup within a 5-minute window, not a transactional guarantee). The interview phrase to use: *"Exactly-once delivery is a marketing term; what you actually build is at-least-once delivery plus idempotent consumers."*

#### Q2 (Scenario / Troubleshooting): A worker crashes permanently while processing one specific order; on every restart the same order is retried and fails again, blocking nothing but flooding error logs for days. Diagnose and design the fix.
**Model Answer:**
This is the classic **poison message**. Diagnose via the structured error logs (`order_id` + exception class) and queue inspection (`LRANGE orders:processing 0 -1` — the same payload persists across restarts).
- **Root cause classes:** (a) payload the code cannot parse (schema drift, producer bug); (b) referentially impossible work (order row deleted); (c) deterministic business failure (SKU deactivated).
- **Fixes, in production order:**
  1. **Bounded retries with a delivery-count** (Redis `INCR` on a retry key or SQS `ApproximateReceiveCount`) — after N attempts route to a **dead-letter queue** (`orders:dead`) for human triage.
  2. **Fail-fast classification:** malformed payloads should be discarded/DLQ'd immediately without any retry (parsing errors don't heal), which is exactly the `DISCARD` path.
  3. **Alerting on DLQ depth** (`orders:dead` length > 0 for 5m → page), because a silent DLQ is a silent revenue leak.
ShopLite's Phase 1 compromise: permanent failures are discarded with an ERROR log (no DLQ yet); transient failures requeue with backoff. The upgrade path to DLQ is intentionally deferred (YAGNI) until the observability phase can alert on it.

#### Q3 (Deep Architecture): Where should "mark order FAILED" live — the API, the worker, or the database? Defend the boundary.
**Model Answer:**
Each component owns the failures it can *observe*. The API owns enqueue failure (it's the only component present at creation time — it marks `FAILED` and tells the client `503` so the client can retry idempotently). The worker owns processing failure (business/infra errors during fulfillment). The database enforces *state legality* via constraints (e.g. a `CHECK`/trigger preventing `COMPLETED → PENDING` transitions) so no buggy writer can violate the machine. This mirrors AWS service boundaries: each service owns its error semantics; shared state machines are enforced at the datastore, not by convention. The anti-pattern is a "state manager" service that both API and worker call — it becomes a chatty, single point of failure with feature envy across boundaries.

---

## Increment 2: Reliable Queue Resilience (`worker/consumer.py`, `worker/main.py`)

### 1. What Was Implemented

- **Startup recovery sweep:** on boot, `recovery_sweep()` atomically `RPOPLPUSH`es every orphan from `orders:processing` back to `orders:pending` (verified live: injected orphan restored, logged `recovered_count`, then processed to `COMPLETED`).
- **Mid-run retry loop:** transient failures no longer strand payloads in `orders:processing` until restart — the consumer requeues immediately with `RETRY_DELAY_SECONDS` backoff.
- **Idempotent shutdown:** `stop()` is guarded by an `asyncio.Lock`, nulls the Redis client after `aclose()`, and waits for `in_flight` — the SIGTERM handler and the finalizer may both call it (live probe: in-flight order completed, no "Task was destroyed but it is pending" warnings).
- **Signal handling:** `loop.add_signal_handler` on Linux; signal-path tasks are pinned in a reference set (`add_done_callback(discard)`) to avoid asyncio GC collection of fire-and-forget tasks.

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Reliability (REL05, REL07) & Operational Excellence (OPS06)**
1. **Crash-only design:** the system treats crash recovery as a *normal startup path*, not an exceptional manual procedure. The sweep is the same mechanism K8s uses when it reschedules a killed pod — recovery correctness does not depend on clean shutdown ever happening.
2. **K8s termination contract:** Kubernetes sends `SIGTERM`, waits `terminationGracePeriodSeconds` (ShopLite: ≥30s), then sends `SIGKILL`. The worker's `in_flight` drain converts that contract into "no order is half-committed." Without it, `SIGKILL` after grace orphans payloads — which is exactly what the startup sweep then recovers: defense in depth.
3. **The double-buffer (`BRPOPLPUSH`) is the SQS visibility-timeout pattern implemented by hand:** payload sits in a per-work "in flight" list; presence = unacknowledged; sweep = SQS's visibility timeout reappearing messages. Interview framing: *"We built SQS semantics on Redis lists because the platform is self-managed; if we migrate to SQS (Bonus Track), the consumer abstraction (`QueueConsumerInterface`) swaps without touching business logic."*

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Why `BRPOPLPUSH`/`BLMOVE` instead of `RPOP` followed by processing?
**Model Answer:**
`RPOP` destructively removes the payload from Redis; if the worker crashes before completing the order, the payload is gone — lost revenue. `BRPOPLPUSH` moves the payload atomically (single server-side command, no TOCTOU window) from `pending` into `processing`, where it persists as an *unacknowledged-work ledger*. Completion is then acknowledged by `LREM`. The blocking `B` variant avoids busy-polling: the connection parks server-side until a payload arrives or the timeout elapses, yielding a clean loop that also checks the shutdown flag every ≤2s instead of spinning.

#### Q2 (Scenario): After `kubectl scale deployment order-worker --replicas=4`, the HPA scales back to 1 and an order vanishes from `orders:pending` but never completes. Walk through the diagnosis.
**Model Answer:**
1. `LLEN orders:processing` — if > 0, the payload is mid-flight from a worker that died during scale-in. `LRANGE orders:processing` shows the payload and its `timestamp` field — a stale timestamp means an orphan.
2. Confirm the worker lifecycle: `kubectl get pods -w` during scale-in shows `SIGTERM` at a random moment; if a pod was killed between `BRPOPLPUSH` and `LREM`, the payload is stranded.
3. Recovery: the surviving worker's startup sweep only runs on *boot*. If the remaining worker never restarted, the orphan waits until the next restart. Hardening options: run the sweep periodically (e.g. reclaim payloads older than `visibility_timeout`), or have each worker sweep on a timer — this is precisely SQS visibility-timeout behavior and is the natural Phase 3 upgrade.
4. Root-cause fix stays the same: shorten the ack window (commit → LREM back-to-back), keep grace period ≥ max processing time (1–2s delay + DB write ≪ 30s).

#### Q3 (Deep Dive): Why does the requeue path `LPUSH` to pending *before* `LREM` from processing — and what failure window remains?
**Model Answer:**
The ordering guarantees at-least-once: if the worker crashes between the two commands, the payload exists in **both** lists — after restart, the sweep returns the `processing` copy and the consumer processes it again → duplicate processing (safe because the terminal write is idempotent: `UPDATE orders SET status='COMPLETED' WHERE id=?`). The reverse order (`LREM` first) has a window where the payload exists in *neither* list — a crash there loses the order permanently. Remaining window in the chosen order: one duplicate execution, mitigated by idempotent writes. This is the standard "crash between ack and requeue" analysis for any broker (Kafka commits offset after process; SQS changes visibility).

---

## Increment 3: W3C Trace Context Propagation Through Redis (`app/observability/tracing.py`, `app/services/queue_service.py`, `worker/processor.py`)

### 1. What Was Implemented

- The OTel `TracerProvider` is installed **unconditionally** in both services; the OTLP exporter to Tempo is attached only when `OTEL_ENABLED=true`. Spans always exist locally (logs carry real `trace_id`s) even before the Tempo collector is deployed in Phase 4.
- `FastAPIInstrumentor.instrument_app(app)` creates the HTTP `SERVER` span per request; `RedisInstrumentor().instrument()` creates `redis.lpush`/`brpoplpush` client spans.
- `POST /orders` → `TraceContextTextMapPropagator().inject(carrier)` writes the active `traceparent` into the JSON payload pushed to `orders:pending`; the worker extracts it (`extract(carrier)`) and opens `worker_process_order` as a **child span**.
- **Verified live at the wire:** the raw payload in Redis read `traceparent: "00-e50d456d…-240bfbb0…-03"`, and the worker's completion log for that order printed `trace_id: e50d456d…` — the same trace across HTTP → Redis → worker.

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Operational Excellence (OPS05, OPS08) — Observability**
1. **Cross-boundary correlation is the entire point of tracing.** A trace that stops at the API returns "nothing wrong here" while the failure lives in the async worker. Propagating W3C `traceparent` through the queue makes the *order*, not the *request*, the unit of investigation — one `trace_id` joins HTTP handler, Redis enqueue, worker processing, and the Postgres write.
2. **W3C TraceContext is vendor-neutral:** the same header works with X-Ray (via ADOT), Jaeger, Tempo, and Datadog. Injecting it into the message payload (rather than relying on broker headers Redis doesn't preserve for lists) keeps the propagation mechanism portable to SQS (where it becomes a message attribute).
3. **Provider-always-on:** installing the SDK even when disabled means `trace_id` in JSON logs (constraint C10's mandatory key) is always populated, so Loki→Tempo correlation (C11's derived field) works the day Tempo lands — no code change required.

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Break down the `traceparent` value `00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01`.
**Model Answer:** `version-traceid-parentspanid-traceflags`: `00` = version 0; the 32-hex `traceid` identifies the whole end-to-end transaction; the 16-hex `parentspanid` identifies the immediate calling span (the API's server span); `01` = sampled (final "01" bit set). The worker uses `traceid` to join the trace and `parentspanid` to parent `worker_process_order` under the API's server span, reproducing the causality chain in Tempo. Propagators also handle `tracestate` (vendor-specific extension list) transparently.

#### Q2 (Scenario / Troubleshooting): The trace exists for `POST /orders` and for the worker span, but they appear as two disconnected traces in Tempo. What are the plausible causes, ranked by likelihood?
**Model Answer:**
1. **Extraction ignored:** worker parses the payload but builds the span with default context (empty carrier) — the classic "inject without extract" bug; check that `extract_trace_context(carrier)` result is passed as `context=` to `start_as_current_span`.
2. **No active span at injection time:** the producer injected with no recording span (missing `instrument_app`) — the payload's `traceparent` is empty, so the worker starts a fresh root. Verify by inspecting the raw queue payload (`LRANGE`).
3. **Clock skew / ordering:** spans exported with divergent clocks can fall outside Tempo's per-trace query window; verify timestamps on spans.
4. **Sampling mismatch:** API sampled (`flags 01`), worker's provider configured with a different sampler forcing unsampled — the trace exists but the worker span isn't stored.
5. **Multiple collector pipelines with different tenant/storage** in multi-env setups (dev trace written to dev Tempo while you query prod).

#### Q3 (Deep Architecture): Why propagate trace context through the Redis *payload* instead of Redis message headers or a sidecar key?
**Model Answer:**
Redis list primitives carry only opaque strings — there is no header/metadata envelope like AMQP properties or SQS message attributes. Options: (a) embed in the JSON payload (chosen: self-describing, survives payload copies verbatim, travels with the order to SQS later as a message attribute); (b) a parallel hash (`order:{id}:meta`) — breaks atomicity, introduces cleanup obligations and read amplification; (c) MDC-style ambient context — impossible across a process boundary where the consumer must *choose* to resume context. Embedding keeps the carrier and the data co-located and atomic — one `LPUSH`, one truth.

---

## Increment 4: Metrics & Middleware Correctness (`app/middleware/`, `worker/metrics.py`)

### 1. What Was Implemented

- **Middleware ordering:** `ChaosMiddleware` is added before `MetricsMiddleware` (Starlette: last-added = outermost), so chaos-injected `500`s traverse the metrics middleware and are counted in `http_requests_total{status="500"}` — without this, a `CHAOS_ERROR_RATE` exercise would show no 5xx spike and the `HighErrorRate` alert would never fire.
- **Route label resolution:** the hand-rolled `route.matches(scope)` loop mislabeled every request as `/openapi.json`; replaced with Starlette's own routing decision — `request.scope["route"].path` after `call_next` — giving correct low-cardinality labels (`route="/products"` verified live).
- **Dedicated worker registry:** worker metrics register in a private `CollectorRegistry` passed to `start_http_server`, because `order_queue_depth` also exists in the API process; loading both modules into one interpreter (unit tests) would otherwise raise `DuplicateTimeseries`.
- **Silent-failure removal:** metrics port bind failures now log a warning instead of vanishing behind `except: pass`.

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Operational Excellence (OPS08) — Golden Signals**
1. **An alerting pipeline is only as trustworthy as its weakest recording rule.** If chaos-injected faults are invisible to the metrics that feed `HighErrorRate`, the Q8 RCA exercise is undemonstrable — observability must observe the faults it is meant to catch.
2. **Label cardinality is a Prometheus out-of-memory vector:** a raw-path label (`route="/products/123"`, scanner garbage, UUIDs) explodes time series unboundedly. Template paths (`/products/{id}`) keep cardinality proportional to *code*, not *traffic*. (Known deferred nit: unmatched 404s still use the raw path — acceptable until a scrape-hardening pass.)
3. **Metric identity:** Prometheus metrics are global singletons per process by name; two modules declaring the same metric in one process collide. Separate registries per service module mirror per-service reality — each service exposes its own `/metrics` endpoint in production.

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Explain the four golden signals and map each to a ShopLite metric and alert.
**Model Answer:**
1. **Latency** — `http_request_duration_seconds` histogram → p95 > 1.0s for 5m (`HighLatency`, warning).
2. **Traffic** — `http_requests_total` rate → RPS panel, capacity planning / HPA signal.
3. **Errors** — `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` > 5% (`HighErrorRate`, critical).
4. **Saturation** — `order_queue_depth` gauge > 50 for 10m (`QueueBacklog`, warning) — for a queue-driven system, pending depth is the saturation signal; container memory/CPU covers node saturation.
Histograms give server-side percentile math via `histogram_quantile()` without storing every sample — buckets are the accuracy/cost tradeoff.

#### Q2 (Scenario): Prometheus shows `http_requests_total{route="/openapi.json"}` climbing while no client ever requests OpenAPI. What's the defect class and how do you prove it?
**Model Answer:**
A **telemetry instrumentation defect**: the middleware's route attribution resolves every request to the same label, so all real traffic (healthchecks, orders) is recorded under a wrong, constant route. Prove it by joining sources: ALB/ingress logs show traffic distribution by real path while Prometheus shows one label absorbing everything — a attribution-only mismatch (requests still served 200/201). Fix: use the framework's authoritative route record (Starlette stores the matched route in `scope["route"]` during routing) rather than re-implementing matching in middleware. Lesson for interviews: *monitor the instrumentation itself* — dashboards can lie when the emitter is buggy; cross-check against an independent source (access logs, ALB metrics) during incident triage.

#### Q3 (Deep Dive): Counter vs Gauge vs Histogram vs Summary — when does each lie to you?
**Model Answer:**
- **Counter:** only goes up (except process restart reset — client librariress handle `rate()` resets). Lies if you compute averages from instant values instead of `rate()`.
- **Gauge:** instant value, can go down. Lies when sampled sparsely — a queue that drains between scrapes never shows depth (why ShopLite's worker updates the gauge every loop iteration, and why the API-side gauge is stale-by-design between orders — the worker's is authoritative).
- **Histogram:** client-side bucketing, enables `histogram_quantile` across instances, cheap server-side. Lies at bucket boundaries: p95 quantization error = bucket width; tune buckets around your SLO (ShopLite buckets 0.1→10s cover the 1–2s processing window).
- **Summary:** client-side quantiles, exact — but **not aggregatable** across instances (quantiles don't sum), so they break in multi-replica K8s. Default to histograms.

---

## Increment 5: Verification Infrastructure (`pytest.ini`, `tests/`, `scripts/smoke-test.sh` probes)

### 1. What Was Implemented

- **Single-invocation test runs:** both services had a `tests` package with `__init__.py` — two top-level packages named `tests` collide in one pytest process (`ModuleNotFoundError: tests.test_worker`). Fixed with pytest `pythonpath = services/catalog-api services/order-worker` + `--import-mode=importlib` + removing both `__init__.py`. The worker package rename `app/` → `worker/` (canonical layout) also de-conflicted the two services' `app` packages. Suite: **27 tests, one command, < 6s**, including new scenario tests: PROCESSING→COMPLETED transition ordering, poison-discard without DB call, transient-retry classification, consumer requeue, and SIGTERM in-flight completion.
- **Live probe discipline (C6/C7):** SIGTERM mid-processing (order completed before exit), recovery sweep with injected orphan, `/readyz` 503 with Redis stopped and recovery to 200, Redis-down order → `FAILED` + client `503`, stdout JSON purity check (0 non-JSON lines on both services), image sizes 95/139/144 MB < 150 MB, smoke test green end-to-end.

### 2. Why This Is Critical (AWS & Cloud-Native Production Alignment)

#### AWS Well-Architected Framework: **Operational Excellence (OPS10 — test everywhere) & Reliability (REL12)**
1. **CI readiness:** a pipeline that can only run tests via two separate invocations will get "fixed" in CI by someone hiding one suite. Importability collisions (`tests`, duplicate `app` packages) are exactly the class of defect CI surfaces on day one — fixing them locally is an order of magnitude cheaper.
2. **`importlib` import mode:** pytest's classic prepend mode inserts the test file's directory on `sys.path`, so same-named test modules shadow each other; importlib imports by derived unique module name — the documented solution for duplicate basenames.
3. **Tier separation:** unit tests prove *logic* (fast, no infra); smoke tests prove *integration* (real Postgres, Redis, HTTP); live probes prove *failure semantics* (SIGTERM, orphan recovery) that no unit test can honestly simulate. A green `make test` with a red `make smoke` is a broken contract — which is why the milestone gate is `make up && make smoke`.

### 3. Interview Questions & Comprehensive Model Answers

#### Q1 (Foundational): Why do liveness and readiness probes need different semantics, and what breaks if you merge them?
**Model Answer:**
Liveness (`/healthz`) answers "is the process wedged?" — must be dependency-free and return 200 immediately; readiness (`/readyz`) answers "can this pod take traffic right now?" — checks Postgres/Redis and returns 503 otherwise. Merging them breaks availability in two directions: (a) checking dependencies in liveness → a Postgres blip makes the kubelet *restart* healthy pods (crash loop during an upstream outage); (b) removing dependency checks from readiness → pods receive traffic they cannot serve (orders 500) — the exact state `readyz` exists to prevent. During Redis-down, ShopLite demonstrates both correctly: `healthz` 200, `readyz` 503, zero restarts.

#### Q2 (Scenario): A graceful shutdown works with `docker compose stop` but orders still go missing when Kubernetes evicts a pod under load. Enumerate the checklist.
**Model Answer:**
1. `terminationGracePeriodSeconds` ≥ worst-case processing time (1–2s delay + DB write; 30s is ample).
2. The container actually forwards `SIGTERM` to the Python process — PID 1 must be a signal-aware init (our CMD runs `python -m worker.main` directly; with shell-form CMD, `/bin/sh -c` may not forward signals).
3. The shutdown handler *drains* (waits for in-flight) rather than just setting a flag the loop checks eventually.
4. Redis client closed only **after** the final `LREM`/commit — premature `aclose()` turns clean drain into connection errors.
5. Endpoints/scale-in race: a pod removed from the Service Endpoints may still hold an in-flight request — readiness gate flip must precede drain (preStop hook `sleep 5` if needed).
6. Residual safety net: the startup sweep recovers anything SIGKILLed after grace — recovery semantics never assume graceful shutdown happened.

#### Q3 (Deep Dive): Why is `docker logs shoplite-catalog-api` producing 100% parseable JSON now important, and what breaks in Phase 4 if a single plain-text line leaks in?
**Model Answer:**
Promtail/Grafana Alloy ships stdout lines to Loki where the JSON parsing pipeline (`json` stage) extracts `level`, `service`, `trace_id` as labels/structured metadata. A non-JSON line fails the pipeline stage: it's either dropped (lost log) or stored unparsed (unfilterable noise) — and because the Loki→Tempo derived field matches `trace_id` regex, unparseable lines are invisible to trace correlation. Mixed-format stdout typically comes from the framework's own logger (uvicorn access/startup lines) — the fix is `--no-access-log` plus routing app logs through the single structured formatter. Operational rule: *stdout is a machine interface*, not a human log.

---

## Phase 1 Edge-Hardening Synthesis: Verification Matrix

| Control | Implementation | Verification Evidence | Failure Mode Prevented |
| :--- | :--- | :--- | :--- |
| **Order state machine** | `PROCESSING` write + `completed_at` on `COMPLETED` | psql row shows `COMPLETED` + timestamp; unit test asserts call order | Orders that never visibly transition; unqueryable completion time |
| **Transient failure policy** | `RETRY` → requeue with backoff | Live SQL failure auto-recovered after worker restart, zero loss | Data loss during DB outage |
| **Permanent failure policy** | `DISCARD` w/o requeue + ERROR log | Unit test: malformed payload never touches DB | Poison-message infinite loop |
| **Enqueue failure policy** | order marked `FAILED`, client `503` | Live probe: Redis stopped → order 7 `FAILED`, HTTP 503 | Orphaned `PENDING` rows, silent loss |
| **Orphan recovery** | Startup `RPOPLPUSH` sweep | Injected orphan restored (`recovered_count: 1`), completed | Stranded payload after crash/SIGKILL |
| **Graceful termination** | Lock-guarded drain, signal-aware PID 1 | SIGTERM probe: in-flight completed, no destroyed tasks | Half-committed orders on redeploy |
| **Trace propagation** | W3C `traceparent` in payload | Raw `LRANGE` shows header; worker log trace_id matches | Un-correlatable async failures |
| **Chaos visibility** | Chaos inner to metrics middleware | `http_requests_total{status="500"}` increments under `CHAOS_ERROR_RATE` | Blind chaos exercise; unalertable error rate |
| **Metric route labels** | `scope["route"].path` attribution | `/healthz`, `/products` labels verified live | Cardinality blowup, lying dashboards |
| **Probe semantics** | Dependency-aware `readyz`, bare `healthz` | 503/200 Redis-outage probe | Restart storms, traffic to unhealthy pods |
| **JSON log purity** | Single formatter, uvicorn access off | 0 non-JSON stdout lines, both services | Broken Loki ingestion in Phase 4 |
| **Image budget** | Multi-stage, stripped venvs | 95/139/144 MB < 150 MB | Slow pulls, larger attack surface |
