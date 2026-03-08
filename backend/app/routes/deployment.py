from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.integrations.openai_client import OpenAIClient
from app.models.brand import Audience
from app.models.output import Output, PerformanceMetric

router = APIRouter(prefix="/api/deployment", tags=["deployment"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CampaignConfig(BaseModel):
    campaign_objective: str = "CONVERSIONS"
    daily_budget: float = 50.0
    currency: str = "USD"
    landing_url: str = "https://example.com"


class PreviewRequest(BaseModel):
    output_ids: list[uuid.UUID]
    campaign_config: CampaignConfig = CampaignConfig()


class AdCreative(BaseModel):
    primary_text: str
    headline: str
    description: str
    call_to_action: str
    link_url: str


class MetaAd(BaseModel):
    ad_id: str
    name: str
    status: str
    creative: AdCreative
    test_key: str | None = None


class MetaAdSet(BaseModel):
    ad_set_id: str
    name: str
    status: str
    daily_budget: float
    billing_event: str
    optimization_goal: str
    targeting: dict[str, Any]
    ads: list[MetaAd]


class MetaCampaign(BaseModel):
    campaign_id: str
    name: str
    objective: str
    status: str
    special_ad_categories: list[str]
    budget: dict[str, Any]


class MetaPayload(BaseModel):
    platform: str = "meta"
    campaign: MetaCampaign
    ad_sets: list[MetaAdSet]
    total_ads: int


class TikTokAd(BaseModel):
    ad_id: str
    ad_name: str
    status: str
    ad_text: str
    call_to_action: str
    landing_page_url: str
    display_name: str
    test_key: str | None = None


class TikTokAdGroup(BaseModel):
    adgroup_id: str
    adgroup_name: str
    status: str
    budget: float
    budget_mode: str
    optimization_goal: str
    placement_type: str
    audience: dict[str, Any]
    ads: list[TikTokAd]


class TikTokCampaign(BaseModel):
    campaign_id: str
    campaign_name: str
    objective_type: str
    status: str
    budget: float
    budget_mode: str


class TikTokPayload(BaseModel):
    platform: str = "tiktok"
    campaign: TikTokCampaign
    ad_groups: list[TikTokAdGroup]
    total_ads: int


class CampaignStrategy(BaseModel):
    summary: str
    budget_allocation: list[dict[str, Any]]
    optimization_recommendations: list[str]
    suggested_test_duration_days: int
    priority_audiences: list[str]


class PreviewResponse(BaseModel):
    meta_payload: MetaPayload
    tiktok_payload: TikTokPayload
    campaign_strategy: CampaignStrategy
    source_output_ids: list[uuid.UUID]


class MatrixEntry(BaseModel):
    entry_id: int
    angle: str
    variation_index: int
    copy: dict[str, str]
    audience: dict[str, Any]
    test_key: str
    projected_metrics: dict[str, Any] | None = None


class MatrixDimensions(BaseModel):
    angles: int
    variations_per_angle: int
    audiences: int


class TestingMatrix(BaseModel):
    total_combinations: int
    dimensions: MatrixDimensions
    entries: list[MatrixEntry]


class MatricesResponse(BaseModel):
    items: list[TestingMatrix]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CAMPAIGN_STRATEGY_SCHEMA = {
    "name": "campaign_strategy",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "1-2 sentence overview of the recommended campaign strategy",
            },
            "budget_allocation": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "audience": {"type": "string"},
                        "percentage": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["audience", "percentage", "rationale"],
                    "additionalProperties": False,
                },
            },
            "optimization_recommendations": {
                "type": "array",
                "items": {"type": "string"},
            },
            "suggested_test_duration_days": {"type": "integer"},
            "priority_audiences": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "summary",
            "budget_allocation",
            "optimization_recommendations",
            "suggested_test_duration_days",
            "priority_audiences",
        ],
        "additionalProperties": False,
    },
}


def _extract_copy_entries(
    outputs: list[Output],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Extract copy variation and matrix entries from output metadata.

    Returns (copy_variations, matrix_entries).
    """
    copy_variations: list[dict[str, Any]] = []
    matrix_entries: list[dict[str, Any]] = []

    for output in outputs:
        meta = output.metadata_ or {}

        if output.output_type == "copy_variations" and "copy_variations" in meta:
            copy_variations.extend(meta["copy_variations"])
        elif output.output_type == "testing_matrix" and "testing_matrix" in meta:
            matrix_entries.extend(meta["testing_matrix"].get("entries", []))
        elif output.output_type == "deployment_payloads":
            # Already-built payloads; extract entries from nested data
            pass

        # Fallback: try reading the file_path if metadata is sparse
        if not copy_variations and not matrix_entries and output.file_path:
            try:
                from pathlib import Path

                fp = Path(output.file_path)
                if fp.is_file():
                    data = json.loads(fp.read_text())
                    if isinstance(data, list) and data and "angle" in data[0]:
                        copy_variations.extend(data)
                    elif isinstance(data, dict) and "entries" in data:
                        matrix_entries.extend(data["entries"])
            except (json.JSONDecodeError, OSError):
                pass

    return copy_variations, matrix_entries


def _build_meta_payload(
    copy_variations: list[dict[str, Any]],
    audiences: list[dict[str, Any]],
    config: CampaignConfig,
    brand_name: str,
    product_name: str,
) -> dict[str, Any]:
    """Build a mock Meta Ads API campaign payload from copy variations."""
    campaign_id = str(uuid.uuid4())
    ad_sets: list[dict[str, Any]] = []

    for audience in audiences:
        ad_set_id = str(uuid.uuid4())
        aud_name = audience.get("name", "Unknown")
        ads: list[dict[str, Any]] = []

        for cv in copy_variations:
            angle = cv.get("angle", "unknown")
            for var_idx, variation in enumerate(cv.get("variations", [])):
                ads.append({
                    "ad_id": str(uuid.uuid4()),
                    "name": f"{product_name} - {angle} - v{var_idx}",
                    "status": "PAUSED",
                    "creative": {
                        "primary_text": variation.get("primary_text", ""),
                        "headline": variation.get("headline", ""),
                        "description": variation.get("description", ""),
                        "call_to_action": variation.get("cta", "Shop Now"),
                        "link_url": config.landing_url,
                    },
                    "test_key": f"{angle}__v{var_idx}__{aud_name.replace(' ', '_').lower()}",
                })

        ad_sets.append({
            "ad_set_id": ad_set_id,
            "name": f"{brand_name} - {aud_name}",
            "status": "PAUSED",
            "daily_budget": config.daily_budget,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": config.campaign_objective,
            "targeting": {
                "audience_name": aud_name,
                "demographics": audience.get("demographics", ""),
            },
            "ads": ads,
        })

    return {
        "platform": "meta",
        "campaign": {
            "campaign_id": campaign_id,
            "name": f"{brand_name} - {product_name} - Ad Copy Test",
            "objective": config.campaign_objective,
            "status": "PAUSED",
            "special_ad_categories": [],
            "budget": {
                "daily_budget": config.daily_budget,
                "currency": config.currency,
            },
        },
        "ad_sets": ad_sets,
        "total_ads": sum(len(s["ads"]) for s in ad_sets),
    }


def _build_tiktok_payload(
    copy_variations: list[dict[str, Any]],
    audiences: list[dict[str, Any]],
    config: CampaignConfig,
    brand_name: str,
    product_name: str,
) -> dict[str, Any]:
    """Build a mock TikTok Ads API campaign payload from copy variations."""
    campaign_id = str(uuid.uuid4())
    objective_type = (
        "CONVERSIONS" if config.campaign_objective == "CONVERSIONS" else "TRAFFIC"
    )
    optimization_goal = (
        "CONVERT" if config.campaign_objective == "CONVERSIONS" else "CLICK"
    )

    ad_groups: list[dict[str, Any]] = []

    for audience in audiences:
        ad_group_id = str(uuid.uuid4())
        aud_name = audience.get("name", "Unknown")
        ads: list[dict[str, Any]] = []

        for cv in copy_variations:
            angle = cv.get("angle", "unknown")
            for var_idx, variation in enumerate(cv.get("variations", [])):
                ads.append({
                    "ad_id": str(uuid.uuid4()),
                    "ad_name": f"{product_name} - {angle} - v{var_idx}",
                    "status": "DISABLE",
                    "ad_text": variation.get("primary_text", ""),
                    "call_to_action": variation.get("cta", "Shop Now"),
                    "landing_page_url": config.landing_url,
                    "display_name": brand_name,
                    "test_key": f"{angle}__v{var_idx}__{aud_name.replace(' ', '_').lower()}",
                })

        ad_groups.append({
            "adgroup_id": ad_group_id,
            "adgroup_name": f"{brand_name} - {aud_name}",
            "status": "DISABLE",
            "budget": config.daily_budget,
            "budget_mode": "BUDGET_MODE_DAY",
            "optimization_goal": optimization_goal,
            "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
            "audience": {
                "audience_name": aud_name,
                "demographics": audience.get("demographics", ""),
            },
            "ads": ads,
        })

    return {
        "platform": "tiktok",
        "campaign": {
            "campaign_id": campaign_id,
            "campaign_name": f"{brand_name} - {product_name} - Ad Copy Test",
            "objective_type": objective_type,
            "status": "DISABLE",
            "budget": config.daily_budget,
            "budget_mode": "BUDGET_MODE_DAY",
        },
        "ad_groups": ad_groups,
        "total_ads": sum(len(ag["ads"]) for ag in ad_groups),
    }


async def _generate_campaign_strategy(
    copy_variations: list[dict[str, Any]],
    audiences: list[dict[str, Any]],
    config: CampaignConfig,
    brand_name: str,
    product_name: str,
) -> dict[str, Any]:
    """Use OpenAI to generate a realistic campaign strategy."""
    client = OpenAIClient()

    angles = [cv.get("angle", "unknown") for cv in copy_variations]
    total_variations = sum(len(cv.get("variations", [])) for cv in copy_variations)
    audience_names = [a.get("name", "Unknown") for a in audiences]

    system_prompt = (
        "You are a senior paid media strategist specializing in Meta and TikTok "
        "advertising for DTC / eCommerce brands. Given a campaign setup, generate "
        "a realistic testing strategy including budget allocation across audiences, "
        "optimization recommendations, and test duration."
    )

    user_prompt = (
        f"Brand: {brand_name}\n"
        f"Product: {product_name}\n"
        f"Campaign objective: {config.campaign_objective}\n"
        f"Daily budget: ${config.daily_budget} {config.currency}\n"
        f"Creative angles ({len(angles)}): {', '.join(angles)}\n"
        f"Total copy variations: {total_variations}\n"
        f"Audiences ({len(audience_names)}): {', '.join(audience_names)}\n\n"
        f"Generate a campaign testing strategy with budget allocation percentages "
        f"per audience, optimization recommendations, suggested test duration, "
        f"and priority audiences to test first."
    )

    try:
        result = await client.structured_output(
            system=system_prompt,
            user=user_prompt,
            json_schema=CAMPAIGN_STRATEGY_SCHEMA,
        )
        return result
    except Exception:
        # Fallback strategy if OpenAI is unavailable
        even_pct = round(100 / max(len(audience_names), 1), 1)
        return {
            "summary": (
                f"Recommended {config.campaign_objective.lower()} campaign for "
                f"{brand_name} {product_name} across {len(audience_names)} audiences "
                f"with {total_variations} creative variations."
            ),
            "budget_allocation": [
                {
                    "audience": name,
                    "percentage": even_pct,
                    "rationale": "Even split for initial testing phase",
                }
                for name in audience_names
            ],
            "optimization_recommendations": [
                "Start with broad targeting then narrow based on performance",
                "Monitor CTR and CPA for the first 72 hours before scaling",
                "Pause underperforming creatives after statistical significance",
            ],
            "suggested_test_duration_days": 7,
            "priority_audiences": audience_names[:3],
        }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/preview", response_model=PreviewResponse, status_code=201)
async def preview_campaign(
    body: PreviewRequest,
    session: AsyncSession = Depends(get_session),
) -> PreviewResponse:
    """Generate mock Meta and TikTok Ads API payloads from pipeline outputs.

    Takes a set of output IDs and campaign configuration, fetches the
    associated copy variations and audience data, builds platform-specific
    campaign payloads, and uses OpenAI to generate a realistic campaign
    strategy.
    """
    if not body.output_ids:
        raise HTTPException(status_code=400, detail="output_ids must not be empty")

    # Fetch outputs with their jobs (to get brand info)
    result = await session.execute(
        select(Output)
        .where(Output.id.in_(body.output_ids))
        .options(selectinload(Output.job))
    )
    outputs = list(result.scalars().all())

    if not outputs:
        raise HTTPException(status_code=404, detail="No outputs found for given IDs")

    found_ids = {o.id for o in outputs}
    missing = [str(oid) for oid in body.output_ids if oid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Outputs not found: {', '.join(missing)}",
        )

    # Resolve brand and product info from the first output's job
    job = outputs[0].job
    brand_name = "Brand"
    product_name = "Product"
    audiences: list[dict[str, Any]] = []

    if job and job.brand_id:
        from app.models.brand import Brand

        brand_result = await session.execute(
            select(Brand)
            .where(Brand.id == job.brand_id)
            .options(
                selectinload(Brand.products),
                selectinload(Brand.audiences),
            )
        )
        brand = brand_result.scalar_one_or_none()
        if brand:
            brand_name = brand.name
            audiences = [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "demographics": a.demographics or "",
                }
                for a in brand.audiences
            ]
            # Use product from job config or first product
            job_config = job.config or {}
            product_id = job_config.get("product_id")
            for p in brand.products:
                if product_id and str(p.id) == product_id:
                    product_name = p.name
                    break
            else:
                if brand.products:
                    product_name = brand.products[0].name

    # Provide default audience if none found
    if not audiences:
        audiences = [{"id": "", "name": "General Audience", "demographics": "18-65"}]

    # Extract copy data from outputs
    copy_variations, _matrix_entries = _extract_copy_entries(outputs)

    if not copy_variations:
        raise HTTPException(
            status_code=400,
            detail=(
                "No copy variations found in the provided outputs. "
                "Ensure output_ids reference copy_variations or testing_matrix outputs."
            ),
        )

    config = body.campaign_config

    # Build platform payloads
    meta_raw = _build_meta_payload(
        copy_variations, audiences, config, brand_name, product_name
    )
    tiktok_raw = _build_tiktok_payload(
        copy_variations, audiences, config, brand_name, product_name
    )

    # Generate AI campaign strategy
    strategy = await _generate_campaign_strategy(
        copy_variations, audiences, config, brand_name, product_name
    )

    return PreviewResponse(
        meta_payload=MetaPayload(**meta_raw),
        tiktok_payload=TikTokPayload(**tiktok_raw),
        campaign_strategy=CampaignStrategy(**strategy),
        source_output_ids=body.output_ids,
    )


@router.get("/matrices", response_model=MatricesResponse)
async def list_testing_matrices(
    pipeline_name: str | None = Query(None),
    job_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> MatricesResponse:
    """Return testing matrices with optional projected metrics.

    Retrieves outputs of type ``testing_matrix`` and enriches each matrix
    entry with projected performance metrics from simulation data when
    available.
    """
    from sqlalchemy import func

    filters = [Output.output_type == "testing_matrix"]
    if pipeline_name is not None:
        filters.append(Output.pipeline_name == pipeline_name)
    if job_id is not None:
        filters.append(Output.job_id == job_id)

    count_result = await session.execute(
        select(func.count(Output.id)).where(*filters)
    )
    total = count_result.scalar_one()

    result = await session.execute(
        select(Output)
        .where(*filters)
        .options(selectinload(Output.performance_metrics))
        .order_by(Output.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    outputs = list(result.scalars().all())

    matrices: list[TestingMatrix] = []
    for output in outputs:
        meta = output.metadata_ or {}
        matrix_data = meta.get("testing_matrix", {})

        # Build a lookup of simulated metrics keyed by test_key
        metric_lookup: dict[str, dict[str, Any]] = {}
        for pm in output.performance_metrics:
            # PerformanceMetric doesn't have test_key — use output-level
            # aggregates as projected estimates for all entries
            metric_lookup["__default__"] = {
                "impressions": pm.impressions,
                "clicks": pm.clicks,
                "ctr": pm.ctr,
                "conversions": pm.conversions,
                "cpa": pm.cpa,
                "roas": pm.roas,
                "simulated_at": pm.simulated_at.isoformat() if pm.simulated_at else None,
            }

        entries: list[MatrixEntry] = []
        for entry in matrix_data.get("entries", []):
            projected = metric_lookup.get("__default__") if metric_lookup else None
            entries.append(
                MatrixEntry(
                    entry_id=entry.get("entry_id", 0),
                    angle=entry.get("angle", ""),
                    variation_index=entry.get("variation_index", 0),
                    copy=entry.get("copy", {}),
                    audience=entry.get("audience", {}),
                    test_key=entry.get("test_key", ""),
                    projected_metrics=projected,
                )
            )

        # Fallback: if metadata is empty, try reading from file
        if not entries and output.file_path:
            try:
                from pathlib import Path

                fp = Path(output.file_path)
                if fp.is_file():
                    file_data = json.loads(fp.read_text())
                    matrix_data = file_data
                    for entry in file_data.get("entries", []):
                        entries.append(
                            MatrixEntry(
                                entry_id=entry.get("entry_id", 0),
                                angle=entry.get("angle", ""),
                                variation_index=entry.get("variation_index", 0),
                                copy=entry.get("copy", {}),
                                audience=entry.get("audience", {}),
                                test_key=entry.get("test_key", ""),
                                projected_metrics=None,
                            )
                        )
            except (json.JSONDecodeError, OSError):
                pass

        dimensions = matrix_data.get("dimensions", {})
        matrices.append(
            TestingMatrix(
                total_combinations=matrix_data.get("total_combinations", len(entries)),
                dimensions=MatrixDimensions(
                    angles=dimensions.get("angles", 0),
                    variations_per_angle=dimensions.get("variations_per_angle", 0),
                    audiences=dimensions.get("audiences", 0),
                ),
                entries=entries,
            )
        )

    return MatricesResponse(
        items=matrices,
        total=total,
        page=page,
        page_size=page_size,
    )
