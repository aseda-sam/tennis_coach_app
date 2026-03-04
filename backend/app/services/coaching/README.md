# Coaching Service — LLM Intelligence Layer

Turns biomechanics metrics into natural-language coaching feedback via Claude.

## Architecture

```
BiomechanicsReport (DB)
        │
        ▼
┌─────────────────────┐     ┌──────────────────────┐
│  player_history.py  │     │  coaching_service.py  │
│  SQL aggregations   │────▶│  Format → LLM → Log  │
│  (min/max/mean/cnt) │     │                       │
└─────────────────────┘     └──────────┬────────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │    llm_logger.py      │
                            │  JSONL append-only    │
                            │  → eval dataset       │
                            └──────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `coaching_service.py` | System prompt, metric formatting, LLM call, response handling |
| `player_history.py` | Compute-on-the-fly per-metric aggregations from player's past serves |
| `llm_logger.py` | Append every LLM call to `data/llm_logs/coaching_calls.jsonl` |

## How it works

1. Caller provides metrics, phases, moments (from a biomechanics report)
2. `player_history.py` queries the player's historical stats, scoped to
   serves from videos recorded **before** the current serve's video
3. `_format_metrics_for_prompt()` builds a structured text block with:
   - Phase timings + confidence + detected/fallback status
   - Key time points (ball release, trophy, racket low, impact)
   - Metrics with definitions (from `METRIC_DESCRIPTIONS`) and player history
4. Claude generates coaching feedback (single call, no tools)
5. `llm_logger.py` appends the full input/output to JSONL for eval

## Design decisions

### Why metric descriptions exist
Without them, the LLM hallucinates interpretations from metric names.
`toss_laterality: 0.38` was interpreted as "toss behind your body" — it's
actually a left-right measurement. Descriptions tell the model what each
number measures.

### Why no reference ranges
We tried adding "typical range: 0.8-1.5" but these came from general
coaching knowledge, not validated against our measurement system. The model
then judged values against these ungrounded ranges. Removed.

The only valid comparison is the player's own history. External benchmarks
require validated reference data we don't have yet.

### Why player history uses video.recorded_at, not report.created_at
Reports can be (re)created at any time. A video from January processed in
March would have a March `created_at`. Using `recorded_at` ensures history
only includes serves that actually happened before the current one.

### Why JSONL logging
- Human-readable (`jq '.' file.jsonl`)
- Append-only (no schema migrations)
- Loadable into pandas (`pd.read_json('file.jsonl', lines=True)`)
- Each record is a self-contained eval test case
- Good enough until production traffic justifies a proper observability tool

### Why no tools/agents yet
Following anthropic-sdk-patterns.mdc: start with direct Claude API call.
Add tool use when evals show the model needs to query data dynamically
(e.g., looking up what a metric means, fetching comparison serves).

## System prompt constraints

The prompt enforces these behaviors (each is an eval-able assertion):
- Address the player as "you" (never "this player")
- Only discuss metrics with measured values
- No drills/advice for null metrics or low-confidence (<0.5) phases
- Compare to player's own history, not external standards
- Acknowledge data gaps honestly
- Suggest working with a coach for complex changes

## Testing

```bash
# Run against a specific serve window
cd backend
python scripts/test_coaching_feedback.py --serve-window-id 58

# View logged LLM calls
jq '.' data/llm_logs/coaching_calls.jsonl
```

## Next steps

- **Part 2: Eval harness** — deterministic assertions over LLM outputs
  (references data? no drills without data? addresses as "you"?)
- **Camera angle** — pass to coaching service so LLM can caveat
  angle-dependent metrics
- **API endpoint** — `POST /v0/videos/{video_id}/coaching-feedback` via RQ
- **Player goals/profile** — skill level, objectives, serve style context
