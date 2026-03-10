"""Landing Page Generator pipeline.

Steps:
  1. generate_page_strategy — OpenAI: page type, section order, offer positioning
  2. generate_sections      — fan-out: generate content for each planned section
  3. generate_variations    — A/B test variants for hero and CTA sections
  4. render_page            — structured JSON page definition + HTML via Jinja2

Outputs: page_definition.json, rendered HTML per variant.
"""
from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.fal_client import FalClient
from app.integrations.openai_client import OpenAIClient
from app.models import Brand, Insight

# ---------------------------------------------------------------------------
# JSON Schemas for OpenAI structured output
# ---------------------------------------------------------------------------

PAGE_STRATEGY_SCHEMA: dict[str, Any] = {
    "name": "page_strategy",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "page_type": {
                "type": "string",
                "description": (
                    "Landing page type: long_form_sales, lead_gen, or product"
                ),
            },
            "headline": {
                "type": "string",
                "description": "Primary above-the-fold headline",
            },
            "subheadline": {
                "type": "string",
                "description": "Supporting subheadline",
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": (
                                "Section identifier: hero, social_proof, "
                                "benefits, objection_handling, cta, faq"
                            ),
                        },
                        "purpose": {
                            "type": "string",
                            "description": "What this section achieves",
                        },
                    },
                    "required": ["id", "purpose"],
                    "additionalProperties": False,
                },
                "description": "Ordered list of page sections",
            },
            "offer_positioning": {
                "type": "object",
                "properties": {
                    "primary_offer": {"type": "string"},
                    "urgency_hook": {"type": "string"},
                    "guarantee": {"type": "string"},
                    "price_anchoring": {"type": "string"},
                },
                "required": [
                    "primary_offer",
                    "urgency_hook",
                    "guarantee",
                    "price_anchoring",
                ],
                "additionalProperties": False,
            },
            "tone": {
                "type": "string",
                "description": "Overall tone and voice for the page",
            },
            "color_scheme": {
                "type": "object",
                "properties": {
                    "primary": {"type": "string"},
                    "secondary": {"type": "string"},
                    "accent": {"type": "string"},
                    "background": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": [
                    "primary",
                    "secondary",
                    "accent",
                    "background",
                    "text",
                ],
                "additionalProperties": False,
            },
        },
        "required": [
            "page_type",
            "headline",
            "subheadline",
            "sections",
            "offer_positioning",
            "tone",
            "color_scheme",
        ],
        "additionalProperties": False,
    },
}

SECTION_CONTENT_SCHEMA: dict[str, Any] = {
    "name": "section_content",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "heading": {"type": "string"},
            "subheading": {"type": "string"},
            "body_html": {
                "type": "string",
                "description": "HTML content for the section body",
            },
            "cta_text": {"type": "string"},
            "cta_url": {"type": "string"},
            "image_prompt": {
                "type": "string",
                "description": "Prompt for AI image generation (if relevant)",
            },
        },
        "required": [
            "heading",
            "subheading",
            "body_html",
            "cta_text",
            "cta_url",
            "image_prompt",
        ],
        "additionalProperties": False,
    },
}

VARIATION_SCHEMA: dict[str, Any] = {
    "name": "section_variations",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "variations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "variant_id": {"type": "string"},
                        "heading": {"type": "string"},
                        "subheading": {"type": "string"},
                        "body_html": {"type": "string"},
                        "cta_text": {"type": "string"},
                    },
                    "required": [
                        "variant_id",
                        "heading",
                        "subheading",
                        "body_html",
                        "cta_text",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["variations"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Step 1: generate_page_strategy
# ---------------------------------------------------------------------------

async def generate_page_strategy(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Determine page type, section order, and offer positioning via OpenAI."""
    brand_id = (
        UUID(config["brand_id"])
        if isinstance(config.get("brand_id"), str)
        else config["brand_id"]
    )

    # Load brand with products and audiences
    stmt = (
        select(Brand)
        .where(Brand.id == brand_id)
        .options(selectinload(Brand.products), selectinload(Brand.audiences))
    )
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")

    # Select product
    product_id = config.get("product_id")
    product = None
    if product_id:
        pid = UUID(product_id) if isinstance(product_id, str) else product_id
        product = next((p for p in brand.products if p.id == pid), None)
    if product is None and brand.products:
        product = brand.products[0]

    # Select audience
    audience_id = config.get("audience_id")
    audience = None
    if audience_id:
        aid = UUID(audience_id) if isinstance(audience_id, str) else audience_id
        audience = next((a for a in brand.audiences if a.id == aid), None)
    if audience is None and brand.audiences:
        audience = brand.audiences[0]

    # Recent insights
    insights_stmt = (
        select(Insight)
        .where(Insight.brand_id == brand_id)
        .order_by(Insight.created_at.desc())
        .limit(5)
    )
    insights_result = await session.execute(insights_stmt)
    insights = insights_result.scalars().all()

    # Build prompts
    system_prompt = (
        "You are an expert landing page strategist and conversion rate "
        "optimizer. Design a high-converting landing page strategy based "
        "on the brand, product, audience, and performance insights provided. "
        "Choose the optimal page type, section ordering, and offer "
        "positioning to maximize conversions."
    )

    parts: list[str] = []
    parts.append(f"## Brand: {brand.name}")
    if brand.voice:
        parts.append(f"**Brand Voice:** {brand.voice}")
    if brand.visual_guidelines:
        parts.append(f"**Visual Guidelines:** {brand.visual_guidelines}")
    if brand.offers:
        offers_text = ", ".join(
            o["name"] if isinstance(o, dict) else str(o)
            for o in brand.offers
        )
        parts.append(f"**Available Offers:** {offers_text}")

    if product:
        parts.append(f"\n## Product: {product.name}")
        if product.description:
            parts.append(f"**Description:** {product.description}")
        if product.price:
            parts.append(f"**Price:** ${product.price}")

    if audience:
        parts.append(f"\n## Target Audience: {audience.name}")
        if audience.demographics:
            parts.append(f"**Demographics:** {audience.demographics}")
        if audience.interests:
            parts.append(f"**Interests:** {audience.interests}")

    if insights:
        parts.append("\n## Recent Performance Insights")
        for ins in insights:
            parts.append(
                f"- [{ins.insight_type}] {ins.content} "
                f"(confidence: {ins.confidence or 'N/A'})"
            )

    campaign_goal = config.get("campaign_goal")
    if campaign_goal:
        parts.append(f"\n## Campaign Goal\n{campaign_goal}")

    page_type_hint = config.get("page_type")
    if page_type_hint:
        parts.append(f"\n## Preferred Page Type: {page_type_hint}")

    parts.append(
        "\nDesign a landing page strategy with optimal section ordering "
        "and offer positioning. Include sections for: hero, social_proof, "
        "benefits, objection_handling, cta, and faq."
    )

    client = OpenAIClient()
    strategy = await client.structured_output(
        system=system_prompt,
        user="\n".join(parts),
        json_schema=PAGE_STRATEGY_SCHEMA,
        temperature=0.4,
        max_tokens=4096,
    )

    # Pass brand/product/audience data downstream
    return {
        "strategy": strategy,
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
        }
        if product
        else None,
        "audience": {
            "name": audience.name,
            "demographics": audience.demographics,
            "interests": audience.interests,
        }
        if audience
        else None,
    }


# ---------------------------------------------------------------------------
# Step 2: generate_sections
# ---------------------------------------------------------------------------

_SECTION_PROMPTS: dict[str, str] = {
    "hero": (
        "Write the hero section: a powerful headline, subheadline, and "
        "compelling body copy that immediately communicates the core value "
        "proposition. Include a strong call-to-action."
    ),
    "social_proof": (
        "Write a social proof section with testimonials, stats, and trust "
        "signals. Include specific numbers and outcomes. Format the body "
        "as HTML with testimonial cards."
    ),
    "benefits": (
        "Write a benefits section highlighting the top 3-5 benefits with "
        "icons, headings, and supporting copy. Focus on outcomes, not "
        "features. Format as HTML with a benefit grid."
    ),
    "objection_handling": (
        "Write an objection-handling section that proactively addresses the "
        "top 3-4 customer concerns. Use a conversational, reassuring tone. "
        "Include risk-reversal language."
    ),
    "cta": (
        "Write a conversion-focused CTA section with urgency, the primary "
        "offer, guarantee, and a clear call-to-action button. Make the "
        "value proposition crystal clear."
    ),
    "faq": (
        "Write an FAQ section with 5-7 questions and answers that address "
        "common purchase hesitations. Format answers as concise HTML "
        "paragraphs."
    ),
}


async def generate_sections(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Generate content for each planned section via OpenAI (fan-out)."""
    strategy_data = prev_outputs["generate_page_strategy"]
    strategy = strategy_data["strategy"]
    brand = strategy_data["brand"]
    product = strategy_data.get("product")
    audience = strategy_data.get("audience")

    system_prompt = (
        f"You are an expert landing page copywriter for {brand['name']}. "
        f"Brand voice: {brand.get('voice', 'Professional and engaging')}. "
        f"Page type: {strategy['page_type']}. "
        f"Tone: {strategy['tone']}. "
        f"Write conversion-optimized copy that drives action."
    )

    # Build context block reused across section prompts
    context_parts: list[str] = []
    if product:
        context_parts.append(
            f"Product: {product['name']} — {product.get('description', '')}"
        )
        if product.get("price"):
            context_parts.append(f"Price: ${product['price']}")
    if audience:
        context_parts.append(f"Target Audience: {audience['name']}")
    offer = strategy["offer_positioning"]
    context_parts.append(f"Primary Offer: {offer['primary_offer']}")
    context_parts.append(f"Urgency Hook: {offer['urgency_hook']}")
    context_parts.append(f"Guarantee: {offer['guarantee']}")
    context = "\n".join(context_parts)

    landing_url = config.get("landing_url", "#")
    client = OpenAIClient()
    sections: dict[str, dict[str, Any]] = {}

    for section_def in strategy["sections"]:
        section_id = section_def["id"]
        section_guidance = _SECTION_PROMPTS.get(
            section_id,
            f"Write compelling content for the '{section_id}' section.",
        )

        user_prompt = (
            f"{context}\n\n"
            f"Section purpose: {section_def['purpose']}\n\n"
            f"{section_guidance}\n\n"
            f"Use '{landing_url}' for the CTA URL."
        )

        content = await client.structured_output(
            system=system_prompt,
            user=user_prompt,
            json_schema=SECTION_CONTENT_SCHEMA,
            temperature=0.5,
            max_tokens=2048,
        )
        sections[section_id] = content

    return {"sections": sections}


# ---------------------------------------------------------------------------
# Step 3: generate_variations
# ---------------------------------------------------------------------------

async def generate_variations(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Create A/B test variants for hero and CTA sections."""
    strategy_data = prev_outputs["generate_page_strategy"]
    sections_data = prev_outputs["generate_sections"]
    strategy = strategy_data["strategy"]
    brand = strategy_data["brand"]
    sections = sections_data["sections"]
    num_variants = config.get("num_variants", 2)

    client = OpenAIClient()
    variations: dict[str, list[dict[str, Any]]] = {}

    # Generate variants for hero and cta sections
    for section_id in ("hero", "cta"):
        original = sections.get(section_id)
        if original is None:
            continue

        system_prompt = (
            f"You are an A/B testing specialist for {brand['name']}. "
            f"Create {num_variants} alternative variations of this "
            f"landing page section. Each variant should test a different "
            f"angle, hook, or emotional trigger while maintaining the "
            f"brand voice: {brand.get('voice', 'Professional')}."
        )

        user_prompt = (
            f"Original {section_id} section:\n"
            f"Heading: {original['heading']}\n"
            f"Subheading: {original['subheading']}\n"
            f"Body: {original['body_html']}\n"
            f"CTA: {original['cta_text']}\n\n"
            f"Page type: {strategy['page_type']}\n"
            f"Offer: {strategy['offer_positioning']['primary_offer']}\n\n"
            f"Generate {num_variants} distinct variations. Use variant IDs "
            f"like '{section_id}_v1', '{section_id}_v2', etc."
        )

        result = await client.structured_output(
            system=system_prompt,
            user=user_prompt,
            json_schema=VARIATION_SCHEMA,
            temperature=0.7,
            max_tokens=4096,
        )
        variations[section_id] = result["variations"]

    return {"variations": variations}


# ---------------------------------------------------------------------------
# Step 4: render_page
# ---------------------------------------------------------------------------

_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ strategy.headline }} | {{ brand.name }}</title>
  <style>
    :root {
      --color-primary: {{ colors.primary }};
      --color-secondary: {{ colors.secondary }};
      --color-accent: {{ colors.accent }};
      --color-bg: {{ colors.background }};
      --color-text: {{ colors.text }};
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
        Oxygen, Ubuntu, sans-serif;
      color: var(--color-text);
      background: var(--color-bg);
      line-height: 1.6;
    }
    .section { padding: 4rem 1.5rem; max-width: 960px; margin: 0 auto; }
    .section--hero {
      text-align: center;
      padding: 6rem 1.5rem;
      background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
      color: #fff;
      max-width: 100%;
    }
    .section--hero h1 { font-size: 2.5rem; margin-bottom: 1rem; }
    .section--hero p { font-size: 1.25rem; margin-bottom: 2rem; opacity: 0.9; }
    .section--cta {
      text-align: center;
      background: var(--color-primary);
      color: #fff;
      max-width: 100%;
    }
    .section h2 { font-size: 1.75rem; margin-bottom: 1rem; color: var(--color-primary); }
    .section h3 { font-size: 1.1rem; margin-bottom: 0.5rem; }
    .section p, .section li { margin-bottom: 0.75rem; }
    .btn {
      display: inline-block;
      padding: 0.875rem 2rem;
      background: var(--color-accent);
      color: #fff;
      text-decoration: none;
      border-radius: 6px;
      font-weight: 600;
      font-size: 1.1rem;
      transition: opacity 0.2s;
    }
    .btn:hover { opacity: 0.9; }
    {% if hero_image_url %}
    .hero-image {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      margin-top: 2rem;
    }
    {% endif %}
  </style>
</head>
<body>
{% for section in ordered_sections %}
  <section class="section section--{{ section.id }}" id="{{ section.id }}">
    <h2>{{ section.content.heading }}</h2>
    {% if section.content.subheading %}
    <p><em>{{ section.content.subheading }}</em></p>
    {% endif %}
    <div>{{ section.content.body_html | safe }}</div>
    {% if section.id == "hero" and hero_image_url %}
    <img class="hero-image" src="{{ hero_image_url }}" alt="{{ strategy.headline }}">
    {% endif %}
    {% if section.content.cta_text %}
    <p style="margin-top:1.5rem;">
      <a class="btn" href="{{ section.content.cta_url }}">{{ section.content.cta_text }}</a>
    </p>
    {% endif %}
  </section>
{% endfor %}
</body>
</html>
"""


async def render_page(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Render structured JSON page definition + HTML per variant."""
    from jinja2 import Template

    strategy_data = prev_outputs["generate_page_strategy"]
    sections_data = prev_outputs["generate_sections"]
    variations_data = prev_outputs["generate_variations"]

    strategy = strategy_data["strategy"]
    brand = strategy_data["brand"]
    sections = sections_data["sections"]
    variations = variations_data["variations"]

    output_dir = os.path.join("outputs", str(job_id), "landing_pages")
    os.makedirs(output_dir, exist_ok=True)

    # Optional hero image generation via FAL
    hero_image_url: str | None = None
    if config.get("generate_hero_image"):
        hero_section = sections.get("hero")
        if hero_section and hero_section.get("image_prompt"):
            fal = FalClient()
            result = await fal.generate_image(hero_section["image_prompt"])
            images = result.get("images", [])
            if images:
                image_url = images[0].get("url", "")
                if image_url:
                    downloaded = await fal.download_file(
                        image_url,
                        f"{job_id}_hero.png",
                    )
                    hero_image_url = str(downloaded)

    # Build ordered section list from strategy
    ordered_sections = []
    for section_def in strategy["sections"]:
        sid = section_def["id"]
        if sid in sections:
            ordered_sections.append({"id": sid, "content": sections[sid]})

    colors = strategy["color_scheme"]
    template = Template(_PAGE_TEMPLATE)
    rendered_files: list[dict[str, str]] = []

    # Render control (original) variant
    control_html = template.render(
        strategy=strategy,
        brand=brand,
        colors=colors,
        ordered_sections=ordered_sections,
        hero_image_url=hero_image_url,
    )
    control_path = os.path.join(output_dir, "control.html")
    with open(control_path, "w") as f:
        f.write(control_html)
    rendered_files.append({"variant": "control", "path": control_path})

    # Render each A/B variant (swap hero and/or cta content)
    for section_id, variant_list in variations.items():
        for variant in variant_list:
            vid = variant["variant_id"]
            # Build variant sections by replacing the varied section
            variant_sections = []
            for sec in ordered_sections:
                if sec["id"] == section_id:
                    variant_content = {
                        "heading": variant["heading"],
                        "subheading": variant["subheading"],
                        "body_html": variant["body_html"],
                        "cta_text": variant["cta_text"],
                        "cta_url": sections[section_id].get("cta_url", "#"),
                        "image_prompt": sections[section_id].get(
                            "image_prompt", ""
                        ),
                    }
                    variant_sections.append(
                        {"id": section_id, "content": variant_content}
                    )
                else:
                    variant_sections.append(sec)

            variant_html = template.render(
                strategy=strategy,
                brand=brand,
                colors=colors,
                ordered_sections=variant_sections,
                hero_image_url=hero_image_url,
            )
            variant_path = os.path.join(output_dir, f"{vid}.html")
            with open(variant_path, "w") as f:
                f.write(variant_html)
            rendered_files.append({"variant": vid, "path": variant_path})

    # Write page definition JSON
    page_definition = {
        "strategy": strategy,
        "sections": sections,
        "variations": variations,
        "hero_image_url": hero_image_url,
    }
    definition_path = os.path.join(output_dir, "page_definition.json")
    with open(definition_path, "w") as f:
        json.dump(page_definition, f, indent=2)

    # Create Output records for gallery and file serving
    from app.models.output import Output

    for rf in rendered_files:
        html_output = Output(
            job_id=job_id,
            pipeline_name="landing_pages",
            output_type="html",
            file_path=rf["path"],
            metadata_={
                "variant": rf["variant"],
                "page_type": strategy.get("page_type", ""),
                "headline": strategy.get("headline", ""),
            },
        )
        session.add(html_output)

    definition_output = Output(
        job_id=job_id,
        pipeline_name="landing_pages",
        output_type="json",
        file_path=definition_path,
        metadata_={
            "format": "page_definition",
            "variant_count": len(rendered_files),
        },
    )
    session.add(definition_output)
    await session.flush()

    return {
        "definition_path": definition_path,
        "rendered_files": rendered_files,
        "page_definition": page_definition,
        "variant_count": len(rendered_files),
    }


# ---------------------------------------------------------------------------
# Pipeline registration
# ---------------------------------------------------------------------------

from app.pipelines import PipelineDefinition, register  # noqa: E402

register(
    PipelineDefinition(
        name="landing_pages",
        steps=[
            ("generate_page_strategy", generate_page_strategy),
            ("generate_sections", generate_sections),
            ("generate_variations", generate_variations),
            ("render_page", render_page),
        ],
    )
)
