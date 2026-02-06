# Observability (OpenTelemetry + structured logs)

Single source of truth for what we’re building and how it fits together. Use this doc when adding instrumentation or debugging “where did the time go?”

## Goal

- **Unified view**: one place to see API request → enqueue → worker pipeline → DB/storage, correlated by IDs.
- **Provider dashboards** (Fly, Upstash Redis, Supabase) stay for infra health; **our instrumentation** gives end-to-end request/job stories.

## Stack choice

- **OpenTelemetry (OTel)** in app code: traces + optional metrics; vendor-neutral.
- **Backend** (where telemetry is sent): **Grafana Cloud** free tier (or OTLP to any compatible backend). No self-hosted Prometheus/Loki unless we decide otherwise.
- **Logs**: keep existing Python logging; add **trace_id / request_id / job_id / video_id** so logs correlate with traces. No need to replace current logs—OTel adds correlation.

## Canonical IDs (use everywhere)

| ID | Where | Purpose |
|----|--------|---------|
| `trace_id` | OTel context (API + worker) | Link all spans for one request or job |
| `span_id` | OTel context | Current span (for log correlation) |
| `request_id` | API only (`request.state.request_id`) | Human-friendly; already in `X-Request-ID` |
| `job_id` | VideoJob.id (DB) | Our job identity |
| `rq_job_id` | RQ job id | Queue/worker identity |
| `video_id` | Video.id | Which video is being processed |

When adding logs or spans, attach the relevant subset of these so we can search by job/video/trace.

## Implementation plan (order of work)

1. **Setup (you)**  
   - Sign up for **Grafana Cloud** (free tier).  
   - In Grafana Cloud: **Get started → connect data**, or **Connections → OpenTelemetry / OLP**. Get:
     - **OTLP endpoint URL** (e.g. `https://otlp-gateway-<region>.grafana.net/otlp`)
     - **API token** (or Instance ID + API key) for sending traces.
   - Add env vars (see below) in backend `.env` (local) and Fly secrets (API + worker); no code change until step 2.

2. **API (first code change)**  
   - Add OTel SDK + FastAPI instrumentation so every HTTP request gets a trace.  
   - Ensure `request_id` is on the trace (span attribute) and in response headers (already done).  
   - Keep existing logging; add `trace_id`/`span_id` to log records where easy (e.g. middleware or a small logging filter).

3. **Worker (second code change)**  
   - In RQ task: create a **root span per job**; set attributes `job_id`, `video_id`, `rq_job_id`.  
   - Add **spans per pipeline stage** (e.g. download, decode, pose, ball, DB write, upload).  
   - Pass through or recreate trace context from enqueue time if we want one trace from API → worker; otherwise worker-only traces are acceptable to start.

4. **Logging conventions**  
   - Structured fields: `timestamp`, `level`, `service` (api|worker), `trace_id`, `span_id`, `request_id` (API), `job_id`/`video_id` (worker).  
   - No PII in logs or span attributes (no raw tokens, emails, full URLs with tokens).

5. **Metrics (optional, after traces)**  
   - Counters: `jobs_started`, `jobs_succeeded`, `jobs_failed`.  
   - Histograms: `job_duration_seconds`, `queue_wait_seconds`.  
   - Gauges: queue depth / active jobs if available.

## Environment variables (reference)

- `OTEL_SERVICE_NAME` — e.g. `tennis-coach-api` or `tennis-coach-worker`.  
- `OTEL_EXPORTER_OTLP_ENDPOINT` — Grafana Cloud OTLP endpoint (or collector).  
- `OTEL_EXPORTER_OTLP_HEADERS` — e.g. `Authorization=Basic <token>` for Grafana Cloud.  
- Optional: `OTEL_TRACES_SAMPLER` (e.g. `parentbased_traceidratio`), `OTEL_LOG_LEVEL`.

## Cursor rules / code conventions

- **backend-patterns**: Routes must have trace/request context; RQ tasks create their own root span and set `job_id`/`video_id`.  
- **observability**: New rule doc (optional) can require: include canonical IDs in logs/spans, no PII, use OTel for traces (not ad‑hoc timing logs).

## Status

- [x] Grafana Cloud account + OTLP endpoint/token  
- [x] API: OTel SDK + FastAPI auto-instrumentation (main.py + FastAPIInstrumentor)  
- [x] Worker: OTel in worker process; root span per job (rq.pose_detection, rq.scout_refine) + job_id/video_id/rq_job_id; flush on job end  
- [x] API: trace_id/span_id in logs via ObservabilityLogFilter  
- [x] Worker: stage spans (download, scout, refine, detect_serves, db_write)  
- [x] Logging: structured fields (trace_id, job_id, video_id) in key log lines via get_log_extra()  
- [x] Metrics: job counts (started/succeeded/failed) and durations (histogram) with OTLP exporter to Grafana Cloud  
- [x] Docs: link from `backend/docs/README.md`  
- [x] Cursor: observability rule (`.cursor/rules/observability.mdc`) + backend-patterns note

## What to use when (metrics vs traces)

- **Metrics (Prometheus data source)**  
  Use when you want **aggregated answers**: “How many jobs started/succeeded/failed?” “How long do jobs take on average?” “Is the worker keeping up?”  
  Example: `jobs_started_total`, `jobs_succeeded_total`, `job_duration_seconds` in Explore with data source **grafanacloud-asedasam-prom**.

- **Traces (Traces / Tempo data source)**  
  Use when you want **one request or job, step by step**: “Why was this job slow?” “Which stage (download, scout, refine, db_write) took the time?”  
  Open a trace for a specific job/request and look at the spans; use `trace_id` to find related logs if needed.

- **In practice:** Start with metrics to see “is something wrong?” then use traces to see “what exactly happened for that one execution?”

## Service graph vs job-level flow

- **Service graph (Traces data source)**  
  In Explore with the **Traces** data source, the “Service Graph” tab shows which *services* call which (e.g. API → something). For us, the “call” from API to worker is enqueue → Redis → worker, so the graph may show tennis-coach-api and tennis-coach-worker; full API→worker flow in one trace would require propagating trace context from API to the job (future improvement).

- **Job-level flow (what we have now)**  
  Each worker job already produces **one trace** with **stage spans**: download → scout → refine → db_write (or pose_detection → db_write for pose-only). In Explore → Traces, open a trace and you see that timeline. So “flow” today is: per-job trace with stages; service graph is the higher-level “which service talks to which.”

## Differentiating local / Docker vs production

- **Service name** already separates API (`tennis-coach-api`) from worker (`tennis-coach-worker`).
- To separate **environment** (e.g. local/Docker vs production), set a resource attribute when running in production, and optionally in local/Docker:
  - **Production (e.g. Fly):** In Fly secrets (or env), add for example  
    `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production`  
    (append to existing `OTEL_RESOURCE_ATTRIBUTES` if you already set `service.namespace=tennis-coach`).
  - **Local / Docker:** In backend `.env` you can set  
    `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=development`  
    (or leave unset if you prefer).
- In Grafana (metrics and traces) you can then filter by `deployment.environment=production` or `development` so local testing doesn’t mix with production.

## Troubleshooting: no traces in Grafana

- **Docker**: After adding OTel deps you must **rebuild** the backend image so the container has the packages:  
  `docker compose build backend` then `docker compose up` (or `up -d backend`).  
  The compose file already loads `backend/.env` via `env_file`; no extra compose config needed.
- **Logs**: On startup, look for either **"OpenTelemetry tracer configured (OTLP endpoint=...)"** (success) or **"OpenTelemetry setup failed: ..."** (see the exception).
- **Auth**: Use exactly the header Grafana gives you, e.g. `OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64>`. Values are URL-unquoted automatically (e.g. `%20` → space).
- **Traffic**: Hit the API (e.g. `GET /`, `GET /health`, or any route) so spans are generated; traces can take 1–2 minutes to show in Grafana.
