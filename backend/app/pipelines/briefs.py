"""Creative Brief Generator pipeline.

Steps:
  1. analyze_product  — load brand, product, audience data; query recent insights
  2. generate_brief   — OpenAI structured output for the creative brief
  3. render_brief     — convert JSON brief to formatted markdown

Outputs: JSON brief file + rendered markdown file.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.openai_client import OpenAIClient
from app.models import Brand, Insight

# ---------------------------------------------------------------------------
# JSON Schema for OpenAI structured output
# ---------------------------------------------------------------------------

BRIEF_SCHEMA: dict[str, Any] = {
    "name": "creative_brief",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "campaign_name": {
                "type": "string",
                "description": "Short memorable campaign name",
            },
            "objective": {
                "type": "string",
                "description": "Primary campaign objective",
            },
            "target_audience": {
                "type": "object",
                "properties": {
                    "primary_segment": {"type": "string"},
                    "demographics": {"type": "string"},
                    "psychographics": {"type": "string"},
                    "pain_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "motivations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "primary_segment",
                    "demographics",
                    "psychographics",
                    "pain_points",
                    "motivations",
                ],
                "additionalProperties": False,
            },
            "key_messages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "supporting_copy": {"type": "string"},
                    },
                    "required": ["headline", "supporting_copy"],
                    "additionalProperties": False,
                },
                "description": "3-5 key messages with headlines and copy",
            },
            "creative_direction": {
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Overarching creative concept",
                    },
                    "visual_style": {
                        "type": "string",
                        "description": "Visual direction aligned with brand guidelines",
                    },
                    "color_palette": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hex colors for the campaign",
                    },
                    "imagery_notes": {
                        "type": "string",
                        "description": "Photography/illustration direction",
                    },
                },
                "required": [
                    "concept",
                    "visual_style",
                    "color_palette",
                    "imagery_notes",
                ],
                "additionalProperties": False,
            },
            "tone_guidelines": {
                "type": "object",
                "properties": {
                    "voice": {"type": "string"},
                    "do": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "dont": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["voice", "do", "dont"],
                "additionalProperties": False,
            },
            "offer_structure": {
                "type": "object",
                "properties": {
                    "primary_offer": {"type": "string"},
                    "urgency_hook": {"type": "string"},
                    "cta": {"type": "string"},
                },
                "required": ["primary_offer", "urgency_hook", "cta"],
                "additionalProperties": False,
            },
            "deliverables": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of creative assets to produce",
            },
        },
        "required": [
            "campaign_name",
            "objective",
            "target_audience",
            "key_messages",
            "creative_direction",
            "tone_guidelines",
            "offer_structure",
            "deliverables",
        ],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Step 1: analyze_product
# ---------------------------------------------------------------------------

async def analyze_product(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Load brand, product, audience data and query recent insights."""
    brand_id = UUID(config["brand_id"]) if isinstance(config.get("brand_id"), str) else config["brand_id"]
    product_id = config.get("product_id")
    audience_id = config.get("audience_id")

    # Load brand with products and audiences eagerly
    stmt = (
        select(Brand)
        .where(Brand.id == brand_id)
        .options(selectinload(Brand.products), selectinload(Brand.audiences))
    )
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")

    # Select specific product or first available
    product = None
    if product_id:
        pid = UUID(product_id) if isinstance(product_id, str) else product_id
        product = next((p for p in brand.products if p.id == pid), None)
    if product is None and brand.products:
        product = brand.products[0]

    # Select specific audience or first available
    audience = None
    if audience_id:
        aid = UUID(audience_id) if isinstance(audience_id, str) else audience_id
        audience = next((a for a in brand.audiences if a.id == aid), None)
    if audience is None and brand.audiences:
        audience = brand.audiences[0]

    # Query recent insights for this brand (up to 5)
    insights_stmt = (
        select(Insight)
        .where(Insight.brand_id == brand_id)
        .order_by(Insight.created_at.desc())
        .limit(5)
    )
    insights_result = await session.execute(insights_stmt)
    insights = insights_result.scalars().all()

    return {
        "brand": {
            "name": brand.name,
            "voice": brand.voice,
            "visual_guidelines": brand.visual_guidelines,
            "offers": brand.offers or [],
        },
        "product": {
            "name": product.name,
            "description": product.description,
            "price": str(product.price) if product.price else None,
        } if product else None,
        "audience": {
            "name": audience.name,
            "demographics": audience.demographics,
            "interests": audience.interests,
        } if audience else None,
        "insights": [
            {
                "type": i.insight_type,
                "content": i.content,
                "confidence": i.confidence,
            }
            for i in insights
        ],
    }


# ---------------------------------------------------------------------------
# Step 2: generate_brief
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    return (
        "You are an expert advertising creative director. "
        "Generate a detailed creative brief for a digital advertising campaign. "
        "The brief should be actionable, specific to the brand and product, "
        "and ready to hand off to designers and copywriters. "
        "Base your recommendations on the brand data, product details, "
        "target audience, and any performance insights provided."
    )


def _build_user_prompt(analysis: dict[str, Any], config: dict[str, Any]) -> str:
    parts: list[str] = []

    brand = analysis["brand"]
    parts.append(f"## Brand: {brand['name']}")
    if brand.get("voice"):
        parts.append(f"**Brand Voice:** {brand['voice']}")
    if brand.get("visual_guidelines"):
        parts.append(f"**Visual Guidelines:** {brand['visual_guidelines']}")
    if brand.get("offers"):
        offers_text = ", ".join(o["name"] for o in brand["offers"])
        parts.append(f"**Available Offers:** {offers_text}")

    product = analysis.get("product")
    if product:
        parts.append(f"\n## Product: {product['name']}")
        if product.get("description"):
            parts.append(f"**Description:** {product['description']}")
        if product.get("price"):
            parts.append(f"**Price:** ${product['price']}")

    audience = analysis.get("audience")
    if audience:
        parts.append(f"\n## Target Audience: {audience['name']}")
        if audience.get("demographics"):
            parts.append(f"**Demographics:** {audience['demographics']}")
        if audience.get("interests"):
            parts.append(f"**Interests:** {audience['interests']}")

    insights = analysis.get("insights", [])
    if insights:
        parts.append("\n## Recent Performance Insights")
        for ins in insights:
            parts.append(f"- [{ins['type']}] {ins['content']} (confidence: {ins.get('confidence', 'N/A')})")

    # Include any campaign-specific guidance from config
    campaign_goal = config.get("campaign_goal")
    if campaign_goal:
        parts.append(f"\n## Campaign Goal\n{campaign_goal}")

    platform = config.get("platform")
    if platform:
        parts.append(f"\n## Target Platform: {platform}")

    parts.append(
        "\nGenerate a comprehensive creative brief for this brand and product."
    )
    return "\n".join(parts)


async def generate_brief(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Call OpenAI structured output to generate the creative brief."""
    analysis = prev_outputs["analyze_product"]
    client = OpenAIClient()

    brief = await client.structured_output(
        system=_build_system_prompt(),
        user=_build_user_prompt(analysis, config),
        json_schema=BRIEF_SCHEMA,
        temperature=0.4,
        max_tokens=4096,
    )

    return {"brief": brief}


# ---------------------------------------------------------------------------
# Step 3: render_brief
# ---------------------------------------------------------------------------

def _render_markdown(brief: dict[str, Any], brand_name: str) -> str:
    """Convert a structured brief dict to formatted markdown."""
    lines: list[str] = []
    lines.append(f"# Creative Brief: {brief['campaign_name']}")
    lines.append(f"**Brand:** {brand_name}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    lines.append("## Objective")
    lines.append(brief["objective"])
    lines.append("")

    # Target Audience
    ta = brief["target_audience"]
    lines.append("## Target Audience")
    lines.append(f"**Primary Segment:** {ta['primary_segment']}")
    lines.append(f"**Demographics:** {ta['demographics']}")
    lines.append(f"**Psychographics:** {ta['psychographics']}")
    lines.append("")
    lines.append("### Pain Points")
    for pp in ta["pain_points"]:
        lines.append(f"- {pp}")
    lines.append("")
    lines.append("### Motivations")
    for m in ta["motivations"]:
        lines.append(f"- {m}")
    lines.append("")

    # Key Messages
    lines.append("## Key Messages")
    for i, msg in enumerate(brief["key_messages"], 1):
        lines.append(f"### Message {i}: {msg['headline']}")
        lines.append(msg["supporting_copy"])
        lines.append("")

    # Creative Direction
    cd = brief["creative_direction"]
    lines.append("## Creative Direction")
    lines.append(f"**Concept:** {cd['concept']}")
    lines.append(f"**Visual Style:** {cd['visual_style']}")
    lines.append(f"**Color Palette:** {', '.join(cd['color_palette'])}")
    lines.append(f"**Imagery Notes:** {cd['imagery_notes']}")
    lines.append("")

    # Tone Guidelines
    tg = brief["tone_guidelines"]
    lines.append("## Tone Guidelines")
    lines.append(f"**Voice:** {tg['voice']}")
    lines.append("")
    lines.append("**Do:**")
    for d in tg["do"]:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("**Don't:**")
    for d in tg["dont"]:
        lines.append(f"- {d}")
    lines.append("")

    # Offer Structure
    offer = brief["offer_structure"]
    lines.append("## Offer Structure")
    lines.append(f"**Primary Offer:** {offer['primary_offer']}")
    lines.append(f"**Urgency Hook:** {offer['urgency_hook']}")
    lines.append(f"**CTA:** {offer['cta']}")
    lines.append("")

    # Deliverables
    lines.append("## Deliverables")
    for d in brief["deliverables"]:
        lines.append(f"- {d}")
    lines.append("")

    return "\n".join(lines)


async def render_brief(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Convert JSON brief to markdown and write output files."""
    brief = prev_outputs["generate_brief"]["brief"]
    brand_name = prev_outputs["analyze_product"]["brand"]["name"]

    markdown = _render_markdown(brief, brand_name)

    # Write output files
    output_dir = os.path.join("outputs", str(job_id), "briefs")
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "brief.json")
    md_path = os.path.join(output_dir, "brief.md")

    with open(json_path, "w") as f:
        json.dump(brief, f, indent=2)

    with open(md_path, "w") as f:
        f.write(markdown)

    # Create Output records for gallery and file serving
    from app.models.output import Output

    md_output = Output(
        job_id=job_id,
        pipeline_name="briefs",
        output_type="text",
        file_path=md_path,
        metadata_={
            "campaign_name": brief.get("campaign_name", ""),
            "objective": brief.get("objective", ""),
            "format": "markdown",
        },
    )
    session.add(md_output)

    json_output = Output(
        job_id=job_id,
        pipeline_name="briefs",
        output_type="json",
        file_path=json_path,
        metadata_={
            "campaign_name": brief.get("campaign_name", ""),
            "format": "json",
        },
    )
    session.add(json_output)
    await session.flush()

    return {
        "json_path": json_path,
        "md_path": md_path,
        "brief": brief,
        "markdown_preview": markdown[:500],
    }


# ---------------------------------------------------------------------------
# Pipeline registration
# ---------------------------------------------------------------------------

from app.pipelines import PipelineDefinition, register  # noqa: E402

register(
    PipelineDefinition(
        name="briefs",
        steps=[
            ("analyze_product", analyze_product),
            ("generate_brief", generate_brief),
            ("render_brief", render_brief),
        ],
    )
)
