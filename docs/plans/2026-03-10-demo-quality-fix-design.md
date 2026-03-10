# AdForge Demo Quality Fix — Design Document

Date: 2026-03-10

## Goal

Make AdForge a functional, impressive demo for portfolio clients. The demo flow: login → pick brand → run pipeline → watch steps execute live → view generated output. All 6 pipelines functional. Briefs and ad_copy production-quality, remaining 4 functional.

## Section 1: Foundation Fixes

### 1a. Backend Response Serialization

Add Pydantic response schemas that alias ORM field names to match frontend expectations:

- `pipeline_name` → `pipeline`
- `step_name` → `name`
- `completed_at` → `updated_at`

All route handlers return response models instead of raw ORM objects.

### 1b. Frontend Type Alignment

Update `frontend/src/types/index.ts` to match response schemas. Verify every page consuming job/step data renders correctly.

### 1c. SSE Event Format

Verify event bus emits events matching what `use-sse.ts` expects. Fix field name mismatches in event payloads.

### 1d. Output File Serving

Verify `/api/outputs/{id}/file` reliably serves generated files. Confirm output directory consistency between worker and API.

## Section 2: Pipeline Completion

### 2a. Briefs (polish)

Steps: `analyze_product` → `generate_brief` → `render_brief`

Already implemented. Verify end-to-end, ensure Output DB records created, polish prompts.

Output: `brief.json` + `brief.md` in `outputs/{job_id}/briefs/`

### 2b. Ad Copy (polish)

Steps: `generate_copy_matrix` → `build_testing_matrix` → `generate_deployment_payloads`

Already implemented. Verify end-to-end, ensure chaining works, polish prompts.

Output: `copy_matrix.json`, `testing_matrix.json`, `meta_payload.json`, `tiktok_payload.json`

### 2c. Static Ads (implement)

Steps:
1. `generate_creative_concepts` — OpenAI generates visual concepts per angle
2. `generate_images` — FAL Flux Pro, 3 formats: 1080×1080, 1080×1920, 1200×628
3. `assemble_ad_variants` — Save images, create Output records with manifest

Output: Images + `manifest.json` in `outputs/{job_id}/static_ads/`

### 2d. Video UGC (implement)

Steps:
1. `generate_script` — OpenAI writes UGC scripts per angle
2. `generate_voiceover` — ElevenLabs TTS
3. `generate_avatar_video` — HeyGen talking-head video
4. `composite_final` — Save final assets (no ffmpeg, HeyGen output is complete)

Output: Audio + video files + `manifest.json` in `outputs/{job_id}/video_ugc/`

### 2e. Landing Pages (implement)

Steps:
1. `generate_page_strategy` — OpenAI outputs page structure per angle
2. `generate_page_html` — Self-contained HTML with inline Tailwind CSS (CDN)
3. `save_pages` — Write HTML files, create Output records

Output: HTML files in `outputs/{job_id}/landing_pages/`

### 2f. Feedback Loop (implement)

Steps:
1. `collect_metrics` — Query PerformanceMetric for brand's recent outputs
2. `analyze_performance` — OpenAI analyzes what worked and why
3. `generate_insights` — Save Insight records to DB, write JSON

Output: `insights.json` + Insight DB records linked to brand

## Section 3: Output Viewing System

### Preview Components

| Pipeline | Preview | Download |
|----------|---------|----------|
| Briefs | Rendered markdown | JSON + MD |
| Ad Copy | Cards grid by angle | JSON |
| Static Ads | Image grid with format labels, lightbox | Images |
| Video UGC | HTML5 video player + script text | Video + audio |
| Landing Pages | Sandboxed iframe + "Open in new tab" | HTML |
| Feedback Loop | Insight cards with confidence badges | JSON |

### Job Detail Flow

Pipeline page: configure → run → watch (SSE) → view results. After completion, transition to output preview.

### Download

Per-output download via `GET /api/outputs/{id}/file`. Multiple files get individual download links.

## Section 4: Demo Flow Polish

### 4a. Seed Data

`python -m app.seed` creates demo user + API key, GlowVita brand, 3 products, 2 audiences. Idempotent.

### 4b. Error Handling

Failed steps show in red with error message. Previous steps stay green. Retry button re-queues from failed step.

### 4c. API Key Validation

Fail fast at job creation if required API keys are missing. Clear error messages.

### 4d. Performance Simulation

`/api/performance/simulate` generates realistic fake metrics (CTR 0.5-4%, ROAS 1.5-6x). Feeds the feedback loop.
