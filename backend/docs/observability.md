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
   - Create an OTLP endpoint / token for traces (and optionally metrics).  
   - Add env vars (see below); no code change required for “just export”.

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

- [ ] Grafana Cloud account + OTLP endpoint/token  
- [ ] API: OTel SDK + FastAPI auto-instrumentation  
- [ ] API: trace_id/span_id in logs (optional filter)  
- [ ] Worker: root span per job + stage spans  
- [ ] Worker: job_id/video_id on spans and in logs  
- [ ] Docs: link from `backend/docs/README.md`  
- [ ] Cursor: observability rule (optional) + backend-patterns note
