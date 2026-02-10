# Progress Overview — Spec & Implementation Details

Design principles are in `.cursor/rules/progress-overview.mdc`. This doc describes the data model, API contract, and implementation as built.

## Data model

No dedicated progress tables. Progress is derived from:

- **Source of truth**: `ServeAttempt` joined with `Video.recorded_at` for ordering.
- **Aggregation**: Averages, trends, and consistency are computed per time window in the backend.
- **Time windows**: "Last 7 days", "Last 30 days", "All time" — filtered by `Video.recorded_at`.
- **Grouping**: Metrics are grouped by video; each video is one data point on trend charts.

## Metrics (Phase 1)

| Metric | Source field | Shown on overview |
|--------|--------------|-------------------|
| Elbow Angle at Contact | `ServeAttempt.elbow_angle_at_contact` | Avg degrees + trend |
| Knee Bend Rate | `ServeAttempt.knee_bend_detected` | % of serves with bend + trend |
| Court Side Distribution | `ServeAttempt.court_side` | Court diagram |

New metrics (e.g. ball toss height, contact height) follow the same card/chart patterns.

## Frontend

### Page structure

```
Overview/
  Overview.tsx
  Overview.css
  components/
    TimeFilter.tsx      # 7d / 30d / All time
    MetricCard.tsx       # Stat card (value, trend, consistency)
    TrendChart.tsx       # Line chart over time (recharts)
    CourtSideDiagram.tsx # SVG court with serve distribution
    ConsistencyReport.tsx
```

### Charts and animation

- **Charts**: recharts (no D3). Chart theme comes from design-tokens.css.
- **Chart entrance**: recharts `isAnimationActive` with ~800ms duration.
- **Number count-up**: CSS or a light hook (no heavy animation lib).
- **Metric cards**: Fade-in on mount with staggered delay.
- **Transitions**: Design token durations (`--transition-normal`, `--transition-slow`).

### Empty and low-data states

- **&lt; 2 videos**: Prompt to upload more (“Upload a few more serves to start tracking your progress”).
- **Some serves missing a metric**: Show data from serves that have it; note sample size.
- **No data**: Prominent upload CTA instead of an empty dashboard.

## Backend

### Endpoint

`GET /v0/progress/me` — aggregated progress for the authenticated user.

**Query params**

- `time_period`: `7d` | `30d` | `all` (default: `30d`)
- `player_id`: optional UUID (defaults to user’s primary player)

### Response shape

```json
{
  "time_period": "30d",
  "total_serves": 41,
  "total_videos": 4,
  "metrics": {
    "elbow_angle": {
      "current_avg": 145.2,
      "previous_avg": 141.8,
      "trend": "improving",
      "consistency": 6.1,
      "consistency_rating": "good",
      "data_points": [
        {"date": "2026-01-22", "avg": 142.0, "count": 8},
        {"date": "2026-02-04", "avg": 146.5, "count": 12}
      ]
    },
    "knee_bend": {
      "current_rate": 0.85,
      "previous_rate": 0.72,
      "trend": "improving",
      "data_points": []
    }
  },
  "court_side": {
    "deuce": 22,
    "ad": 19,
    "unknown": 0
  }
}
```

- `trend`: `"improving"` | `"declining"` | `"stable"`
- `consistency_rating`: `"excellent"` | `"good"` | `"fair"` | `"needs_work"`

### Service and logic

- **Service**: `ProgressService` in `backend/app/services/progress_service.py` does all aggregation; the route has no business logic.
- **Trend**: Current window is compared to the previous equivalent window (e.g. last 30d vs. 30d before). Improving &gt; 3% better, declining &gt; 3% worse, else stable. For elbow angle, “better” means moving toward the 140–170° range.
- **Consistency** (elbow angle std dev): Excellent σ ≤ 5, Good 5 &lt; σ ≤ 10, Fair 10 &lt; σ ≤ 15, Needs work σ &gt; 15.
