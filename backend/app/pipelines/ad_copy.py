"""Ad Copy & Deployment Engine pipeline.

Generates structured ad copy variations per creative angle, builds a testing
matrix (angles x copy variants x audiences), and creates mock Meta/TikTok
Ads API deployment payloads.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.integrations.openai_client import OpenAIClient

DEFAULT_ANGLES = [
    "before_after_transformation",
    "ingredient_science",
    "social_proof_testimonials",
    "urgency_scarcity",
    "routine_integration",
]

COPY_VARIATION_SCHEMA = {
    "type": "object",
    "properties": {
        "variations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "primary_text": {"type": "string"},
                    "headline": {"type": "string"},
                    "description": {"type": "string"},
                    "cta": {"type": "string"},
                },
                "required": ["primary_text", "headline", "description", "cta"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["variations"],
    "additionalProperties": False,
}


async def generate_copy_matrix(ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate ad copy variations per creative angle using OpenAI.

    Fan-out: produces one copy variant set per angle, each containing
    N variations with primary_text, headline, description, and CTA.
    """
    config = ctx["config"]
    brand = ctx["brand"]
    product = config.get("product", {})
    angles = config.get("angles", DEFAULT_ANGLES)
    variations_per_angle = config.get("variations_per_angle", 3)

    system_prompt = (
        f"You are an expert direct-response ad copywriter for {brand['name']}. "
        f"Brand voice: {brand.get('voice', 'Professional and engaging')}. "
        f"Write compelling ad copy that drives conversions for eCommerce."
    )

    copy_variations: list[dict[str, Any]] = []

    for angle in angles:
        user_prompt = (
            f"Generate {variations_per_angle} ad copy variations for the "
            f"creative angle: '{angle}'.\n\n"
            f"Product: {product.get('name', 'Unknown Product')}\n"
            f"Description: {product.get('description', '')}\n"
            f"Price: ${product.get('price', 'N/A')}\n\n"
            f"For each variation provide:\n"
            f"- primary_text: Main ad body (2-3 sentences, conversational)\n"
            f"- headline: Punchy headline (under 40 characters)\n"
            f"- description: Supporting line (1 sentence)\n"
            f"- cta: Call-to-action button text (e.g. Shop Now, Get Yours)\n\n"
            f"Return JSON with key 'variations' containing an array of objects."
        )

        client = OpenAIClient()
        result = await client.structured_output(
            system=system_prompt,
            user=user_prompt,
            json_schema={
                "name": "copy_variations",
                "strict": True,
                "schema": COPY_VARIATION_SCHEMA,
            },
        )

        copy_variations.append({
            "angle": angle,
            "variations": result["variations"],
        })

    # Persist output file
    output_dir = Path(ctx["output_dir"]) / str(ctx["job_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "copy_variations.json"
    output_path.write_text(json.dumps(copy_variations, indent=2))

    return {
        "copy_variations": copy_variations,
        "file_path": str(output_path),
        "angle_count": len(angles),
        "total_variations": sum(len(cv["variations"]) for cv in copy_variations),
    }


async def build_testing_matrix(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build testing matrix: angles x copy variants x audiences.

    Produces a flat list of test entries, each uniquely keyed for
    downstream A/B test tracking and deployment mapping.
    """
    config = ctx["config"]
    previous = ctx["previous_outputs"]

    copy_data = previous["generate_copy_matrix"]
    copy_variations = copy_data["copy_variations"]
    audiences = config.get("audiences", [])

    matrix_entries: list[dict[str, Any]] = []
    entry_id = 0

    for cv in copy_variations:
        angle = cv["angle"]
        for var_idx, variation in enumerate(cv["variations"]):
            for audience in audiences:
                entry_id += 1
                aud_slug = (
                    audience.get("name", "unknown")
                    .replace(" ", "_")
                    .lower()
                )
                matrix_entries.append({
                    "entry_id": entry_id,
                    "angle": angle,
                    "variation_index": var_idx,
                    "copy": variation,
                    "audience": {
                        "id": audience.get("id", ""),
                        "name": audience.get("name", "Unknown"),
                        "demographics": audience.get("demographics", ""),
                    },
                    "test_key": f"{angle}__v{var_idx}__{aud_slug}",
                })

    variations_per_angle = (
        len(copy_variations[0]["variations"]) if copy_variations else 0
    )

    testing_matrix = {
        "total_combinations": len(matrix_entries),
        "dimensions": {
            "angles": len(copy_variations),
            "variations_per_angle": variations_per_angle,
            "audiences": len(audiences),
        },
        "entries": matrix_entries,
    }

    output_dir = Path(ctx["output_dir"]) / str(ctx["job_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "testing_matrix.json"
    output_path.write_text(json.dumps(testing_matrix, indent=2))

    return {
        "testing_matrix": testing_matrix,
        "file_path": str(output_path),
        "total_combinations": len(matrix_entries),
    }


def _build_meta_payload(
    brand: dict[str, Any],
    product: dict[str, Any],
    config: dict[str, Any],
    entries_by_audience: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Construct a mock Meta Ads API campaign payload."""
    campaign_objective = config.get("campaign_objective", "CONVERSIONS")
    daily_budget = config.get("daily_budget", 50.0)
    currency = config.get("currency", "USD")
    landing_url = config.get("landing_url", "https://example.com")
    product_name = product.get("name", "Product")

    campaign_id = str(uuid.uuid4())
    ad_sets: list[dict[str, Any]] = []

    for aud_name, entries in entries_by_audience.items():
        ad_set_id = str(uuid.uuid4())
        ads = [
            {
                "ad_id": str(uuid.uuid4()),
                "name": (
                    f"{product_name} - {e['angle']} - v{e['variation_index']}"
                ),
                "status": "PAUSED",
                "creative": {
                    "primary_text": e["copy"]["primary_text"],
                    "headline": e["copy"]["headline"],
                    "description": e["copy"]["description"],
                    "call_to_action": e["copy"]["cta"],
                    "link_url": landing_url,
                },
                "test_key": e["test_key"],
            }
            for e in entries
        ]

        ad_sets.append({
            "ad_set_id": ad_set_id,
            "name": f"{brand['name']} - {aud_name}",
            "status": "PAUSED",
            "daily_budget": daily_budget,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": campaign_objective,
            "targeting": {
                "audience_name": aud_name,
                "demographics": entries[0]["audience"].get("demographics", ""),
            },
            "ads": ads,
        })

    return {
        "platform": "meta",
        "campaign": {
            "campaign_id": campaign_id,
            "name": f"{brand['name']} - {product_name} - Ad Copy Test",
            "objective": campaign_objective,
            "status": "PAUSED",
            "special_ad_categories": [],
            "budget": {
                "daily_budget": daily_budget,
                "currency": currency,
            },
        },
        "ad_sets": ad_sets,
        "total_ads": sum(len(s["ads"]) for s in ad_sets),
    }


def _build_tiktok_payload(
    brand: dict[str, Any],
    product: dict[str, Any],
    config: dict[str, Any],
    entries_by_audience: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Construct a mock TikTok Ads API campaign payload."""
    campaign_objective = config.get("campaign_objective", "CONVERSIONS")
    daily_budget = config.get("daily_budget", 50.0)
    landing_url = config.get("landing_url", "https://example.com")
    product_name = product.get("name", "Product")

    campaign_id = str(uuid.uuid4())
    objective_type = (
        "CONVERSIONS" if campaign_objective == "CONVERSIONS" else "TRAFFIC"
    )
    optimization_goal = (
        "CONVERT" if campaign_objective == "CONVERSIONS" else "CLICK"
    )

    ad_groups: list[dict[str, Any]] = []

    for aud_name, entries in entries_by_audience.items():
        ad_group_id = str(uuid.uuid4())
        ads = [
            {
                "ad_id": str(uuid.uuid4()),
                "ad_name": (
                    f"{product_name} - {e['angle']} - v{e['variation_index']}"
                ),
                "status": "DISABLE",
                "ad_text": e["copy"]["primary_text"],
                "call_to_action": e["copy"]["cta"],
                "landing_page_url": landing_url,
                "display_name": brand["name"],
                "test_key": e["test_key"],
            }
            for e in entries
        ]

        ad_groups.append({
            "adgroup_id": ad_group_id,
            "adgroup_name": f"{brand['name']} - {aud_name}",
            "status": "DISABLE",
            "budget": daily_budget,
            "budget_mode": "BUDGET_MODE_DAY",
            "optimization_goal": optimization_goal,
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "audience": {
                "audience_name": aud_name,
                "demographics": entries[0]["audience"].get("demographics", ""),
            },
            "ads": ads,
        })

    return {
        "platform": "tiktok",
        "campaign": {
            "campaign_id": campaign_id,
            "campaign_name": (
                f"{brand['name']} - {product_name} - Ad Copy Test"
            ),
            "objective_type": objective_type,
            "status": "DISABLE",
            "budget": daily_budget,
            "budget_mode": "BUDGET_MODE_DAY",
        },
        "ad_groups": ad_groups,
        "total_ads": sum(len(ag["ads"]) for ag in ad_groups),
    }


async def generate_deployment_payloads(ctx: dict[str, Any]) -> dict[str, Any]:
    """Generate mock Meta and TikTok Ads API deployment payloads.

    Structures the testing matrix entries into platform-specific campaign
    hierarchies: Meta (campaign > ad_set > ad) and TikTok (campaign >
    ad_group > ad).
    """
    config = ctx["config"]
    previous = ctx["previous_outputs"]
    brand = ctx["brand"]
    product = config.get("product", {})

    matrix_data = previous["build_testing_matrix"]
    testing_matrix = matrix_data["testing_matrix"]

    # Group entries by audience for ad set / ad group creation
    entries_by_audience: dict[str, list[dict[str, Any]]] = {}
    for entry in testing_matrix["entries"]:
        aud_name = entry["audience"]["name"]
        entries_by_audience.setdefault(aud_name, []).append(entry)

    meta_payload = _build_meta_payload(
        brand, product, config, entries_by_audience
    )
    tiktok_payload = _build_tiktok_payload(
        brand, product, config, entries_by_audience
    )

    # Persist output files
    output_dir = Path(ctx["output_dir"]) / str(ctx["job_id"])
    output_dir.mkdir(parents=True, exist_ok=True)

    meta_path = output_dir / "meta_payload.json"
    meta_path.write_text(json.dumps(meta_payload, indent=2))

    tiktok_path = output_dir / "tiktok_payload.json"
    tiktok_path.write_text(json.dumps(tiktok_payload, indent=2))

    return {
        "meta_payload": meta_payload,
        "tiktok_payload": tiktok_payload,
        "meta_file_path": str(meta_path),
        "tiktok_file_path": str(tiktok_path),
        "total_meta_ads": meta_payload["total_ads"],
        "total_tiktok_ads": tiktok_payload["total_ads"],
    }


# ---------------------------------------------------------------------------
# Pipeline registration — wrap ctx-style functions to standard signature
# ---------------------------------------------------------------------------

from uuid import UUID  # noqa: E402

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.pipelines import PipelineDefinition, register  # noqa: E402


def _adapt_ctx(fn, prev_step_name: str | None = None):
    """Wrap a ``ctx``-dict step into the standard keyword-args signature."""

    async def wrapper(
        *,
        job_id: UUID,
        config: dict[str, Any],
        prev_outputs: dict[str, dict[str, Any]],
        session: AsyncSession,
    ) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "job_id": str(job_id),
            "config": config,
            "brand": config.get("brand", {}),
            "previous_outputs": prev_outputs,
            "output_dir": "outputs",
        }
        return await fn(ctx)

    return wrapper


register(
    PipelineDefinition(
        name="ad_copy",
        steps=[
            ("generate_copy_matrix", _adapt_ctx(generate_copy_matrix)),
            ("build_testing_matrix", _adapt_ctx(build_testing_matrix, "generate_copy_matrix")),
            ("generate_deployment_payloads", _adapt_ctx(generate_deployment_payloads, "build_testing_matrix")),
        ],
    )
)
