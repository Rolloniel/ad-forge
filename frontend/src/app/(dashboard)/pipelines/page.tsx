"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Video,
  Image,
  FileText,
  Globe,
  Type,
  RefreshCw,
  ArrowLeft,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
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
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
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

const PIPELINES: {
  name: PipelineName;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  steps: string[];
}[] = [
  {
    name: "video_ugc",
    label: "Video UGC",
    icon: Video,
    description:
      "Generate authentic UGC-style video ads with AI avatars and voiceovers",
    steps: [
      "Script Generation",
      "Voice Synthesis",
      "Avatar Rendering",
      "Video Compositing",
      "Quality Check",
    ],
  },
  {
    name: "static_ads",
    label: "Static Ads",
    icon: Image,
    description:
      "Create high-converting static ad creatives with copy and visuals",
    steps: [
      "Copy Generation",
      "Image Generation",
      "Layout Compositing",
      "Variation Matrix",
      "Quality Check",
    ],
  },
  {
    name: "briefs",
    label: "Creative Briefs",
    icon: FileText,
    description: "AI-generated creative briefs and advertising concepts",
    steps: [
      "Market Research",
      "Angle Discovery",
      "Brief Writing",
      "Review & Scoring",
    ],
  },
  {
    name: "landing_pages",
    label: "Landing Pages",
    icon: Globe,
    description: "Generate optimized landing pages for ad campaigns",
    steps: [
      "Copy Generation",
      "Design Generation",
      "HTML Build",
      "Performance Prediction",
    ],
  },
  {
    name: "ad_copy",
    label: "Ad Copy",
    icon: Type,
    description:
      "Generate compelling ad copy variations for multiple platforms",
    steps: [
      "Audience Analysis",
      "Hook Generation",
      "Body Copy",
      "CTA Variations",
      "A/B Scoring",
    ],
  },
  {
    name: "feedback_loop",
    label: "Feedback Loop",
    icon: RefreshCw,
    description:
      "Analyze performance data and generate optimization suggestions",
    steps: [
      "Data Collection",
      "Pattern Analysis",
      "Insight Generation",
      "Optimization Suggestions",
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type Phase = "select" | "configure" | "running" | "completed";

interface PipelineConfig {
  brand_id: string;
  product_ids: string[];
  audience_ids: string[];
  creative_angles: string;
  variation_count: number;
}

function deriveStepStatuses(
  stepNames: string[],
  events: JobEvent[],
): Record<string, JobStatus> {
  const statuses: Record<string, JobStatus> = {};
  for (const name of stepNames) {
    statuses[name] = "pending";
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
    pending: { label: "Pending", cls: "bg-muted text-muted-foreground" },
    running: { label: "Running", cls: "bg-yellow-100 text-yellow-700" },
    completed: { label: "Completed", cls: "bg-green-100 text-green-700" },
    failed: { label: "Failed", cls: "bg-red-100 text-red-700" },
  };
  const v = map[status];
  return (
    <Badge variant="outline" className={cn("text-xs", v.cls)}>
      {v.label}
    </Badge>
  );
}

function StepIcon({ status }: { status: JobStatus }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case "running":
      return <Loader2 className="h-5 w-5 text-yellow-500 animate-spin" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-red-500" />;
    default:
      return <Circle className="h-5 w-5 text-muted-foreground/40" />;
  }
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
    url: activeJob ? `/api/jobs/${activeJob.id}/events` : "",
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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to launch pipeline");
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
          <h1 className="text-2xl font-bold">
            {phase === "select" ? "Pipelines" : (pipeline?.label ?? "Pipeline")}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {phase === "select" &&
              "Select a creative generation pipeline to get started."}
            {phase === "configure" && "Configure your pipeline run."}
            {phase === "running" &&
              "Pipeline is running. Watch progress below."}
            {phase === "completed" && "Pipeline run complete."}
          </p>
        </div>

        {/* ---- Phase: select ---- */}
        {phase === "select" && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINES.map((p) => (
              <Card
                key={p.name}
                className="cursor-pointer transition-colors hover:border-primary/50 hover:shadow-md"
                onClick={() => selectPipeline(p.name)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <p.icon className="h-5 w-5 text-primary" />
                    </div>
                    <CardTitle className="text-base">{p.label}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>{p.description}</CardDescription>
                  <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {p.steps.length} steps
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* ---- Phase: configure ---- */}
        {phase === "configure" && pipeline && (
          <Card>
            <CardContent className="space-y-5 pt-6">
              {/* Brand */}
              <div className="space-y-2">
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
                <div className="space-y-2">
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
                            "rounded-full border px-3 py-1 text-sm transition-colors",
                            on
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-input hover:bg-accent",
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
                <div className="space-y-2">
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
                            "rounded-full border px-3 py-1 text-sm transition-colors",
                            on
                              ? "border-primary bg-primary text-primary-foreground"
                              : "border-input hover:bg-accent",
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
              <div className="space-y-2">
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
              <div className="space-y-2">
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
              <div className="space-y-2">
                <Label className="text-muted-foreground">Pipeline Steps</Label>
                <div className="flex flex-wrap items-center gap-2">
                  {pipeline.steps.map((step, i) => (
                    <span
                      key={step}
                      className="flex items-center gap-1.5 text-sm text-muted-foreground"
                    >
                      {i > 0 && <span className="text-border">&rarr;</span>}
                      {step}
                    </span>
                  ))}
                </div>
              </div>

              <Separator />

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
            </CardContent>
          </Card>
        )}

        {/* ---- Phase: running / completed ---- */}
        {(phase === "running" || phase === "completed") && pipeline && (
          <div className="space-y-4">
            {/* Status bar */}
            <div className="flex items-center gap-3">
              <StatusBadge status={activeJob?.status ?? "running"} />
              {connected && phase === "running" && (
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
                  Live
                </span>
              )}
              {sseError && (
                <span className="text-xs text-destructive">{sseError}</span>
              )}
            </div>

            {/* Step-by-step visualization */}
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-0">
                  {pipeline.steps.map((stepName, i) => {
                    const status = stepStatuses[stepName] ?? "pending";
                    return (
                      <div key={stepName} className="flex items-start gap-4">
                        {/* Timeline */}
                        <div className="flex flex-col items-center">
                          <StepIcon status={status} />
                          {i < pipeline.steps.length - 1 && (
                            <div
                              className={cn(
                                "h-8 w-0.5",
                                status === "completed"
                                  ? "bg-green-500"
                                  : "bg-border",
                              )}
                            />
                          )}
                        </div>
                        {/* Label */}
                        <div className="pb-8">
                          <p
                            className={cn(
                              "text-sm font-medium",
                              status === "running" && "text-yellow-600",
                              status === "completed" && "text-green-600",
                              status === "failed" && "text-destructive",
                              status === "pending" && "text-muted-foreground",
                            )}
                          >
                            {stepName}
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
              </CardContent>
            </Card>

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
        <h2 className="mb-3 text-sm font-semibold">Recent Jobs</h2>
        <div className="space-y-2 overflow-y-auto" style={{ maxHeight: "calc(100vh - 10rem)" }}>
          {jobs.length === 0 && (
            <p className="text-sm text-muted-foreground">No jobs yet.</p>
          )}
          {jobs.map((job) => {
            const pDef = PIPELINES.find((p) => p.name === job.pipeline);
            return (
              <Card
                key={job.id}
                className={cn(
                  "cursor-pointer transition-colors hover:bg-accent/50",
                  activeJob?.id === job.id && "border-primary",
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
                <CardContent className="p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {pDef?.label ?? job.pipeline}
                    </span>
                    <StatusBadge status={job.status} />
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {new Date(job.created_at).toLocaleString()}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </aside>
    </div>
  );
}
