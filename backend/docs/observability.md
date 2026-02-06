# Observability (OpenTelemetry + structured logs)

Single source of truth for observability setup and usage. Use this doc when adding instrumentation or debugging "where did the time go?"

## Overview

We use **OpenTelemetry (OTel)** for distributed tracing and metrics, sending telemetry to **Grafana Cloud** (free tier). Logs are enhanced with canonical IDs (`trace_id`, `span_id`, `request_id`, `job_id`, `video_id`) so they correlate with traces.

**What you get:**

- **Traces**: See API request → enqueue → worker pipeline → DB/storage, with stage breakdowns (download → scout → refine → db_write)
- **Metrics**: Job counts (started/succeeded/failed) and durations (histogram) visible in Grafana Prometheus
- **Correlated logs**: Search logs by `trace_id` or `job_id` to find all related events

**Provider dashboards** (Fly, Upstash Redis, Supabase) stay for infra health; **our instrumentation** gives end-to-end request/job stories.

## Architecture

### Stack

- **OpenTelemetry (OTel)** in app code: traces + metrics; vendor-neutral
- **Backend** (where telemetry is sent): **Grafana Cloud** free tier (or OTLP to any compatible backend)
- **Logs**: Existing Python logging enhanced with **trace_id / request_id / job_id / video_id** for correlation

### Services

- **`tennis-coach-api`**: FastAPI app with auto-instrumentation (HTTP request spans)
- **`tennis-coach-worker`**: RQ worker with root span per job + stage spans

### Data Flow

1. **API request** → FastAPI auto-instrumentation creates trace → enqueue job → return response
2. **Worker picks up job** → `_rq_job_span()` creates root span → `_stage_span()` for each pipeline stage → metrics recorded → flush on completion
3. **All telemetry** → OTLP exporter → Grafana Cloud (Tempo for traces, Prometheus for metrics)

## Canonical IDs (use everywhere)

When adding logs or spans, attach the relevant subset of these so we can search by job/video/trace:

| ID           | Where                                 | Purpose                                   |
| ------------ | ------------------------------------- | ----------------------------------------- |
| `trace_id`   | OTel context (API + worker)           | Link all spans for one request or job     |
| `span_id`    | OTel context                          | Current span (for log correlation)        |
| `request_id` | API only (`request.state.request_id`) | Human-friendly; already in `X-Request-ID` |
| `job_id`     | VideoJob.id (DB)                      | Our job identity                          |
| `rq_job_id`  | RQ job id                             | Queue/worker identity                     |
| `video_id`   | Video.id                              | Which video is being processed            |

## Code Conventions

### Logging

- **API routes**: Use `get_log_extra(request_id=..., video_id=..., job_id=...)` to add IDs to log statements
- **Worker tasks**: Always include `video_id` and `job_id` via `get_log_extra()`
- **Automatic**: `trace_id` and `span_id` are added by `ObservabilityLogFilter` (no need to include manually)

### Tracing

- **API routes**: Automatic via FastAPI instrumentation (`FastAPIInstrumentor`)
- **Worker tasks**: Use `_rq_job_span()` for root span, `_stage_span()` for pipeline stages (`download`, `scout`, `refine`, `detect_serves`, `db_write`)

### Metrics

- Use `record_job_started()`, `record_job_succeeded()`, `record_job_failed()` from `app.utils.metrics`
- Record metrics for all background jobs (`pose_detection`, `scout_refine`, `transcode_video`)

### Best Practices

1. **Always include IDs**: Every log/span should have `video_id` (and `job_id` in workers)
2. **No PII**: Never log tokens, passwords, full URLs with tokens, or raw user data
3. **Stage spans**: Wrap major pipeline stages so Grafana shows "where did time go?"
4. **Metrics on all jobs**: Record start/success/failure for every background job
5. **Silent failures**: OTel/metrics failures should not break the app (they're optional)

## Environment Variables

Required for OTel to work (without them, tracing/metrics are no-op):

- `OTEL_SERVICE_NAME` — e.g. `tennis-coach-api` or `tennis-coach-worker`
- `OTEL_EXPORTER_OTLP_ENDPOINT` — Grafana Cloud OTLP endpoint (e.g. `https://otlp-gateway-<region>.grafana.net/otlp`)
- `OTEL_EXPORTER_OTLP_HEADERS` — e.g. `Authorization=Basic <token>` for Grafana Cloud
- `OTEL_EXPORTER_OTLP_PROTOCOL` — e.g. `http/protobuf` (default)
- `OTEL_RESOURCE_ATTRIBUTES` — Optional: `service.namespace=tennis-coach` or `deployment.environment=production`

Optional:

- `OTEL_TRACES_SAMPLER` (e.g. `parentbased_traceidratio`)
- `OTEL_LOG_LEVEL`
- `RQ_DEQUEUE_TIMEOUT` — Worker polling interval (default: 60s)

## Using Grafana

### Metrics (Prometheus data source)

Use when you want **aggregated answers**: "How many jobs started/succeeded/failed?" "How long do jobs take on average?" "Is the worker keeping up?"

**Example queries:**

- `jobs_started_total{service_name="tennis-coach-worker"}`
- `jobs_succeeded_total{service_name="tennis-coach-worker"}`
- `job_duration_seconds{job_type="scout_refine"}` (histogram for p50/p95/p99)
- `queue_wait_seconds{job_type="scout_refine"}` (time jobs spent waiting in queue)

### Traces (Traces / Tempo data source)

Use when you want **one request or job, step by step**: "Why was this job slow?" "Which stage (download, scout, refine, db_write) took the time?"

**Example queries:**

- `{resource.service.name="tennis-coach-api" && name="POST /v0/videos/upload"}` — API upload traces
- `{resource.service.name="tennis-coach-worker"}` — All worker job traces
- `{resource.service.name="tennis-coach-worker" && name="rq.scout_refine"}` — Scout/refine jobs only

**In practice:** Start with metrics to see "is something wrong?" then use traces to see "what exactly happened for that one execution?"

### Service Graph vs Job-Level Flow

- **Service graph** (Traces data source → Service Graph tab): Shows which _services_ call which (e.g. API ↔ worker). For us, the "call" from API to worker is enqueue → Redis → worker.
- **Job-level flow** (what we have now): Each worker job produces **one trace** with **stage spans**: download → scout → refine → db_write. Open a trace in Explore → Traces to see the timeline.

## Differentiating Local / Docker vs Production

- **Service name** already separates API (`tennis-coach-api`) from worker (`tennis-coach-worker`)
- To separate **environment** (e.g. local/Docker vs production), set a resource attribute:
  - **Production (e.g. Fly):** In Fly secrets, add `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production` (append to existing if you already set `service.namespace=tennis-coach`)
  - **Local / Docker:** In backend `.env` you can set `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=development` (or leave unset)
- In Grafana (metrics and traces) you can then filter by `deployment.environment=production` or `development` so local testing doesn't mix with production

## Troubleshooting

### No traces in Grafana

- **Docker**: After adding OTel deps you must **rebuild** the backend image: `docker compose build backend` then `docker compose up`
- **Logs**: On startup, look for either **"OpenTelemetry tracer configured (service=..., endpoint=...)"** (success) or **"OpenTelemetry setup failed: ..."** (see the exception)
- **Auth**: Use exactly the header Grafana gives you, e.g. `OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64>`. Values are URL-unquoted automatically (e.g. `%20` → space)
- **Traffic**: Hit the API (e.g. `GET /`, `GET /health`, or any route) so spans are generated; traces can take 1–2 minutes to show in Grafana

### No metrics in Grafana

- **Worker running**: Ensure worker has same `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` as API
- **Jobs executed**: Metrics only appear after jobs run (they're recorded when `record_job_started` / `record_job_succeeded` are called)
- **Export delay**: Metrics are exported every 30 seconds; wait ~1 minute after jobs run before querying

## Reference Files

- **Logging filter**: `backend/app/utils/logging_context.py` (`ObservabilityLogFilter`, `get_log_extra()`)
- **Metrics helpers**: `backend/app/utils/metrics.py` (`record_job_started`, `record_job_succeeded`, `record_job_failed`, `record_queue_wait`)
- **OTel setup**: `backend/app/utils/otel.py` (`setup_otel_tracing()`)
- **Worker spans**: `backend/app/services/rq_tasks.py` (`_rq_job_span()`, `_stage_span()`)
