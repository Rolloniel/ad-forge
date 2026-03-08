"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Activity,
  CheckCircle2,
  Clock,
  ImageIcon,
  Layers,
  Loader2,
  Palette,
  PlayCircle,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { Job, PaginatedResponse, PipelineName } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  switch (status) {
    case "completed":
      return (
        <Badge className="bg-emerald-600/15 text-emerald-700 border-emerald-600/20 hover:bg-emerald-600/15">
          <CheckCircle2 className="mr-1 h-3 w-3" />
          Completed
        </Badge>
      );
    case "running":
      return (
        <Badge className="bg-blue-600/15 text-blue-700 border-blue-600/20 hover:bg-blue-600/15">
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          Running
        </Badge>
      );
    case "failed":
      return (
        <Badge variant="destructive">
          <XCircle className="mr-1 h-3 w-3" />
          Failed
        </Badge>
      );
    case "pending":
    default:
      return (
        <Badge variant="secondary">
          <Clock className="mr-1 h-3 w-3" />
          Pending
        </Badge>
      );
  }
}

function formatDuration(startedAt: string, updatedAt: string): string {
  const start = new Date(startedAt).getTime();
  const end = new Date(updatedAt).getTime();
  const diffMs = end - start;
  if (diffMs < 0) return "—";
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
      icon: Layers,
      description: "Pipeline runs",
    },
    {
      title: "Outputs Generated",
      value: metrics.outputsGenerated,
      icon: ImageIcon,
      description: "Completed steps",
    },
    {
      title: "Active Pipelines",
      value: metrics.activePipelines,
      icon: Activity,
      description: "Currently running",
    },
    {
      title: "Brands Configured",
      value: metrics.brandsConfigured,
      icon: Palette,
      description: "Unique brands",
    },
  ];

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Overview of recent pipeline runs, output counts, and system status.
        </p>
      </div>

      {/* Overview metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <card.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {loading ? "—" : card.value}
              </div>
              <p className="text-xs text-muted-foreground">
                {card.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick-launch pipelines */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quick Launch</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {(Object.keys(PIPELINE_LABELS) as PipelineName[]).map(
              (pipeline) => (
                <Button key={pipeline} variant="outline" size="sm" asChild>
                  <Link href={`/pipelines?launch=${pipeline}`}>
                    <PlayCircle className="mr-1.5 h-3.5 w-3.5" />
                    {PIPELINE_LABELS[pipeline]}
                  </Link>
                </Button>
              ),
            )}
          </div>
        </CardContent>
      </Card>

      {/* System status */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatusIndicator
          label="API Server"
          status="operational"
        />
        <StatusIndicator
          label="Pipeline Engine"
          status={
            metrics.activePipelines > 0 ? "operational" : "idle"
          }
        />
        <StatusIndicator
          label="Job Queue"
          status={
            jobs.some((j) => j.status === "pending") ? "pending" : "operational"
          }
        />
      </div>

      {/* Recent pipeline runs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Pipeline Runs</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="mb-4 text-sm text-destructive">{error}</p>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusIndicator({
  label,
  status,
}: {
  label: string;
  status: "operational" | "idle" | "pending" | "degraded";
}) {
  const colors: Record<typeof status, string> = {
    operational: "bg-emerald-500",
    idle: "bg-zinc-400",
    pending: "bg-amber-500",
    degraded: "bg-red-500",
  };

  const labels: Record<typeof status, string> = {
    operational: "Operational",
    idle: "Idle",
    pending: "Jobs Pending",
    degraded: "Degraded",
  };

  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <span className={`h-2.5 w-2.5 rounded-full ${colors[status]}`} />
        <div>
          <p className="text-sm font-medium">{label}</p>
          <p className="text-xs text-muted-foreground">{labels[status]}</p>
        </div>
      </CardContent>
    </Card>
  );
}
