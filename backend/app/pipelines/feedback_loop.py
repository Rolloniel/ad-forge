"""Performance Feedback Loop pipeline.

Steps:
  1. simulate_performance  — generate realistic ad metrics with statistical distributions
  2. analyze_results       — identify winning hooks, losing angles, significant patterns
  3. generate_insights     — OpenAI: produce optimization recommendations
  4. update_context        — store insights so future pipeline runs bias toward winners

Outputs: simulated metrics, analysis report, and stored insights.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
from sqlalchemy import select

from app.db import async_session
from app.integrations.openai_client import OpenAIClient
from app.models import Insight, Output, PerformanceMetric

# ---------------------------------------------------------------------------
# JSON Schema for OpenAI structured output
# ---------------------------------------------------------------------------

INSIGHTS_SCHEMA: dict[str, Any] = {
    "name": "performance_insights",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Executive summary of performance analysis",
            },
            "recommendations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "One of: creative, targeting, budget, messaging",
                        },
                        "action": {
                            "type": "string",
                            "description": "Specific recommendation",
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Why this is recommended based on data",
                        },
                        "priority": {
                            "type": "string",
                            "description": "One of: high, medium, low",
                        },
                    },
                    "required": ["category", "action", "rationale", "priority"],
                    "additionalProperties": False,
                },
            },
            "winning_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns observed in top-performing creatives",
            },
            "losing_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns observed in under-performing creatives",
            },
        },
        "required": [
            "summary",
            "recommendations",
            "winning_patterns",
            "losing_patterns",
        ],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Step 1: simulate_performance
# ---------------------------------------------------------------------------


def _generate_metrics(
    output_count: int, rng: np.random.Generator
) -> list[dict[str, Any]]:
    """Generate realistic ad performance metrics with statistical distributions.

    Higher-performing outputs get realistic patterns (2-5% CTR), while
    lower performers cluster around 0.5-1.5% CTR. Uses log-normal
    distributions for impressions and conversions to model real ad data.
    """
    metrics: list[dict[str, Any]] = []

    # Impressions: log-normal, median ~5000, range ~1000-50000
    impressions_arr = rng.lognormal(mean=8.5, sigma=0.7, size=output_count).astype(int)
    impressions_arr = np.clip(impressions_arr, 500, 100_000)

    # CTR: mixture — ~30% are "winners" (2-5%), rest are average (0.5-1.5%)
    is_winner = rng.random(output_count) < 0.3
    ctr_arr = np.where(
        is_winner,
        rng.uniform(0.02, 0.05, output_count),
        rng.uniform(0.005, 0.015, output_count),
    )

    for i in range(output_count):
        impressions = int(impressions_arr[i])
        ctr = float(round(ctr_arr[i], 5))
        clicks = max(1, int(impressions * ctr))
        actual_ctr = round(clicks / impressions, 5)

        # Conversion rate: 1-8% of clicks
        conv_rate = float(rng.uniform(0.01, 0.08))
        conversions = max(0, int(clicks * conv_rate))

        # CPA: $5-$80, inversely correlated with CTR
        base_cpa = float(rng.lognormal(mean=3.0, sigma=0.5))
        cpa = round(base_cpa / (actual_ctr * 100 + 0.1), 2)
        cpa = max(2.0, min(cpa, 150.0))

        # ROAS: higher CTR → better ROAS (1.0-8.0x)
        roas = round(float(rng.uniform(0.5, 3.0)) + actual_ctr * 100, 2)
        roas = max(0.5, min(roas, 12.0))

        metrics.append({
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(actual_ctr, 5),
            "conversions": conversions,
            "cpa": cpa,
            "roas": roas,
        })

    return metrics


async def simulate_performance(prev_output: dict, config: dict) -> dict[str, Any]:
    """Generate realistic ad metrics for a batch of outputs.

    Expects config to contain:
      - brand_id: UUID of the brand
      - source_job_id (optional): UUID of a previous pipeline job whose outputs
        to simulate against. If omitted, generates metrics for a default count.
      - output_count (optional): number of outputs to simulate (default 10)
      - seed (optional): random seed for reproducibility
    """
    brand_id = config.get("brand_id")
    if not brand_id:
        raise ValueError("brand_id is required in config")

    source_job_id = config.get("source_job_id")
    output_count = config.get("output_count", 10)
    seed = config.get("seed")

    rng = np.random.default_rng(seed)
    now = datetime.now(timezone.utc)

    output_refs: list[dict[str, Any]] = []

    async with async_session() as session:
        # If source_job_id provided, load those outputs
        if source_job_id:
            result = await session.execute(
                select(Output).where(Output.job_id == UUID(str(source_job_id)))
            )
            outputs = result.scalars().all()
            output_count = max(len(outputs), 1)
            output_refs = [
                {
                    "output_id": str(o.id),
                    "output_type": o.output_type,
                    "metadata": o.metadata_ or {},
                }
                for o in outputs
            ]

    # Generate simulated metrics
    metrics_data = _generate_metrics(output_count, rng)

    # Persist to database
    persisted: list[dict[str, Any]] = []

    async with async_session() as session:
        for i, m in enumerate(metrics_data):
            output_ref = output_refs[i] if i < len(output_refs) else None

            if output_ref and output_ref.get("output_id"):
                output_id = UUID(output_ref["output_id"])
            else:
                # Create a synthetic output record for standalone simulation
                # Use source_job_id if available, otherwise the current pipeline job_id
                parent_job_id = source_job_id or config.get("job_id")
                if not parent_job_id:
                    raise ValueError(
                        "Either source_job_id or job_id must be present in config"
                    )
                output = Output(
                    job_id=UUID(str(parent_job_id)),
                    pipeline_name="feedback_loop",
                    output_type="simulated_creative",
                    metadata_={"simulation_index": i, "brand_id": str(brand_id)},
                )
                session.add(output)
                await session.flush()
                output_id = output.id

            pm = PerformanceMetric(
                output_id=output_id,
                impressions=m["impressions"],
                clicks=m["clicks"],
                ctr=m["ctr"],
                conversions=m["conversions"],
                cpa=m["cpa"],
                roas=m["roas"],
                simulated_at=now,
            )
            session.add(pm)
            persisted.append({
                "metric_id": str(pm.id),
                "output_id": str(output_id),
                **m,
            })

        await session.commit()

    return {
        "brand_id": str(brand_id),
        "output_count": output_count,
        "metrics": persisted,
        "simulated_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Step 2: analyze_results
# ---------------------------------------------------------------------------


def _compute_significance(group_a: list[float], group_b: list[float]) -> float:
    """Compute a simple z-test p-value between two groups of CTR values."""
    if len(group_a) < 2 or len(group_b) < 2:
        return 1.0

    mean_a = sum(group_a) / len(group_a)
    mean_b = sum(group_b) / len(group_b)

    var_a = sum((x - mean_a) ** 2 for x in group_a) / len(group_a)
    var_b = sum((x - mean_b) ** 2 for x in group_b) / len(group_b)

    se = math.sqrt(var_a / len(group_a) + var_b / len(group_b))
    if se == 0:
        return 1.0

    z = abs(mean_a - mean_b) / se
    # Approximate two-tailed p-value using the complementary error function
    p_value = math.erfc(z / math.sqrt(2))
    return round(p_value, 6)


async def analyze_results(prev_output: dict, config: dict) -> dict[str, Any]:
    """Identify winning hooks, losing angles, and statistically significant patterns."""
    metrics = prev_output.get("metrics", [])
    if not metrics:
        return {
            "winners": [],
            "losers": [],
            "rankings": [],
            "significance": {},
            "summary_stats": {},
        }

    # Compute summary statistics
    ctrs = [m["ctr"] for m in metrics]
    cpas = [m["cpa"] for m in metrics]
    roas_vals = [m["roas"] for m in metrics]

    mean_ctr = sum(ctrs) / len(ctrs)
    mean_cpa = sum(cpas) / len(cpas)
    mean_roas = sum(roas_vals) / len(roas_vals)

    # Rank by composite score: normalize CTR, ROAS (higher=better), CPA (lower=better)
    max_ctr = max(ctrs) or 1
    max_roas = max(roas_vals) or 1
    max_cpa = max(cpas) or 1

    scored = []
    for i, m in enumerate(metrics):
        score = (
            (m["ctr"] / max_ctr) * 0.4
            + (m["roas"] / max_roas) * 0.35
            + (1 - m["cpa"] / max_cpa) * 0.25
        )
        scored.append({
            "index": i,
            "output_id": m.get("output_id", ""),
            "ctr": m["ctr"],
            "cpa": m["cpa"],
            "roas": m["roas"],
            "impressions": m["impressions"],
            "conversions": m["conversions"],
            "score": round(score, 4),
        })

    ranked = sorted(scored, key=lambda x: x["score"], reverse=True)

    # Top 30% are winners, bottom 30% are losers
    n = len(ranked)
    top_n = max(1, int(n * 0.3))
    bottom_n = max(1, int(n * 0.3))

    winners = ranked[:top_n]
    losers = ranked[-bottom_n:]

    # Statistical significance: winners vs losers CTR
    winner_ctrs = [w["ctr"] for w in winners]
    loser_ctrs = [l["ctr"] for l in losers]
    p_value = _compute_significance(winner_ctrs, loser_ctrs)

    return {
        "winners": winners,
        "losers": losers,
        "rankings": ranked,
        "significance": {
            "winners_vs_losers_ctr_p_value": p_value,
            "is_significant": p_value < 0.05,
            "winner_count": len(winners),
            "loser_count": len(losers),
        },
        "summary_stats": {
            "total_outputs": n,
            "mean_ctr": round(mean_ctr, 5),
            "mean_cpa": round(mean_cpa, 2),
            "mean_roas": round(mean_roas, 2),
            "best_ctr": round(max(ctrs), 5),
            "worst_ctr": round(min(ctrs), 5),
            "best_roas": round(max(roas_vals), 2),
        },
    }


# ---------------------------------------------------------------------------
# Step 3: generate_insights
# ---------------------------------------------------------------------------


def _build_insights_prompt(analysis: dict[str, Any], config: dict[str, Any]) -> str:
    """Build user prompt from analysis results."""
    parts: list[str] = []
    parts.append("## Performance Analysis Results\n")

    stats = analysis.get("summary_stats", {})
    parts.append(f"**Total Outputs Analyzed:** {stats.get('total_outputs', 0)}")
    parts.append(f"**Mean CTR:** {stats.get('mean_ctr', 0):.3%}")
    parts.append(f"**Mean CPA:** ${stats.get('mean_cpa', 0):.2f}")
    parts.append(f"**Mean ROAS:** {stats.get('mean_roas', 0):.2f}x")
    parts.append(f"**Best CTR:** {stats.get('best_ctr', 0):.3%}")
    parts.append(f"**Best ROAS:** {stats.get('best_roas', 0):.2f}x")

    sig = analysis.get("significance", {})
    parts.append(f"\n**Statistical Significance:** p={sig.get('winners_vs_losers_ctr_p_value', 'N/A')}")
    parts.append(f"**Significant:** {sig.get('is_significant', False)}")

    winners = analysis.get("winners", [])
    if winners:
        parts.append("\n### Top Performers")
        for w in winners[:5]:
            parts.append(
                f"- Output {w.get('output_id', w.get('index', '?'))}: "
                f"CTR={w['ctr']:.3%}, CPA=${w['cpa']:.2f}, ROAS={w['roas']:.2f}x, "
                f"Score={w['score']:.4f}"
            )

    losers = analysis.get("losers", [])
    if losers:
        parts.append("\n### Under-Performers")
        for l in losers[:5]:
            parts.append(
                f"- Output {l.get('output_id', l.get('index', '?'))}: "
                f"CTR={l['ctr']:.3%}, CPA=${l['cpa']:.2f}, ROAS={l['roas']:.2f}x, "
                f"Score={l['score']:.4f}"
            )

    parts.append(
        "\nBased on this data, provide actionable optimization recommendations "
        "for improving ad creative performance."
    )
    return "\n".join(parts)


async def generate_insights(prev_output: dict, config: dict) -> dict[str, Any]:
    """Call OpenAI to produce optimization recommendations from analysis data."""
    brand_id = config.get("brand_id")

    client = OpenAIClient()
    insights_data = await client.structured_output(
        system=(
            "You are an expert performance marketing analyst. "
            "Analyze the ad performance data and provide specific, "
            "actionable optimization recommendations. Focus on patterns "
            "that distinguish top performers from under-performers."
        ),
        user=_build_insights_prompt(prev_output, config),
        json_schema=INSIGHTS_SCHEMA,
        temperature=0.3,
        max_tokens=4096,
    )

    # Persist insights to database
    stored_insights: list[dict[str, Any]] = []

    async with async_session() as session:
        bid = UUID(str(brand_id))

        # Store each recommendation as an insight
        for rec in insights_data.get("recommendations", []):
            insight = Insight(
                brand_id=bid,
                insight_type=f"recommendation_{rec['category']}",
                content=f"{rec['action']} — {rec['rationale']}",
                confidence={"high": 0.9, "medium": 0.7, "low": 0.4}.get(
                    rec.get("priority", "medium"), 0.5
                ),
                source_metrics=prev_output.get("summary_stats"),
            )
            session.add(insight)
            stored_insights.append({
                "type": insight.insight_type,
                "content": insight.content,
                "confidence": insight.confidence,
            })

        # Store winning and losing patterns as insights
        for pattern in insights_data.get("winning_patterns", []):
            insight = Insight(
                brand_id=bid,
                insight_type="winning_pattern",
                content=pattern,
                confidence=0.8,
                source_metrics=prev_output.get("summary_stats"),
            )
            session.add(insight)
            stored_insights.append({
                "type": "winning_pattern",
                "content": pattern,
                "confidence": 0.8,
            })

        for pattern in insights_data.get("losing_patterns", []):
            insight = Insight(
                brand_id=bid,
                insight_type="losing_pattern",
                content=pattern,
                confidence=0.8,
                source_metrics=prev_output.get("summary_stats"),
            )
            session.add(insight)
            stored_insights.append({
                "type": "losing_pattern",
                "content": pattern,
                "confidence": 0.8,
            })

        await session.commit()

    return {
        "insights": insights_data,
        "stored_count": len(stored_insights),
        "stored_insights": stored_insights,
    }


# ---------------------------------------------------------------------------
# Step 4: update_context
# ---------------------------------------------------------------------------


async def update_context(prev_output: dict, config: dict) -> dict[str, Any]:
    """Update brand's generation context so future runs bias toward winners.

    Stores a consolidated 'generation_context' insight that summarizes
    winning patterns and recommendations for the brand. Future pipeline
    runs (briefs, ad_copy) query recent insights and will pick this up.
    """
    brand_id = config.get("brand_id")
    if not brand_id:
        raise ValueError("brand_id is required in config")

    bid = UUID(str(brand_id))
    insights_data = prev_output.get("insights", {})

    winning = insights_data.get("winning_patterns", [])
    recommendations = insights_data.get("recommendations", [])
    high_priority = [r for r in recommendations if r.get("priority") == "high"]

    context_parts: list[str] = []

    if winning:
        context_parts.append("WINNING PATTERNS: " + "; ".join(winning))

    if high_priority:
        actions = [r["action"] for r in high_priority]
        context_parts.append("HIGH-PRIORITY ACTIONS: " + "; ".join(actions))

    if insights_data.get("summary"):
        context_parts.append("ANALYSIS: " + insights_data["summary"])

    context_content = " | ".join(context_parts) if context_parts else "No significant patterns detected."

    async with async_session() as session:
        # Store as a generation_context insight — future pipelines will query this
        insight = Insight(
            brand_id=bid,
            insight_type="generation_context",
            content=context_content,
            confidence=0.85,
            source_metrics={
                "winning_pattern_count": len(winning),
                "recommendation_count": len(recommendations),
                "high_priority_count": len(high_priority),
            },
        )
        session.add(insight)
        await session.commit()

    return {
        "brand_id": str(brand_id),
        "context_updated": True,
        "context_content": context_content,
        "winning_pattern_count": len(winning),
        "recommendation_count": len(recommendations),
    }


# ---------------------------------------------------------------------------
# Pipeline registration
# ---------------------------------------------------------------------------

from app.engine.pipeline_engine import register_pipeline  # noqa: E402

register_pipeline(
    "feedback_loop",
    [
        ("simulate_performance", simulate_performance),
        ("analyze_results", analyze_results),
        ("generate_insights", generate_insights),
        ("update_context", update_context),
    ],
)
