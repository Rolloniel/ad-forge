"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Play,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { api, API_BASE_URL } from "@/lib/api";
import { useSSE } from "@/lib/use-sse";
import type {
  PipelineName,
  Job,
  JobEvent,
  JobStatus,
  Brand,
} from "@/types";

// ---------------------------------------------------------------------------
// Pipeline definitions
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiKey(): string {
  const match = document.cookie.match(/adforge_api_key=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

type Phase = "select" | "configure" | "running" | "completed";

interface PipelineConfig {
  brand_id: string;
  product_ids: string[];
  audience_ids: string[];
  creative_angles: string;
  variation_count: number;
}

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
    else if (event.type === "step_completed")
      statuses[event.step] = "completed";
    else if (event.type === "step_failed") statuses[event.step] = "failed";
  }
  return statuses;
}

function StatusBadge({ status }: { status: JobStatus }) {
  const map: Record<JobStatus, { label: string; cls: string }> = {
    pending: { label: "PENDING", cls: "border-[var(--color-status-pending)] text-[var(--color-status-pending)]" },
    running: { label: "RUNNING", cls: "border-[var(--color-status-running)] text-[var(--color-status-running)]" },
    completed: { label: "COMPLETED", cls: "border-[var(--color-status-completed)] text-[var(--color-status-completed)]" },
    failed: { label: "FAILED", cls: "border-[var(--color-status-failed)] text-[var(--color-status-failed)]" },
  };
  const v = map[status];
  return (
    <Badge variant="outline" className={v.cls}>
      {v.label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function PipelinesPage() {
  const [phase, setPhase] = useState<Phase>("select");
  const [selectedPipeline, setSelectedPipeline] =
    useState<PipelineName | null>(null);

  const [config, setConfig] = useState<PipelineConfig>({
    brand_id: "",
    product_ids: [],
    audience_ids: [],
    creative_angles: "",
    variation_count: 3,
  });

  const searchParams = useSearchParams();
  const [brands, setBrands] = useState<Brand[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // SSE handler — stable via useCallback so useSSE ref always has latest
  const handleJobEvent = useCallback(
    (event: JobEvent) => {
      if (event.type === "job_completed" || event.type === "job_failed") {
        setPhase("completed");
        if (event.type === "job_completed") {
          toast.success("Pipeline completed", {
            description: "All steps finished successfully.",
          });
        } else {
          toast.error("Pipeline failed", {
            description: "One or more steps encountered an error.",
          });
        }
        setActiveJob((prev) =>
          prev
            ? {
                ...prev,
                status:
                  event.type === "job_completed" ? "completed" : "failed",
              }
            : null,
        );
        // Refresh job list
        api
          .get<{ items: Job[] }>("/api/jobs?per_page=20")
          .then((res) => setJobs(res.items))
          .catch(() => {});
      }
    },
    [],
  );

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

  // Load brands on mount
  useEffect(() => {
    api
      .get<Brand[]>("/api/brands")
      .then(setBrands)
      .catch(() => {});
  }, []);

  // Load recent jobs on mount
  useEffect(() => {
    api
      .get<{ items: Job[] }>("/api/jobs?per_page=20")
      .then((res) => setJobs(res.items))
      .catch(() => {});
  }, []);

  // Auto-select pipeline from ?launch= query param
  useEffect(() => {
    const launch = searchParams.get("launch");
    if (launch && PIPELINES.some((p) => p.name === launch)) {
      setSelectedPipeline(launch as PipelineName);
      setPhase("configure");
      setError(null);
    }
  }, [searchParams]);

  const pipeline = selectedPipeline
    ? PIPELINES.find((p) => p.name === selectedPipeline) ?? null
    : null;

  const selectedBrand = brands.find((b) => b.id === config.brand_id);

  const stepStatuses = deriveStepStatuses(
    pipeline?.steps ?? [],
    events,
  );

  // ------- actions -------

  function selectPipeline(name: PipelineName) {
    setSelectedPipeline(name);
    setPhase("configure");
    setError(null);
  }

  function goBack() {
    setPhase("select");
    setSelectedPipeline(null);
    setActiveJob(null);
    resetSSE();
    setError(null);
  }

  async function launchPipeline() {
    if (!selectedPipeline || !config.brand_id) return;
    setLaunching(true);
    setError(null);
    try {
      const job = await api.post<Job>(
        `/api/pipelines/${selectedPipeline}/run`,
        {
          brand_id: config.brand_id,
          config: {
            product_ids: config.product_ids,
            audience_ids: config.audience_ids,
            creative_angles: config.creative_angles
              .split(",")
              .map((a) => a.trim())
              .filter(Boolean),
            variation_count: config.variation_count,
          },
        },
      );
      setActiveJob(job);
      setPhase("running");
      resetSSE();
      toast.success("Pipeline launched", {
        description: `${pipeline?.label ?? selectedPipeline} is now running.`,
      });
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to launch pipeline";
      setError(message);
      toast.error("Launch failed", { description: message });
    } finally {
      setLaunching(false);
    }
  }

  // ------- render -------

  return (
    <div className="flex h-full gap-6">
      {/* Main content area */}
      <div className="min-w-0 flex-1">
        {/* Header */}
        <div className="mb-6">
          {phase !== "select" && (
            <Button
              variant="ghost"
              size="sm"
              onClick={goBack}
              className="-ml-2 mb-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Pipelines
            </Button>
          )}
          <h1 className="text-page-title">
            {phase === "select" ? "PIPELINES" : (pipeline?.label ?? "Pipeline").toUpperCase()}
          </h1>
        </div>

        {/* ---- Phase: select ---- */}
        {phase === "select" && (
          <div className="stagger-children grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINES.map((p) => (
              <div
                key={p.name}
                className="brutalist-hover cursor-pointer border border-border bg-card p-5"
                onClick={() => selectPipeline(p.name)}
              >
                <h3 className="text-section-header">{p.label}</h3>
                <p className="mt-2 font-mono text-sm text-muted-foreground">
                  {p.description}
                </p>
                <p className="text-label text-muted-foreground mt-3">
                  {p.steps.length} STEPS
                </p>
              </div>
            ))}
          </div>
        )}

        {/* ---- Phase: configure ---- */}
        {phase === "configure" && pipeline && (
          <div className="space-y-5">
            {/* Brand */}
            <div className="space-y-2 border-b border-border pb-5">
              <Label>Brand</Label>
              <Select
                value={config.brand_id}
                onValueChange={(v) =>
                  setConfig((c) => ({
                    ...c,
                    brand_id: v,
                    product_ids: [],
                    audience_ids: [],
                  }))
                }
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a brand" />
                </SelectTrigger>
                <SelectContent>
                  {brands.map((b) => (
                    <SelectItem key={b.id} value={b.id}>
                      {b.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Products (toggle chips) */}
            {selectedBrand && selectedBrand.products.length > 0 && (
              <div className="space-y-2 border-b border-border pb-5">
                <Label>Products</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedBrand.products.map((p) => {
                    const on = config.product_ids.includes(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() =>
                          setConfig((c) => ({
                            ...c,
                            product_ids: on
                              ? c.product_ids.filter((id) => id !== p.id)
                              : [...c.product_ids, p.id],
                          }))
                        }
                        className={cn(
                          "border px-3 py-1 text-sm transition-colors",
                          on
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-input hover:bg-accent hover:text-accent-foreground",
                        )}
                      >
                        {p.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Audiences (toggle chips) */}
            {selectedBrand && selectedBrand.audiences.length > 0 && (
              <div className="space-y-2 border-b border-border pb-5">
                <Label>Audiences</Label>
                <div className="flex flex-wrap gap-2">
                  {selectedBrand.audiences.map((a) => {
                    const on = config.audience_ids.includes(a.id);
                    return (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() =>
                          setConfig((c) => ({
                            ...c,
                            audience_ids: on
                              ? c.audience_ids.filter((id) => id !== a.id)
                              : [...c.audience_ids, a.id],
                          }))
                        }
                        className={cn(
                          "border px-3 py-1 text-sm transition-colors",
                          on
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-input hover:bg-accent hover:text-accent-foreground",
                        )}
                      >
                        {a.name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Creative angles */}
            <div className="space-y-2 border-b border-border pb-5">
              <Label>Creative Angles</Label>
              <Input
                placeholder="e.g. social proof, urgency, luxury lifestyle (comma-separated)"
                value={config.creative_angles}
                onChange={(e) =>
                  setConfig((c) => ({
                    ...c,
                    creative_angles: e.target.value,
                  }))
                }
              />
            </div>

            {/* Variation count */}
            <div className="space-y-2 border-b border-border pb-5">
              <Label>Variations</Label>
              <div className="flex items-center gap-3">
                <Input
                  type="number"
                  min={1}
                  max={20}
                  className="w-24"
                  value={config.variation_count}
                  onChange={(e) =>
                    setConfig((c) => ({
                      ...c,
                      variation_count: Math.max(
                        1,
                        Math.min(20, Number(e.target.value) || 1),
                      ),
                    }))
                  }
                />
                <span className="text-sm text-muted-foreground">
                  variations per angle
                </span>
              </div>
            </div>

            {/* Pipeline steps preview */}
            <div className="space-y-2 border-b border-border pb-5">
              <span className="text-label text-muted-foreground">Pipeline Steps</span>
              <div className="flex flex-wrap items-center gap-2">
                {pipeline.steps.map((step, i) => (
                  <span
                    key={step.key}
                    className="text-label flex items-center gap-1.5 text-muted-foreground"
                  >
                    {i > 0 && <span className="text-border">&rarr;</span>}
                    {step.label}
                  </span>
                ))}
              </div>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button
              size="lg"
              disabled={!config.brand_id || launching}
              onClick={launchPipeline}
            >
              {launching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {launching ? "Launching\u2026" : "Launch Pipeline"}
            </Button>
          </div>
        )}

        {/* ---- Phase: running / completed ---- */}
        {(phase === "running" || phase === "completed") && pipeline && (
          <div className="space-y-4">
            {/* Status bar */}
            <div className="flex items-center gap-3">
              <StatusBadge status={activeJob?.status ?? "running"} />
              {connected && phase === "running" && (
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="h-1.5 w-1.5 animate-pulse bg-status-running" />
                  Live
                </span>
              )}
              {sseError && (
                <span className="text-xs text-destructive">{sseError}</span>
              )}
            </div>

            {/* Step-by-step visualization */}
            <div className="border border-border bg-card p-6">
              <div className="space-y-0">
                {pipeline.steps.map((step, i) => {
                  const status = stepStatuses[step.key] ?? "pending";
                  return (
                    <div key={step.key} className="flex items-start gap-4">
                      {/* Timeline connector */}
                      <div className="flex flex-col items-center">
                        <div
                          className={cn(
                            "mt-1 h-2 w-2",
                            status === "completed" && "bg-status-completed",
                            status === "running" && "bg-status-running",
                            status === "failed" && "bg-status-failed",
                            status === "pending" && "bg-muted-foreground/40",
                          )}
                        />
                        {i < pipeline.steps.length - 1 && (
                          <div
                            className={cn(
                              "h-8 w-0 border-l",
                              status === "completed"
                                ? "border-status-completed"
                                : "border-border",
                            )}
                          />
                        )}
                      </div>
                      {/* Label */}
                      <div
                        className={cn(
                          "pb-5",
                          status === "running" && "animate-pulse-border border-l-2 pl-3",
                        )}
                      >
                        <p
                          className={cn(
                            "font-mono text-sm font-medium",
                            status === "completed" && "text-muted-foreground line-through",
                            status === "running" && "text-foreground",
                            status === "failed" && "text-destructive",
                            status === "pending" && "text-muted-foreground/40",
                          )}
                        >
                          {step.label}
                        </p>
                        {status === "running" && (
                          <p className="mt-0.5 text-xs text-muted-foreground">
                            Processing&hellip;
                          </p>
                        )}
                        {status === "failed" && (
                          <p className="mt-0.5 text-xs text-destructive">
                            Step failed
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Post-completion actions */}
            {phase === "completed" && (
              <div className="flex gap-3">
                <Button onClick={goBack}>Run Another Pipeline</Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setPhase("configure");
                    setActiveJob(null);
                    resetSSE();
                  }}
                >
                  Re-run with Same Config
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ------- Job history sidebar ------- */}
      <aside className="hidden w-72 shrink-0 lg:block">
        <h2 className="text-label mb-3">Recent Jobs</h2>
        <div className="space-y-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 10rem)" }}>
          {jobs.length === 0 && (
            <p className="text-sm text-muted-foreground">No jobs yet.</p>
          )}
          {jobs.map((job) => {
            const pDef = PIPELINES.find((p) => p.name === job.pipeline);
            const isActive = activeJob?.id === job.id;
            return (
              <div
                key={job.id}
                className={cn(
                  "brutalist-hover cursor-pointer border border-border bg-card p-3",
                  isActive && "border-l-2 border-l-accent",
                )}
                onClick={() => {
                  setSelectedPipeline(job.pipeline);
                  setActiveJob(job);
                  setPhase(
                    job.status === "running" || job.status === "pending"
                      ? "running"
                      : "completed",
                  );
                  resetSSE();
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {pDef?.label ?? job.pipeline}
                  </span>
                  <StatusBadge status={job.status} />
                </div>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {new Date(job.created_at).toLocaleString()}
                </p>
              </div>
            );
          })}
        </div>
      </aside>
    </div>
  );
}
