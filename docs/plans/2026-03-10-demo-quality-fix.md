# Demo Quality Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all 6 AdForge pipelines work end-to-end with live SSE monitoring and output viewing, creating a polished demo for portfolio clients.

**Architecture:** Fix the frontend-backend contract (field names, SSE format, step names), add Output record creation to all pipelines, enhance the pipeline completion UI with output previews. Backend-first approach — fix the data layer, then the presentation.

**Tech Stack:** FastAPI + Pydantic v2 (backend), Next.js 15 + React 19 (frontend), PostgreSQL LISTEN/NOTIFY (SSE), SQLAlchemy 2.0 (ORM)

---

## Critical Issues Identified

| # | Issue | Impact | Location |
|---|-------|--------|----------|
| 1 | Job response returns `pipeline_name`/`step_name`/`completed_at` but frontend expects `pipeline`/`name`/`updated_at` | Dashboard and pipelines page render empty/broken data | `backend/app/routes/jobs.py:32-66` vs `frontend/src/types/index.ts:73-90` |
| 2 | SSE events send `{job_id, step, status}` but frontend expects `{type, job_id, step, data, timestamp}` | Pipeline live monitoring completely broken | `backend/app/engine/event_bus.py:21-26` vs `frontend/src/types/index.ts:92-98` |
| 3 | EventSource can't send Authorization headers but SSE endpoint requires them | SSE connection fails with 422 (missing header) | `backend/app/routes/jobs.py:152` + `frontend/src/lib/use-sse.ts:34` |
| 4 | Frontend pipeline steps use display labels ("Script Generation") but backend emits technical names ("generate_script") | Step timeline never updates — all steps stay "pending" | `frontend/src/app/(dashboard)/pipelines/page.tsx:42-116` vs pipeline registrations |
| 5 | Most pipelines don't create Output DB records | Gallery empty, output file serving broken | All pipeline final steps except feedback_loop |
| 6 | Backend doesn't emit `step_started` or `job_completed`/`job_failed` events | Frontend can't show running state or detect completion via SSE | `backend/app/engine/job_worker.py:60-94` |
| 7 | No output preview on pipeline completion phase | Demo ends abruptly with just "Run Another" button | `frontend/src/app/(dashboard)/pipelines/page.tsx:619-634` |

---

### Task 1: Fix SSE Auth — Add Token Query Parameter

The EventSource browser API cannot send custom headers. The SSE endpoint must accept auth via query parameter as fallback.

**Files:**
- Modify: `backend/app/routes/jobs.py:151-176`
- Modify: `frontend/src/lib/use-sse.ts:34`
- Modify: `frontend/src/app/(dashboard)/pipelines/page.tsx:228`

**Step 1: Update SSE endpoint to accept token query param**

In `backend/app/routes/jobs.py`, change the SSE endpoint to accept either header or query param:

```python
@router.get("/jobs/{job_id}/events")
async def job_events_sse(
    job_id: uuid.UUID,
    token: str | None = Query(None),
    authorization: str | None = Header(None),
):
    # Extract token from header or query param
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.removeprefix("Bearer ")
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(
            status_code=401,
            detail="Provide Authorization header or token query parameter",
        )

    async with async_session() as session:
        user = await _lookup_user_by_key(session, raw_token)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        query = select(Job).where(Job.id == job_id)
        if not user.is_admin:
            query = query.join(Brand, Job.brand_id == Brand.id).where(Brand.user_id == user.id)
        result = await session.execute(query)
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Job not found")

    dsn = settings.database_url.replace("+asyncpg", "")

    async def event_stream():
        async for event in listen_job_events(dsn):
            if event.get("job_id") == str(job_id):
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Step 2: Update frontend SSE hook to pass token as query param**

In `frontend/src/lib/use-sse.ts`, the URL already comes from the parent component. No change needed in the hook itself.

In `frontend/src/app/(dashboard)/pipelines/page.tsx`, update the URL construction to include the API key:

```typescript
// Add a helper to read the cookie
function getApiKey(): string {
  const match = document.cookie.match(/adforge_api_key=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

// Then in the useSSE call (line ~228):
const {
  events,
  connected,
  error: sseError,
  reset: resetSSE,
} = useSSE({
  url: activeJob
    ? `${API_BASE_URL}/api/jobs/${activeJob.id}/events?token=${encodeURIComponent(getApiKey())}`
    : "",
  enabled: phase === "running" && !!activeJob,
  onEvent: handleJobEvent,
});
```

**Step 3: Run backend tests**

```bash
cd backend && python -m pytest tests/test_jobs.py -v
```

**Step 4: Commit**

```bash
git add backend/app/routes/jobs.py frontend/src/app/\(dashboard\)/pipelines/page.tsx
git commit -m "fix: add token query param to SSE endpoint for EventSource auth"
```

---

### Task 2: Fix SSE Event Format and Add Missing Events

Backend events use `{status: "completed"}` but frontend expects `{type: "step_completed", timestamp: "..."}`. Backend also doesn't emit `step_started`, `job_completed`, or `job_failed` events.

**Files:**
- Modify: `backend/app/engine/event_bus.py:14-30`
- Modify: `backend/app/engine/job_worker.py:28-94`

**Step 1: Update event_bus to accept event_type**

Replace the `notify_step_event` function in `backend/app/engine/event_bus.py`:

```python
async def notify_step_event(
    session: AsyncSession,
    job_id: str,
    event_type: str,
    step: str | None = None,
    output_preview: str | None = None,
) -> None:
    payload = json.dumps({
        "type": event_type,
        "job_id": job_id,
        "step": step,
        "data": {"output_preview": output_preview} if output_preview else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": CHANNEL, "payload": payload},
    )
```

Add the necessary import at the top:

```python
from datetime import datetime, timezone
```

**Step 2: Update job_worker to emit all event types**

In `backend/app/engine/job_worker.py`, update `execute_job`:

```python
async def execute_job(job: Job, steps: list[JobStep], session: AsyncSession) -> None:
    pipeline = get_pipeline(job.pipeline_name)
    if pipeline is None:
        job.status = JobStatus.failed
        await session.commit()
        return

    step_order = {name: i for i, (name, _) in enumerate(pipeline.steps)}
    step_funcs = {name: func for name, func in pipeline.steps}
    sorted_steps = sorted(steps, key=lambda s: step_order.get(s.step_name, 999))

    job.status = JobStatus.running
    job.started_at = datetime.now(timezone.utc)
    await session.commit()

    prev_outputs: dict[str, dict] = {}
    config = job.config or {}

    for step in sorted_steps:
        step_func = step_funcs.get(step.step_name)
        if step_func is None:
            step.status = StepStatus.failed
            step.error = f"No function registered for step '{step.step_name}'"
            step.completed_at = datetime.now(timezone.utc)
            job.status = JobStatus.failed
            job.completed_at = datetime.now(timezone.utc)
            await notify_step_event(session, str(job.id), "step_failed", step.step_name)
            await notify_step_event(session, str(job.id), "job_failed")
            await session.commit()
            return

        step.status = StepStatus.running
        step.started_at = datetime.now(timezone.utc)
        step.input = config
        await session.commit()

        # Emit step_started event
        await notify_step_event(session, str(job.id), "step_started", step.step_name)
        await session.commit()

        try:
            result = await step_func(
                job_id=job.id,
                config=config,
                prev_outputs=prev_outputs,
                session=session,
            )
            step.status = StepStatus.completed
            step.output = result
            step.completed_at = datetime.now(timezone.utc)
            prev_outputs[step.step_name] = result
            output_preview = str(result)[:200] if result else None
            await notify_step_event(
                session, str(job.id), "step_completed", step.step_name, output_preview
            )
            await session.commit()
        except Exception as exc:
            logger.exception("Step %s failed for job %s", step.step_name, job.id)
            step.status = StepStatus.failed
            step.error = str(exc)
            step.completed_at = datetime.now(timezone.utc)
            job.status = JobStatus.failed
            job.completed_at = datetime.now(timezone.utc)
            await notify_step_event(session, str(job.id), "step_failed", step.step_name)
            await notify_step_event(session, str(job.id), "job_failed")
            await session.commit()
            return

    job.status = JobStatus.completed
    job.completed_at = datetime.now(timezone.utc)
    await notify_step_event(session, str(job.id), "job_completed")
    await session.commit()
```

**Step 3: Run tests**

```bash
cd backend && python -m pytest tests/ -v
```

**Step 4: Commit**

```bash
git add backend/app/engine/event_bus.py backend/app/engine/job_worker.py
git commit -m "fix: emit proper SSE event types (step_started, step_completed, job_completed)"
```

---

### Task 3: Fix Backend Response Field Names

Backend Pydantic models return `pipeline_name`, `step_name`, `completed_at` but the frontend expects `pipeline`, `name`, `updated_at`.

**Files:**
- Modify: `backend/app/routes/jobs.py:32-66`

**Step 1: Update response models with field aliases**

Replace the response models in `backend/app/routes/jobs.py`:

```python
from pydantic import BaseModel, Field

class StepResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str = Field(alias="step_name")
    status: str
    input: dict | None = None
    output: dict | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    pipeline: str = Field(alias="pipeline_name")
    brand_id: uuid.UUID
    status: str
    config: dict | None = None
    created_at: datetime
    started_at: datetime | None = None
    updated_at: datetime | None = Field(None, alias="completed_at")


class JobDetailResponse(JobResponse):
    steps: list[StepResponse] = []


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
```

Note: With Pydantic v2 `from_attributes=True`, the `alias` parameter tells Pydantic to read the ORM attribute by alias name. When serializing to JSON, it uses the field name (not the alias) by default. So `pipeline_name` attribute → reads as `pipeline` field → serializes as `"pipeline"` in JSON.

**Step 2: Verify with tests**

```bash
cd backend && python -m pytest tests/test_jobs.py -v
```

Note: Existing tests may assert on `pipeline_name` in responses — update those assertions to expect `pipeline` instead.

**Step 3: Commit**

```bash
git add backend/app/routes/jobs.py
git commit -m "fix: alias job response fields to match frontend contract"
```

---

### Task 4: Align Frontend Pipeline Step Definitions with Backend

The frontend PIPELINES array uses display labels ("Script Generation") as step identifiers, but SSE events use backend step names ("generate_script"). The step count also differs.

**Files:**
- Modify: `frontend/src/app/(dashboard)/pipelines/page.tsx:37-148`

**Step 1: Map actual backend step names**

Backend pipeline registrations (from pipeline files):

| Pipeline | Backend steps (exact `step_name` values) |
|----------|-------|
| `briefs` | `analyze_product`, `generate_brief`, `render_brief` |
| `ad_copy` | `generate_copy_matrix`, `build_testing_matrix`, `generate_deployment_payloads` |
| `static_ads` | `generate_angle_matrix`, `generate_ad_copy`, `generate_base_images`, `compose_final_ads` |
| `video_ugc` | `generate_script`, `generate_voiceover`, `generate_video`, `composite` |
| `landing_pages` | `generate_page_strategy`, `generate_sections`, `generate_variations`, `render_page` |
| `feedback_loop` | `simulate_performance`, `analyze_results`, `generate_insights`, `update_context` |

**Step 2: Update PIPELINES to use key+label pairs**

Replace the PIPELINES definition and update `deriveStepStatuses`:

```typescript
interface PipelineStep {
  key: string;   // backend step_name — matches SSE event.step
  label: string; // human-readable display name
}

const PIPELINES: {
  name: PipelineName;
  label: string;
  description: string;
  steps: PipelineStep[];
}[] = [
  {
    name: "video_ugc",
    label: "Video UGC",
    description:
      "Generate authentic UGC-style video ads with AI avatars and voiceovers",
    steps: [
      { key: "generate_script", label: "Script Generation" },
      { key: "generate_voiceover", label: "Voice Synthesis" },
      { key: "generate_video", label: "Video Rendering" },
      { key: "composite", label: "Compositing" },
    ],
  },
  {
    name: "static_ads",
    label: "Static Ads",
    description:
      "Create high-converting static ad creatives with copy and visuals",
    steps: [
      { key: "generate_angle_matrix", label: "Angle Discovery" },
      { key: "generate_ad_copy", label: "Copy Generation" },
      { key: "generate_base_images", label: "Image Generation" },
      { key: "compose_final_ads", label: "Compositing" },
    ],
  },
  {
    name: "briefs",
    label: "Creative Briefs",
    description: "AI-generated creative briefs and advertising concepts",
    steps: [
      { key: "analyze_product", label: "Product Analysis" },
      { key: "generate_brief", label: "Brief Generation" },
      { key: "render_brief", label: "Brief Rendering" },
    ],
  },
  {
    name: "landing_pages",
    label: "Landing Pages",
    description: "Generate optimized landing pages for ad campaigns",
    steps: [
      { key: "generate_page_strategy", label: "Page Strategy" },
      { key: "generate_sections", label: "Section Content" },
      { key: "generate_variations", label: "A/B Variations" },
      { key: "render_page", label: "HTML Rendering" },
    ],
  },
  {
    name: "ad_copy",
    label: "Ad Copy",
    description:
      "Generate compelling ad copy variations for multiple platforms",
    steps: [
      { key: "generate_copy_matrix", label: "Copy Matrix" },
      { key: "build_testing_matrix", label: "Testing Matrix" },
      { key: "generate_deployment_payloads", label: "Deployment Payloads" },
    ],
  },
  {
    name: "feedback_loop",
    label: "Feedback Loop",
    description:
      "Analyze performance data and generate optimization suggestions",
    steps: [
      { key: "simulate_performance", label: "Performance Simulation" },
      { key: "analyze_results", label: "Results Analysis" },
      { key: "generate_insights", label: "Insight Generation" },
      { key: "update_context", label: "Context Update" },
    ],
  },
];
```

**Step 3: Update deriveStepStatuses to use step keys**

```typescript
function deriveStepStatuses(
  steps: PipelineStep[],
  events: JobEvent[],
): Record<string, JobStatus> {
  const statuses: Record<string, JobStatus> = {};
  for (const step of steps) {
    statuses[step.key] = "pending";
  }
  for (const event of events) {
    if (!event.step) continue;
    if (event.type === "step_started") statuses[event.step] = "running";
    else if (event.type === "step_completed") statuses[event.step] = "completed";
    else if (event.type === "step_failed") statuses[event.step] = "failed";
  }
  return statuses;
}
```

**Step 4: Update all references from `string[]` to `PipelineStep[]`**

Throughout the component, update:
- `pipeline.steps.map((stepName, i) => ...)` → `pipeline.steps.map((step, i) => ...)`
- `stepStatuses[stepName]` → `stepStatuses[step.key]`
- Display text: `{stepName}` → `{step.label}`
- `pipeline.steps.length` stays the same
- `stepNames` parameter in `deriveStepStatuses` → `steps` (already done above)

Key locations to update:

1. **Config phase step preview** (~line 508-518): Change `pipeline.steps.map((step, i) =>` to use `step.label`
2. **Running phase step visualization** (~line 558-615): Change to use `step.key` for status lookup, `step.label` for display
3. **deriveStepStatuses call** (~line 265): Pass `pipeline?.steps ?? []`

**Step 5: Commit**

```bash
git add frontend/src/app/\(dashboard\)/pipelines/page.tsx
git commit -m "fix: align frontend pipeline steps with backend step names"
```

---

### Task 5: Add Output Record Creation to All Pipelines

Most pipelines write files to disk but never create Output records in the database. Without Output records, the gallery page is empty and the file serving endpoint returns 404.

**Files:**
- Modify: `backend/app/pipelines/briefs.py` — `render_brief` step
- Modify: `backend/app/pipelines/ad_copy.py` — `generate_deployment_payloads` step
- Modify: `backend/app/pipelines/static_ads.py` — `compose_final_ads` step
- Modify: `backend/app/pipelines/video_ugc.py` — `composite` step
- Modify: `backend/app/pipelines/landing_pages.py` — `render_page` step

**Pattern:** Each pipeline's final step should create Output record(s):

```python
from app.models.output import Output

output = Output(
    job_id=job_id,
    pipeline_name="<pipeline_name>",
    output_type="<text|image|video|html|json>",
    file_path="<relative_path_to_file>",
    metadata_={...},
)
session.add(output)
await session.flush()
```

**Step 1: Add Output creation to briefs `render_brief`**

After writing the files in `backend/app/pipelines/briefs.py` `render_brief()`, add:

```python
from app.models.output import Output

# After writing brief.json and brief.md files:
# Create Output records for gallery/file serving
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
```

**Step 2: Add Output creation to ad_copy `generate_deployment_payloads`**

In `backend/app/pipelines/ad_copy.py`, at the end of the final step, after writing payload files:

```python
from app.models.output import Output

# Create Output records for each payload file
for label, path in [
    ("meta_payload", meta_path),
    ("tiktok_payload", tiktok_path),
]:
    output = Output(
        job_id=ctx["job_id"],
        pipeline_name="ad_copy",
        output_type="json",
        file_path=path,
        metadata_={"payload_type": label, "total_ads": result.get(f"total_{label.split('_')[0]}_ads", 0)},
    )
    ctx["session"].add(output)
await ctx["session"].flush()
```

Note: ad_copy uses `ctx` dict wrapper. Check the exact variable names (`ctx["job_id"]`, `ctx["session"]`) match the adapter pattern.

**Step 3: Add Output creation to static_ads `compose_final_ads`**

In `backend/app/pipelines/static_ads.py`, at the end of `compose_final_ads()`, after writing manifest:

```python
from app.models.output import Output

# Create an Output record for each final ad image
for ad in ads:
    output = Output(
        job_id=job_id,
        pipeline_name="static_ads",
        output_type="image",
        file_path=ad["path"],
        metadata_={
            "angle": ad.get("angle", ""),
            "dimension": ad.get("dimension", ""),
            "width": ad.get("width"),
            "height": ad.get("height"),
        },
    )
    session.add(output)

# Also create an Output for the manifest
manifest_output = Output(
    job_id=job_id,
    pipeline_name="static_ads",
    output_type="json",
    file_path=manifest_path,
    metadata_={"type": "manifest", "total_ads": len(ads)},
)
session.add(manifest_output)
await session.flush()
```

**Step 4: Add Output creation to video_ugc `composite`**

In `backend/app/pipelines/video_ugc.py`, at the end of `composite()`, after writing manifest:

```python
from app.models.output import Output

for vid in composited_videos:
    output = Output(
        job_id=ctx["job_id"],
        pipeline_name="video_ugc",
        output_type="video",
        file_path=vid["path"],
        metadata_={
            "angle": vid.get("angle", ""),
            "voice": vid.get("voice_label", ""),
            "duration_seconds": vid.get("duration_seconds"),
        },
    )
    ctx["session"].add(output)
await ctx["session"].flush()
```

**Step 5: Add Output creation to landing_pages `render_page`**

In `backend/app/pipelines/landing_pages.py`, at the end of `render_page()`, after writing HTML files:

```python
from app.models.output import Output

for rendered_file in rendered_files:
    output = Output(
        job_id=job_id,
        pipeline_name="landing_pages",
        output_type="html",
        file_path=rendered_file["path"],
        metadata_={
            "variant_id": rendered_file.get("variant_id", "control"),
            "product_name": prev_outputs.get("generate_page_strategy", {}).get("product", {}).get("name", ""),
        },
    )
    session.add(output)
await session.flush()
```

**Step 6: Run tests**

```bash
cd backend && python -m pytest tests/ -v
```

**Step 7: Commit**

```bash
git add backend/app/pipelines/
git commit -m "feat: create Output records in all pipelines for gallery and file serving"
```

---

### Task 6: Add Output Preview to Pipeline Completion Phase

When a pipeline completes, the user currently sees just "Run Another Pipeline" and "Re-run" buttons. Add an output preview section.

**Files:**
- Modify: `frontend/src/app/(dashboard)/pipelines/page.tsx`

**Step 1: Add output fetching on completion**

Add state and fetch logic after the existing state declarations (~line 184-187):

```typescript
const [jobOutputs, setJobOutputs] = useState<Output[]>([]);
const [outputsLoading, setOutputsLoading] = useState(false);
```

Add import for Output type:
```typescript
import type { ..., Output, OutputListResponse } from "@/types";
```

Add a useEffect that fetches outputs when phase becomes "completed":

```typescript
useEffect(() => {
  if (phase !== "completed" || !activeJob) return;
  setOutputsLoading(true);
  api
    .get<OutputListResponse>(
      `/api/outputs?page=1&page_size=50&pipeline_name=${activeJob.pipeline}`
    )
    .then((res) => {
      // Filter to just this job's outputs
      const jobOuts = res.items.filter((o) => o.job_id === activeJob.id);
      setJobOutputs(jobOuts);
    })
    .catch(() => setJobOutputs([]))
    .finally(() => setOutputsLoading(false));
}, [phase, activeJob]);
```

**Step 2: Add output preview rendering**

After the post-completion actions div (~line 619-634), add output preview:

```tsx
{/* Output preview */}
{phase === "completed" && activeJob?.status === "completed" && (
  <div className="mt-6 space-y-4">
    <h2 className="text-section-header">Generated Outputs</h2>
    {outputsLoading ? (
      <div className="flex items-center gap-2 py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Loading outputs...</span>
      </div>
    ) : jobOutputs.length === 0 ? (
      <p className="py-4 text-sm text-muted-foreground">
        No outputs generated. Check the Gallery page for results.
      </p>
    ) : (
      <div className="grid gap-4 sm:grid-cols-2">
        {jobOutputs.map((output) => (
          <div
            key={output.id}
            className="border border-border bg-card p-4 space-y-3"
          >
            <div className="flex items-center justify-between">
              <Badge variant="secondary">
                {output.output_type.toUpperCase()}
              </Badge>
              <button
                type="button"
                className="text-label text-muted-foreground hover:text-foreground"
                onClick={() =>
                  window.open(
                    `${API_BASE_URL}/api/outputs/${output.id}/file?download=true`,
                    "_blank",
                  )
                }
              >
                DOWNLOAD
              </button>
            </div>
            <OutputPreview output={output} />
            {output.metadata && (
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(output.metadata).slice(0, 3).map(([k, v]) => (
                  <span key={k} className="text-xs text-muted-foreground font-mono">
                    {k}: {String(v)}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
)}
```

**Step 3: Create OutputPreview component**

Add a minimal inline preview component above the page export or in the helpers section:

```tsx
function OutputPreview({ output }: { output: Output }) {
  const fileUrl = `${API_BASE_URL}/api/outputs/${output.id}/file`;

  if (output.output_type === "image" && output.file_path) {
    return (
      <img
        src={fileUrl}
        className="max-h-48 w-full object-contain bg-muted/30"
        alt=""
        loading="lazy"
      />
    );
  }

  if (output.output_type === "video" && output.file_path) {
    return (
      <video
        src={fileUrl}
        controls
        className="max-h-48 w-full bg-muted/30"
      />
    );
  }

  if (output.output_type === "html" && output.file_path) {
    return (
      <div className="relative">
        <iframe
          src={fileUrl}
          className="h-48 w-full border"
          sandbox=""
          title="Landing Page Preview"
        />
        <button
          type="button"
          className="absolute bottom-2 right-2 bg-background/80 px-2 py-1 text-xs hover:bg-background"
          onClick={() => window.open(fileUrl, "_blank")}
        >
          Open Full Page
        </button>
      </div>
    );
  }

  // Text, JSON, and other types — show truncated preview
  return (
    <div className="h-24 overflow-hidden bg-muted/30 p-3">
      <p className="font-mono text-xs text-muted-foreground line-clamp-4">
        {output.file_path?.split("/").pop() ?? "output"} — {output.output_type}
      </p>
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/src/app/\(dashboard\)/pipelines/page.tsx
git commit -m "feat: show output preview on pipeline completion"
```

---

### Task 7: Verify & Fix Briefs Pipeline E2E

Run the briefs pipeline and fix any runtime issues.

**Files:**
- Possibly modify: `backend/app/pipelines/briefs.py`

**Step 1: Start services**

```bash
cd /home/rolloniel/projects/personal/side-projects/ad-forge && docker compose up --build -d
```

**Step 2: Test pipeline via API**

```bash
# Get an API key (from CLAUDE.md: adf_dd956bf027aebf0886de5c5253111fbc)

# Get brand ID
curl -s -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  https://api-adforge.kliuiev.com/api/brands | python3 -m json.tool

# Run briefs pipeline (use actual brand_id from above)
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"creative_angles": ["social proof", "luxury"]}}' \
  https://api-adforge.kliuiev.com/api/pipelines/briefs/run | python3 -m json.tool

# Check job status (use job_id from above)
curl -s -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  https://api-adforge.kliuiev.com/api/jobs/<JOB_ID> | python3 -m json.tool

# Check outputs were created
curl -s -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  "https://api-adforge.kliuiev.com/api/outputs?pipeline_name=briefs" | python3 -m json.tool
```

**Step 3: Debug any failures**

Check backend logs:
```bash
source ~/projects/personal/.env
curl -s -H "Authorization: Bearer $COOLIFY_API_TOKEN" \
  https://coolify.kliuiev.com/api/v1/applications/e8cwwkoogo0osss804ks8s8w/logs
```

Common issues to watch for:
- OpenAI API key not set → check env vars in Coolify
- `json_schema` response format errors → fix schema definition
- File path issues → check output directory permissions
- Output model import missing → add `from app.models.output import Output`

**Step 4: Fix and commit any issues found**

---

### Task 8: Verify & Fix Ad Copy Pipeline E2E

Same pattern as Task 7 but for ad_copy.

**Step 1: Run pipeline**

```bash
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"creative_angles": ["social proof", "urgency"], "variation_count": 2}}' \
  https://api-adforge.kliuiev.com/api/pipelines/ad_copy/run | python3 -m json.tool
```

**Step 2: Verify completion and outputs**

Check job status, verify Output records created, check file serving works.

**Step 3: Fix any issues**

Common issues for ad_copy:
- The ctx-dict adapter pattern — ensure `ctx["job_id"]`, `ctx["session"]` work correctly for Output creation
- The `_adapt_ctx` wrapper may need the session passed through
- Config must include `brand_id`, `angles`, `variation_count`

---

### Task 9: Verify & Fix Static Ads Pipeline E2E

**Step 1: Run pipeline**

```bash
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"creative_angles": ["luxury"]}}' \
  https://api-adforge.kliuiev.com/api/pipelines/static_ads/run | python3 -m json.tool
```

**Step 2: Verify**

- Check that FAL.ai image generation works (requires `FAL_KEY` env var)
- Check Pillow compositing produces valid PNGs
- Check Output records created with `output_type="image"`
- Check images are servable via `/api/outputs/{id}/file`

**Step 3: Fix issues**

Common issues:
- Pillow not in Docker image → add to `pyproject.toml` / `requirements.txt`
- FAL API key not set → verify env var
- Image download path issues

---

### Task 10: Verify & Fix Video UGC Pipeline E2E

**Step 1: Run pipeline**

```bash
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"creative_angles": ["social proof"], "video_style": "avatar"}}' \
  https://api-adforge.kliuiev.com/api/pipelines/video_ugc/run | python3 -m json.tool
```

**Step 2: Verify each step**

1. `generate_script` — OpenAI call, writes script files
2. `generate_voiceover` — ElevenLabs TTS, writes MP3 files (needs `ELEVENLABS_API_KEY`)
3. `generate_video` — HeyGen avatar video OR FAL video (needs `HEYGEN_API_KEY` or `FAL_KEY`)
4. `composite` — ffmpeg compositing (needs `ffmpeg` installed in Docker image)

**Step 3: Fix issues**

Common issues:
- ffmpeg not installed in Docker image → add `apt-get install -y ffmpeg` to Dockerfile
- ElevenLabs voice_id not configured → use a default voice or list voices first
- HeyGen avatar_id not configured → use a default avatar or list avatars first
- ctx-dict adapter issues for Output creation

---

### Task 11: Verify & Fix Landing Pages Pipeline E2E

**Step 1: Run pipeline**

```bash
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"creative_angles": ["luxury"]}}' \
  https://api-adforge.kliuiev.com/api/pipelines/landing_pages/run | python3 -m json.tool
```

**Step 2: Verify**

- Check that Jinja2 template renders valid HTML
- Check that Tailwind CDN link is included in output HTML
- Check Output records with `output_type="html"`
- Check HTML file serving with correct MIME type

**Step 3: Fix issues**

Common issues:
- Jinja2 not in dependencies
- Template rendering errors
- FAL image generation for hero image (optional step)

---

### Task 12: Verify & Fix Feedback Loop Pipeline E2E

**Step 1: Run pipeline**

The feedback loop requires existing outputs with performance metrics, or it creates synthetic ones.

```bash
curl -s -X POST \
  -H "Authorization: Bearer adf_dd956bf027aebf0886de5c5253111fbc" \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "<BRAND_ID>", "config": {"output_count": 10}}' \
  https://api-adforge.kliuiev.com/api/pipelines/feedback_loop/run | python3 -m json.tool
```

**Step 2: Verify**

- Check that `simulate_performance` creates Output + PerformanceMetric records
- Check that `analyze_results` computes stats
- Check that `generate_insights` creates Insight records
- Check that `update_context` stores generation context
- Verify Insights appear on the Performance page

**Step 3: Fix issues**

Common issues:
- `numpy` not installed → add to dependencies
- The `source_job_id` or `job_id` config plumbing may need fixing
- Insight model field mapping (frontend expects `pattern`, `metric`, `impact` but backend Insight has `insight_type`, `content`, `confidence`)

---

### Task 13: Frontend E2E Test via Browser

Use Playwright MCP to test the full demo flow.

**Step 1: Navigate to login**

1. Open `https://adforge.kliuiev.com/login`
2. Enter API key: `adf_dd956bf027aebf0886de5c5253111fbc`
3. Click Submit
4. Verify redirect to `/dashboard`

**Step 2: Test pipeline flow**

1. Navigate to `/pipelines`
2. Click "Creative Briefs"
3. Select brand "GlowVita"
4. Select a product and audience
5. Enter creative angles: "social proof, luxury"
6. Click "Launch Pipeline"
7. Verify SSE connection (live indicator appears)
8. Verify steps progress through the timeline
9. Verify completion shows output preview

**Step 3: Check gallery**

1. Navigate to `/gallery`
2. Verify outputs appear
3. Click an output to preview
4. Click download to verify file serving

**Step 4: Fix any issues found**

---

### Task 14: Demo Polish

**Files:**
- Modify: `backend/app/seed/glowvita.py` — ensure idempotent
- Modify: `backend/app/engine/pipeline_engine.py` — fail-fast on missing API keys
- Modify: `frontend/src/app/(dashboard)/pipelines/page.tsx` — retry button

**Step 1: Add API key validation to create_job**

In `backend/app/engine/pipeline_engine.py`, before creating the job, check required API keys:

```python
from app.config import settings

PIPELINE_API_REQUIREMENTS: dict[str, list[str]] = {
    "briefs": ["openai_api_key"],
    "ad_copy": ["openai_api_key"],
    "static_ads": ["openai_api_key", "fal_key"],
    "video_ugc": ["openai_api_key", "elevenlabs_api_key", "heygen_api_key"],
    "landing_pages": ["openai_api_key"],
    "feedback_loop": ["openai_api_key"],
}

def validate_api_keys(pipeline_name: str) -> None:
    required = PIPELINE_API_REQUIREMENTS.get(pipeline_name, [])
    missing = [k for k in required if not getattr(settings, k, "")]
    if missing:
        raise ValueError(
            f"Pipeline '{pipeline_name}' requires API keys: {', '.join(missing)}. "
            "Configure them in environment variables."
        )
```

Call `validate_api_keys(pipeline_name)` at the start of `create_job()`.

**Step 2: Ensure seed is idempotent**

In `backend/app/seed/glowvita.py`, check if GlowVita brand already exists before creating:

```python
# At the start of seed_glowvita():
result = await session.execute(select(Brand).where(Brand.id == BRAND_ID))
if result.scalar_one_or_none():
    return  # Already seeded
```

**Step 3: Commit**

```bash
git add backend/app/engine/pipeline_engine.py backend/app/seed/glowvita.py
git commit -m "feat: fail-fast on missing API keys, ensure idempotent seed"
```

---

## Execution Order & Dependencies

```
Task 1 (SSE auth) ──┐
Task 2 (SSE events) ─┤── Can run in parallel
Task 3 (field names) ─┘
         │
Task 4 (pipeline step alignment) ── depends on Task 2 (event format)
         │
Task 5 (Output records) ── independent of frontend tasks
         │
Task 6 (output preview UI) ── depends on Tasks 3, 4, 5
         │
Tasks 7-12 (E2E verification) ── depends on all above, run sequentially per pipeline
         │
Task 13 (browser E2E) ── depends on all above
         │
Task 14 (polish) ── final
```

Tasks 1, 2, 3 can be done in parallel. Task 5 can also be done in parallel with Tasks 1-4.
