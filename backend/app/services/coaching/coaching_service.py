"""Coaching service — turns biomechanics data into coaching feedback via LLM.

This is intentionally simple: one prompt, one LLM call, one output.
No chains, no agents, no retrieval. We'll add complexity only when
evals tell us we need it.
"""

import logging
import time
from typing import Any, Optional

import anthropic
from pydantic import BaseModel

from app.core.config import settings
from app.services.coaching.llm_logger import log_llm_call

logger = logging.getLogger(__name__)

COACHING_SYSTEM_PROMPT = """\
You are a tennis serve coach analyzing biomechanics data from a video.
You receive structured data: phase timings, key time points, and raw metrics
from pose estimation. You are speaking directly to the player.

Your job:
1. Assess whether the metrics show anything worth addressing. If values are
   consistent with the player's history and nothing stands out, say so —
   not every serve needs a correction. If there IS something notable,
   identify at most 1-2 things to focus on.
2. Explain WHY in simple language (reference the specific data values)
3. Give ONE specific drill or practice cue for each issue — but ONLY if the
   underlying metric has a measured value. If the metric is null or the phase
   has low confidence, do NOT recommend a drill. Instead, note that the data
   is insufficient.

Constraints:
- Address the player as "you" throughout. Never say "this player" or "the player".
- Be concise. You should spend time on court, not reading.
- ONLY discuss metrics that have actual measured values. If a metric is null,
  acknowledge it briefly and move on. Do not speculate about what the value
  might be or give advice based on missing data.
- If a phase was not detected (detected=false) or has low confidence (<0.5),
  do not give technique advice for that phase. Simply note the data gap.
- Never invent data you weren't given.
- When historical ranges are provided ("Your history"), use them to put the
  current serve in context. Say whether this serve is typical, above, or below
  the player's own range. Do NOT judge values against external standards —
  only compare to this player's own data.
- Do NOT judge whether a metric value is "high", "low", "good", or "bad" unless
  the player's historical range is provided AND has at least 3 serves. Without
  sufficient history, simply report the value and note that more data is needed
  to assess it.
- You're a coach-prep tool, not a live coach. Suggest working with a coach
  on complex technique changes.
- Use plain language. No jargon without explanation.
"""


class CoachingFeedback(BaseModel):
    """Result of a coaching LLM call."""

    feedback: str
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int


def _get_client() -> anthropic.Anthropic:
    """Get or create the singleton Anthropic client."""
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to backend/.env")
    if not hasattr(_get_client, "_client"):
        _get_client._client = anthropic.Anthropic(  # type: ignore[attr-defined]
            api_key=settings.ANTHROPIC_API_KEY
        )
    return _get_client._client  # type: ignore[attr-defined]


# Human-readable descriptions so the LLM knows what each metric means.
# Without these, the model guesses from the metric name and hallucinates.
# IMPORTANT: Do NOT add reference ranges (e.g. "typical: 110-130°") here.
# We tried this and the model used ungrounded ranges to judge values.
# The only valid comparison is the player's own history (via player_history.py).
# Add ranges only when we have validated reference data from our own pipeline.
METRIC_DESCRIPTIONS: dict[str, str] = {
    "knee_flexion_min_deg": (
        "Minimum knee bend angle during the toss phase. "
        "180° = fully straight leg, lower = deeper bend."
    ),
    "toss_peak_height": (
        "Ball peak height above shoulders, normalized by player height "
        "(shoulder-to-ankle distance). 0 = shoulder level, 1.0 = one full "
        "body-height above shoulders."
    ),
    "toss_drop": (
        "How far the ball dropped from its peak to the contact point, "
        "normalized by player height. Larger values mean the ball fell "
        "further before contact. Compare to your own history only."
    ),
    "toss_laterality": (
        "Horizontal distance of ball from shoulder center at peak, normalized "
        "by player height. 0 = directly above shoulders, positive = to the "
        "right of center. This is a LEFT-RIGHT measurement only (not "
        "front-back). Only meaningful when video is recorded from behind."
    ),
}


def _format_metrics_for_prompt(
    metrics: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    moments: list[dict[str, Any]],
    *,
    history: Optional[dict[str, dict[str, Any]]] = None,
) -> str:
    """Format biomechanics data into a readable prompt section.

    This is where we control what the LLM sees. Keeping it structured
    and readable helps the model reason about the data.
    """
    lines = []

    # Phases
    lines.append("## Serve Phases")
    for p in phases:
        detected = "detected" if p.get("detected") else "fallback"
        lines.append(
            f"- {p.get('phase_label', p.get('phase', '?'))}: "
            f"{p.get('start_timestamp', '?'):.2f}s - {p.get('end_timestamp', '?'):.2f}s "
            f"(confidence: {p.get('confidence', 0):.0%}, {detected})"
        )

    # Key moments
    lines.append("\n## Key Time Points")
    for m in moments:
        ts = m.get("timestamp")
        if ts is not None:
            lines.append(
                f"- {m.get('moment_label', m.get('moment', '?'))}: "
                f"{ts:.2f}s (confidence: {m.get('confidence', 0):.0%})"
            )
        else:
            lines.append(
                f"- {m.get('moment_label', m.get('moment', '?'))}: not detected"
            )

    # Metrics grouped by phase
    lines.append("\n## Metrics")
    by_phase: dict[str, list[dict[str, Any]]] = {}
    for m in metrics:
        phase = m.get("phase") or "general"
        by_phase.setdefault(phase, []).append(m)

    for phase, phase_metrics in by_phase.items():
        lines.append(f"\n### {phase}")
        for m in phase_metrics:
            name = m["metric_name"]
            val = m.get("value")
            unit = m.get("unit", "")
            desc = METRIC_DESCRIPTIONS.get(name, "")
            if val is not None:
                lines.append(f"- {name}: {val:.1f}{unit}")
            else:
                lines.append(f"- {name}: null (not measurable)")
            if desc:
                lines.append(f"  Definition: {desc}")
            # Add player's historical range if available
            hist = (history or {}).get(name)
            if hist and hist["count"] >= 3:
                lines.append(
                    f"  Your history ({hist['count']} serves): "
                    f"min={hist['min']}, max={hist['max']}, mean={hist['mean']}"
                )

    return "\n".join(lines)


def generate_coaching_feedback(
    *,
    metrics: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    moments: list[dict[str, Any]],
    serve_window_id: Optional[int] = None,
    history: Optional[dict[str, dict[str, Any]]] = None,
) -> CoachingFeedback:
    """Call the LLM to generate coaching feedback from biomechanics data.

    Args:
        history: Per-metric historical stats from get_player_metric_history().
            If provided, the prompt includes the player's personal ranges.

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not configured.
        RuntimeError: If the LLM API call fails.
    """
    client = _get_client()

    formatted_data = _format_metrics_for_prompt(
        metrics, phases, moments, history=history
    )
    user_message = (
        "Here is the biomechanics analysis for this serve:\n\n"
        f"{formatted_data}\n\n"
        "Based on this data, what should this player focus on?"
    )

    try:
        start = time.perf_counter()
        response = client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=settings.LLM_MAX_TOKENS,
            system=COACHING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        latency_ms = (time.perf_counter() - start) * 1000
    except anthropic.APIError as e:
        raise RuntimeError(f"Coaching LLM call failed: {e}") from e

    content_block = response.content[0]
    output_text = content_block.text  # pyright: ignore[reportAttributeAccessIssue]
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens

    # Log for evals
    log_llm_call(
        input_data={
            "metrics": metrics,
            "phases": phases,
            "moments": moments,
            "history": history,
        },
        output_text=output_text,
        model=settings.LLM_MODEL,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        serve_window_id=serve_window_id,
    )

    logger.info(
        "Coaching feedback generated: model=%s, tokens=%d/%d, latency=%.0fms",
        settings.LLM_MODEL,
        input_tokens,
        output_tokens,
        latency_ms,
    )

    return CoachingFeedback(
        feedback=output_text,
        model=settings.LLM_MODEL,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
