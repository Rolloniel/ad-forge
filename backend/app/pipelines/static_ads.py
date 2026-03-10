"""Static Ad Creative Engine pipeline.

Steps:
  1. generate_angle_matrix  — OpenAI generates creative angles from product data
  2. generate_ad_copy       — fan-out: per angle, generate headline/subhead/CTA
  3. generate_base_images   — per angle, generate product/lifestyle images via FAL
  4. compose_final_ads      — composite text overlay onto images with Pillow

Outputs: PNG files per dimension per variation.
Ad dimensions: 1080x1080 (feed), 1080x1920 (story), 1200x628 (display).
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from uuid import UUID

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.fal_client import FalClient
from app.integrations.openai_client import OpenAIClient
from app.models import Brand

# ---------------------------------------------------------------------------
# Ad dimensions: (width, height, label)
# ---------------------------------------------------------------------------

AD_DIMENSIONS: list[tuple[int, int, str]] = [
    (1080, 1080, "feed"),
    (1080, 1920, "story"),
    (1200, 628, "display"),
]

# ---------------------------------------------------------------------------
# JSON Schemas for OpenAI structured output
# ---------------------------------------------------------------------------

ANGLE_MATRIX_SCHEMA: dict[str, Any] = {
    "name": "angle_matrix",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "angles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Short slug for the angle (e.g. 'social_proof')",
                        },
                        "theme": {
                            "type": "string",
                            "description": "One-line creative theme",
                        },
                        "visual_direction": {
                            "type": "string",
                            "description": "Description of the visual style for image generation",
                        },
                        "emotional_hook": {
                            "type": "string",
                            "description": "The emotional trigger this angle targets",
                        },
                    },
                    "required": ["name", "theme", "visual_direction", "emotional_hook"],
                    "additionalProperties": False,
                },
                "description": "3-5 creative angles for the ad campaign",
            },
        },
        "required": ["angles"],
        "additionalProperties": False,
    },
}

AD_COPY_SCHEMA: dict[str, Any] = {
    "name": "ad_copy_variations",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "variations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {
                            "type": "string",
                            "description": "Punchy headline, under 40 characters",
                        },
                        "subhead": {
                            "type": "string",
                            "description": "Supporting subhead, 1 sentence",
                        },
                        "cta": {
                            "type": "string",
                            "description": "Call-to-action text (e.g. 'Shop Now')",
                        },
                    },
                    "required": ["headline", "subhead", "cta"],
                    "additionalProperties": False,
                },
                "description": "2-3 copy variations for this angle",
            },
        },
        "required": ["variations"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Step 1: generate_angle_matrix
# ---------------------------------------------------------------------------

async def generate_angle_matrix(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Load brand/product data and generate creative angles via OpenAI."""
    brand_id = UUID(config["brand_id"]) if isinstance(config.get("brand_id"), str) else config["brand_id"]
    product_id = config.get("product_id")

    stmt = (
        select(Brand)
        .where(Brand.id == brand_id)
        .options(selectinload(Brand.products))
    )
    result = await session.execute(stmt)
    brand = result.scalar_one_or_none()
    if brand is None:
        raise ValueError(f"Brand {brand_id} not found")

    product = None
    if product_id:
        pid = UUID(product_id) if isinstance(product_id, str) else product_id
        product = next((p for p in brand.products if p.id == pid), None)
    if product is None and brand.products:
        product = brand.products[0]

    brand_data = {
        "name": brand.name,
        "voice": brand.voice,
        "visual_guidelines": brand.visual_guidelines,
    }
    product_data = {
        "name": product.name,
        "description": product.description,
        "price": str(product.price) if product.price else None,
        "image_url": product.image_url,
    } if product else None

    system = (
        "You are an expert advertising creative director specializing in "
        "performance marketing for eCommerce brands. Generate creative angles "
        "that will drive conversions across social media ad placements."
    )

    parts: list[str] = [f"## Brand: {brand_data['name']}"]
    if brand_data.get("voice"):
        parts.append(f"**Brand Voice:** {brand_data['voice']}")
    if brand_data.get("visual_guidelines"):
        parts.append(f"**Visual Guidelines:** {brand_data['visual_guidelines']}")
    if product_data:
        parts.append(f"\n## Product: {product_data['name']}")
        if product_data.get("description"):
            parts.append(f"**Description:** {product_data['description']}")
        if product_data.get("price"):
            parts.append(f"**Price:** ${product_data['price']}")

    num_angles = config.get("num_angles", 4)
    parts.append(
        f"\nGenerate {num_angles} distinct creative angles for static ad creatives. "
        "Each angle should target a different emotional trigger and suggest a "
        "unique visual direction for image generation."
    )

    client = OpenAIClient()
    angles_result = await client.structured_output(
        system=system,
        user="\n".join(parts),
        json_schema=ANGLE_MATRIX_SCHEMA,
        temperature=0.6,
        max_tokens=2048,
    )

    return {
        "brand": brand_data,
        "product": product_data,
        "angles": angles_result["angles"],
    }


# ---------------------------------------------------------------------------
# Step 2: generate_ad_copy
# ---------------------------------------------------------------------------

async def generate_ad_copy(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Fan-out: per angle, generate headline/subhead/CTA variations via OpenAI."""
    angle_data = prev_outputs["generate_angle_matrix"]
    angles = angle_data["angles"]
    brand = angle_data["brand"]
    product = angle_data["product"]

    client = OpenAIClient()
    variations_per_angle = config.get("variations_per_angle", 3)

    system = (
        f"You are an expert direct-response ad copywriter for {brand['name']}. "
        f"Brand voice: {brand.get('voice', 'Professional and engaging')}. "
        "Write compelling, concise copy for static image ads."
    )

    async def _generate_for_angle(angle: dict[str, Any]) -> dict[str, Any]:
        user = (
            f"Generate {variations_per_angle} ad copy variations for the "
            f"creative angle: '{angle['name']}'\n\n"
            f"Theme: {angle['theme']}\n"
            f"Emotional hook: {angle['emotional_hook']}\n\n"
        )
        if product:
            user += (
                f"Product: {product['name']}\n"
                f"Description: {product.get('description', '')}\n"
                f"Price: ${product.get('price', 'N/A')}\n\n"
            )
        user += (
            "For each variation provide:\n"
            "- headline: Punchy, under 40 characters\n"
            "- subhead: Supporting line, 1 sentence\n"
            "- cta: Call-to-action button text\n"
        )
        result = await client.structured_output(
            system=system,
            user=user,
            json_schema=AD_COPY_SCHEMA,
            temperature=0.5,
            max_tokens=1024,
        )
        return {
            "angle": angle["name"],
            "theme": angle["theme"],
            "variations": result["variations"],
        }

    copy_results = await asyncio.gather(*[
        _generate_for_angle(angle) for angle in angles
    ])

    return {
        "copy_by_angle": list(copy_results),
        "total_variations": sum(len(c["variations"]) for c in copy_results),
    }


# ---------------------------------------------------------------------------
# Step 3: generate_base_images
# ---------------------------------------------------------------------------

async def generate_base_images(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Per angle, generate product/lifestyle images via FAL Flux Pro."""
    angle_data = prev_outputs["generate_angle_matrix"]
    angles = angle_data["angles"]
    brand = angle_data["brand"]
    product = angle_data["product"]

    fal = FalClient()

    output_dir = os.path.join("outputs", str(job_id), "static_ads", "base_images")
    os.makedirs(output_dir, exist_ok=True)

    async def _generate_for_angle(angle: dict[str, Any]) -> dict[str, Any]:
        prompt_parts = [
            f"Professional advertising product photography for {brand['name']}.",
            f"Visual direction: {angle['visual_direction']}.",
        ]
        if product:
            prompt_parts.append(f"Product: {product['name']}.")
            if product.get("description"):
                prompt_parts.append(product["description"])
        if brand.get("visual_guidelines"):
            prompt_parts.append(f"Style: {brand['visual_guidelines']}.")
        prompt_parts.append(
            "Clean composition with space for text overlay. "
            "High quality, studio lighting, commercial advertising style."
        )
        prompt = " ".join(prompt_parts)

        result = await fal.generate_image(
            prompt,
            image_size="square_hd",
            num_images=1,
        )

        image_url = result["images"][0]["url"]
        filename = f"{angle['name']}.png"
        local_path = await fal.download_file(image_url, filename)
        # Move to job-specific output dir
        dest = os.path.join(output_dir, filename)
        os.rename(str(local_path), dest)

        return {
            "angle": angle["name"],
            "image_path": dest,
            "source_url": image_url,
        }

    image_results = await asyncio.gather(*[
        _generate_for_angle(angle) for angle in angles
    ])

    return {
        "images": list(image_results),
    }


# ---------------------------------------------------------------------------
# Step 4: compose_final_ads
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to an RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _luminance(r: int, g: int, b: int) -> float:
    """Relative luminance of an sRGB color."""
    vals = []
    for c in (r, g, b):
        v = c / 255.0
        vals.append(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _text_color_for_bg(bg_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Pick white or black text based on background luminance."""
    return (255, 255, 255) if _luminance(*bg_rgb) < 0.5 else (0, 0, 0)


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TTF font, falling back to the default bitmap font."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    return lines or [text]


def _compose_ad(
    base_image_path: str,
    width: int,
    height: int,
    headline: str,
    subhead: str,
    cta: str,
    brand_color: tuple[int, int, int],
) -> Image.Image:
    """Compose a single ad image with text overlay on the base image."""
    base = Image.open(base_image_path).convert("RGBA")
    base = base.resize((width, height), Image.LANCZOS)

    # Semi-transparent overlay at bottom for text readability
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient overlay on bottom 40% of image
    overlay_height = int(height * 0.4)
    overlay_top = height - overlay_height
    for y in range(overlay_height):
        alpha = int(180 * (y / overlay_height))
        draw.line(
            [(0, overlay_top + y), (width, overlay_top + y)],
            fill=(0, 0, 0, alpha),
        )

    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)

    text_color = (255, 255, 255)
    padding = int(width * 0.06)
    text_area_width = width - (padding * 2)

    # Font sizes proportional to image dimensions
    headline_size = max(int(height * 0.05), 20)
    subhead_size = max(int(height * 0.03), 14)
    cta_size = max(int(height * 0.028), 12)

    headline_font = _get_font(headline_size)
    subhead_font = _get_font(subhead_size)
    cta_font = _get_font(cta_size)

    # Layout from bottom up
    cta_padding_h = int(cta_size * 0.8)
    cta_padding_v = int(cta_size * 0.4)

    # CTA button
    cta_bbox = draw.textbbox((0, 0), cta, font=cta_font)
    cta_w = cta_bbox[2] - cta_bbox[0] + cta_padding_h * 2
    cta_h = cta_bbox[3] - cta_bbox[1] + cta_padding_v * 2
    cta_y = height - padding - cta_h
    cta_x = padding

    draw.rounded_rectangle(
        [cta_x, cta_y, cta_x + cta_w, cta_y + cta_h],
        radius=int(cta_h * 0.3),
        fill=brand_color,
    )
    cta_text_color = _text_color_for_bg(brand_color)
    draw.text(
        (cta_x + cta_padding_h, cta_y + cta_padding_v),
        cta,
        font=cta_font,
        fill=cta_text_color,
    )

    # Subhead
    subhead_lines = _wrap_text(draw, subhead, subhead_font, text_area_width)
    line_height = int(subhead_size * 1.3)
    subhead_block_height = len(subhead_lines) * line_height
    subhead_y = cta_y - int(cta_size * 0.6) - subhead_block_height
    for i, line in enumerate(subhead_lines):
        draw.text(
            (padding, subhead_y + i * line_height),
            line,
            font=subhead_font,
            fill=(*text_color, 200),
        )

    # Headline
    headline_lines = _wrap_text(draw, headline, headline_font, text_area_width)
    headline_line_height = int(headline_size * 1.2)
    headline_block_height = len(headline_lines) * headline_line_height
    headline_y = subhead_y - int(subhead_size * 0.4) - headline_block_height
    for i, line in enumerate(headline_lines):
        draw.text(
            (padding, headline_y + i * headline_line_height),
            line,
            font=headline_font,
            fill=text_color,
        )

    return base.convert("RGB")


async def compose_final_ads(
    *,
    job_id: UUID,
    config: dict[str, Any],
    prev_outputs: dict[str, dict[str, Any]],
    session: AsyncSession,
) -> dict[str, Any]:
    """Composite text overlay onto images with brand colors."""
    angle_data = prev_outputs["generate_angle_matrix"]
    copy_data = prev_outputs["generate_ad_copy"]
    image_data = prev_outputs["generate_base_images"]

    brand = angle_data["brand"]
    copy_by_angle = copy_data["copy_by_angle"]
    images = image_data["images"]

    # Build lookup: angle_name -> image_path
    image_lookup: dict[str, str] = {
        img["angle"]: img["image_path"] for img in images
    }

    # Parse brand color from config or visual_guidelines, default to a blue
    brand_color_hex = config.get("brand_color", "#2563EB")
    brand_color = _hex_to_rgb(brand_color_hex)

    output_dir = os.path.join("outputs", str(job_id), "static_ads", "final")
    os.makedirs(output_dir, exist_ok=True)

    composed_ads: list[dict[str, Any]] = []

    for angle_copy in copy_by_angle:
        angle_name = angle_copy["angle"]
        base_path = image_lookup.get(angle_name)
        if not base_path:
            continue

        for var_idx, variation in enumerate(angle_copy["variations"]):
            for width, height, dim_label in AD_DIMENSIONS:
                ad_image = _compose_ad(
                    base_image_path=base_path,
                    width=width,
                    height=height,
                    headline=variation["headline"],
                    subhead=variation["subhead"],
                    cta=variation["cta"],
                    brand_color=brand_color,
                )
                filename = f"{angle_name}_v{var_idx}_{dim_label}_{width}x{height}.png"
                filepath = os.path.join(output_dir, filename)
                ad_image.save(filepath, "PNG")

                composed_ads.append({
                    "angle": angle_name,
                    "variation_index": var_idx,
                    "dimension": dim_label,
                    "size": f"{width}x{height}",
                    "headline": variation["headline"],
                    "subhead": variation["subhead"],
                    "cta": variation["cta"],
                    "file_path": filepath,
                })

    # Write manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(
            {
                "job_id": str(job_id),
                "brand": brand["name"],
                "total_ads": len(composed_ads),
                "dimensions": [
                    {"width": w, "height": h, "label": l}
                    for w, h, l in AD_DIMENSIONS
                ],
                "ads": composed_ads,
            },
            f,
            indent=2,
        )

    # Create Output records for gallery and file serving
    from app.models.output import Output

    for ad in composed_ads:
        ad_output = Output(
            job_id=job_id,
            pipeline_name="static_ads",
            output_type="image",
            file_path=ad["file_path"],
            metadata_={
                "angle": ad["angle"],
                "variation_index": ad["variation_index"],
                "dimension": ad["dimension"],
                "size": ad["size"],
                "headline": ad["headline"],
            },
        )
        session.add(ad_output)

    manifest_output = Output(
        job_id=job_id,
        pipeline_name="static_ads",
        output_type="json",
        file_path=manifest_path,
        metadata_={
            "format": "manifest",
            "total_ads": len(composed_ads),
        },
    )
    session.add(manifest_output)
    await session.flush()

    return {
        "total_ads": len(composed_ads),
        "output_dir": output_dir,
        "manifest_path": manifest_path,
        "ads": composed_ads,
    }


# ---------------------------------------------------------------------------
# Pipeline registration
# ---------------------------------------------------------------------------

from app.pipelines import PipelineDefinition, register  # noqa: E402

register(
    PipelineDefinition(
        name="static_ads",
        steps=[
            ("generate_angle_matrix", generate_angle_matrix),
            ("generate_ad_copy", generate_ad_copy),
            ("generate_base_images", generate_base_images),
            ("compose_final_ads", compose_final_ads),
        ],
    )
)
