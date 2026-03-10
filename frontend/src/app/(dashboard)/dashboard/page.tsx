"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Job, PaginatedResponse, PipelineName } from "@/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PIPELINE_LABELS: Record<PipelineName, string> = {
  video_ugc: "Video UGC",
  static_ads: "Static Ads",
  briefs: "Briefs",
  landing_pages: "Landing Pages",
  ad_copy: "Ad Copy",
  feedback_loop: "Feedback Loop",
};

function statusBadge(status: Job["status"]) {
  const config: Record<string, { label: string; color: string }> = {
    completed: { label: "COMPLETED", color: "border-[var(--color-status-completed)] text-[var(--color-status-completed)]" },
    running: { label: "RUNNING", color: "border-[var(--color-status-running)] text-[var(--color-status-running)]" },
    failed: { label: "FAILED", color: "border-[var(--color-status-failed)] text-[var(--color-status-failed)]" },
    pending: { label: "PENDING", color: "border-[var(--color-status-pending)] text-[var(--color-status-pending)]" },
  };
  const { label, color } = config[status] ?? config.pending;
  return <Badge variant="outline" className={color}>{label}</Badge>;
}

function formatDuration(startedAt: string, updatedAt: string): string {
  const start = new Date(startedAt).getTime();
  const end = new Date(updatedAt).getTime();
  const diffMs = end - start;
  if (diffMs < 0) return "\u2014";
  const secs = Math.floor(diffMs / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface DashboardMetrics {
  totalJobs: number;
  outputsGenerated: number;
  activePipelines: number;
  brandsConfigured: number;
}

function computeMetrics(jobs: Job[]): DashboardMetrics {
  const activePipelines = new Set(
    jobs.filter((j) => j.status === "running").map((j) => j.pipeline),
  ).size;

  const outputsGenerated = jobs
    .filter((j) => j.status === "completed")
    .reduce((sum, j) => sum + j.steps.length, 0);

  const brandIds = new Set(jobs.map((j) => j.brand_id));

  return {
    totalJobs: jobs.length,
    outputsGenerated,
    activePipelines,
    brandsConfigured: brandIds.size,
  };
}

export default function DashboardPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    totalJobs: 0,
    outputsGenerated: 0,
    activePipelines: 0,
    brandsConfigured: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.get<PaginatedResponse<Job>>(
        "/api/jobs?page=1&per_page=10",
      );
      setJobs(data.items);
      setMetrics(computeMetrics(data.items));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 15_000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // -------------------------------------------------------------------------
  // Overview cards config
  // -------------------------------------------------------------------------
  const cards = [
    {
      title: "Total Jobs",
      value: metrics.totalJobs,
    },
    {
      title: "Outputs Generated",
      value: metrics.outputsGenerated,
    },
    {
      title: "Active Pipelines",
      value: metrics.activePipelines,
    },
    {
      title: "Brands Configured",
      value: metrics.brandsConfigured,
    },
  ];

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="animate-fade-in space-y-6">
      {/* Page header */}
      <h1 className="text-page-title">DASHBOARD</h1>

      {/* Overview metric cards */}
      <div className="stagger-children grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.title}>
            <CardContent className="p-6">
              <span className="text-label font-mono text-muted-foreground">
                {card.title}
              </span>
              <div className="text-metric mt-1">
                {loading ? "\u2014" : card.value}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* System status */}
      <div className="flex items-center gap-8">
        <StatusDot
          label="API Server"
          status="operational"
        />
        <StatusDot
          label="Pipeline Engine"
          status={
            metrics.activePipelines > 0 ? "operational" : "idle"
          }
        />
        <StatusDot
          label="Job Queue"
          status={
            jobs.some((j) => j.status === "pending") ? "pending" : "operational"
          }
        />
      </div>

      {/* Quick launch */}
      <section>
        <h2 className="text-section-header mb-4 border-b border-border pb-2">QUICK LAUNCH</h2>
        <div className="flex flex-wrap gap-2">
          {(Object.keys(PIPELINE_LABELS) as PipelineName[]).map(
            (pipeline) => (
              <Button key={pipeline} variant="outline" size="sm" asChild>
                <Link href={`/pipelines?launch=${pipeline}`}>
                  {PIPELINE_LABELS[pipeline]}
                </Link>
              </Button>
            ),
          )}
        </div>
      </section>

      {/* Recent pipeline runs */}
      <section>
        <h2 className="text-section-header mb-4 border-b border-border pb-2">RECENT RUNS</h2>

        {error && (
          <p className="mb-4 text-sm text-destructive">{error}</p>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <span className="animate-cursor-blink font-mono">_</span>
          </div>
        ) : jobs.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No pipeline runs yet. Use Quick Launch above to start one.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Pipeline</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead className="text-right">Duration</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">
                    {job.id.slice(0, 8)}
                  </TableCell>
                  <TableCell>{PIPELINE_LABELS[job.pipeline]}</TableCell>
                  <TableCell>{statusBadge(job.status)}</TableCell>
                  <TableCell>{formatTime(job.created_at)}</TableCell>
                  <TableCell className="text-right">
                    {formatDuration(job.created_at, job.updated_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusDot({
  label,
  status,
}: {
  label: string;
  status: "operational" | "idle" | "pending" | "degraded";
}) {
  const colors: Record<typeof status, string> = {
    operational: "bg-status-completed",
    idle: "bg-muted-foreground",
    pending: "bg-status-running",
    degraded: "bg-status-failed",
  };

  const labels: Record<typeof status, string> = {
    operational: "Operational",
    idle: "Idle",
    pending: "Jobs Pending",
    degraded: "Degraded",
  };

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 ${colors[status]}`} />
      <span className="text-label">{label}</span>
      <span className="font-mono text-xs text-muted-foreground">{labels[status]}</span>
    </div>
  );
}
