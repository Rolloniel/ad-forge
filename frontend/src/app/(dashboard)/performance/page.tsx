"use client";

import { useEffect, useState, useCallback } from "react";
import {
  BarChart3,
  TrendingUp,
  Eye,
  MousePointerClick,
  Target,
  DollarSign,
  Loader2,
  Lightbulb,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  Trophy,
  PlayCircle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { api } from "@/lib/api";
import type {
  Brand,
  PipelineName,
  PerformanceDashboard,
  Insight,
  SimulateResponse,
} from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PIPELINE_LABELS: Record<PipelineName, string> = {
  video_ugc: "Video UGC",
  static_ads: "Static Ads",
  briefs: "Briefs",
  landing_pages: "Landing Pages",
  ad_copy: "Ad Copy",
  feedback_loop: "Feedback Loop",
};

const DATE_RANGES = [
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function fmtPct(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}

function fmtCurrency(n: number): string {
  return `$${n.toFixed(2)}`;
}

function fmtRoas(n: number): string {
  return `${n.toFixed(2)}x`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PerformancePage() {
  const [dashboard, setDashboard] = useState<PerformanceDashboard | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [brandFilter, setBrandFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<string>("30d");
  const [pipelineFilter, setPipelineFilter] = useState<string>("all");

  // Simulate
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<SimulateResponse | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams({ range: dateRange });
      if (brandFilter !== "all") params.set("brand_id", brandFilter);
      if (pipelineFilter !== "all") params.set("pipeline", pipelineFilter);

      const [metricsData, insightsData, brandsData] = await Promise.all([
        api.get<PerformanceDashboard>(
          `/api/performance/metrics?${params.toString()}`,
        ),
        api.get<Insight[]>(`/api/insights?${params.toString()}`),
        api.get<Brand[]>("/api/brands"),
      ]);

      setDashboard(metricsData);
      setInsights(insightsData);
      setBrands(brandsData);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load performance data",
      );
    } finally {
      setLoading(false);
    }
  }, [brandFilter, dateRange, pipelineFilter]);

  useEffect(() => {
    setLoading(true);
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleSimulate = async () => {
    setSimulating(true);
    setSimResult(null);
    try {
      const params: Record<string, string> = { range: dateRange };
      if (brandFilter !== "all") params.brand_id = brandFilter;
      if (pipelineFilter !== "all") params.pipeline = pipelineFilter;

      const result = await api.post<SimulateResponse>(
        "/api/performance/simulate",
        params,
      );
      setSimResult(result);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Simulation failed",
      );
    } finally {
      setSimulating(false);
    }
  };

  // -------------------------------------------------------------------------
  // KPI cards config
  // -------------------------------------------------------------------------
  const summary = dashboard?.summary;
  const kpiCards = [
    {
      title: "Impressions",
      value: summary ? fmtNum(summary.impressions) : "—",
      icon: Eye,
      description: "Total ad views",
    },
    {
      title: "Clicks",
      value: summary ? fmtNum(summary.clicks) : "—",
      icon: MousePointerClick,
      description: "Total interactions",
    },
    {
      title: "CTR",
      value: summary ? fmtPct(summary.ctr) : "—",
      icon: Target,
      description: "Click-through rate",
    },
    {
      title: "Conversions",
      value: summary ? fmtNum(summary.conversions) : "—",
      icon: TrendingUp,
      description: "Completed actions",
    },
    {
      title: "CPA",
      value: summary ? fmtCurrency(summary.cpa) : "—",
      icon: DollarSign,
      description: "Cost per acquisition",
    },
    {
      title: "ROAS",
      value: summary ? fmtRoas(summary.roas) : "—",
      icon: BarChart3,
      description: "Return on ad spend",
    },
  ];

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header + filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Performance &amp; Insights</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Simulated performance dashboards and optimization insights.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Select value={brandFilter} onValueChange={setBrandFilter}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Brand" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Brands</SelectItem>
              {brands.map((b) => (
                <SelectItem key={b.id} value={b.id}>
                  {b.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Date range" />
            </SelectTrigger>
            <SelectContent>
              {DATE_RANGES.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={pipelineFilter} onValueChange={setPipelineFilter}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Pipeline" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Pipelines</SelectItem>
              {(Object.keys(PIPELINE_LABELS) as PipelineName[]).map((p) => (
                <SelectItem key={p} value={p}>
                  {PIPELINE_LABELS[p]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* KPI metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {kpiCards.map((card) => (
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

      {/* Charts row */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* CTR by Creative Angle - Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                CTR by Creative Angle
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard && dashboard.ctr_by_angle.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={dashboard.ctr_by_angle}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis
                      dataKey="angle"
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                    />
                    <YAxis
                      tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                    />
                    <Tooltip
                      formatter={(value: number) => [
                        `${(value * 100).toFixed(2)}%`,
                        "CTR",
                      ]}
                      contentStyle={{
                        backgroundColor: "var(--color-card)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "0.5rem",
                        fontSize: "0.875rem",
                      }}
                    />
                    <Bar
                      dataKey="ctr"
                      fill="var(--color-primary)"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  No creative angle data available.
                </p>
              )}
            </CardContent>
          </Card>

          {/* ROAS Trend Over Time - Line Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">ROAS Trend Over Time</CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard && dashboard.roas_trend.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={dashboard.roas_trend}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                    />
                    <YAxis
                      tickFormatter={(v: number) => `${v.toFixed(1)}x`}
                      tick={{ fontSize: 12 }}
                      className="fill-muted-foreground"
                    />
                    <Tooltip
                      formatter={(value: number, name: string) => {
                        if (name === "roas") return [`${value.toFixed(2)}x`, "ROAS"];
                        return [`$${value.toFixed(0)}`, name === "spend" ? "Spend" : "Revenue"];
                      }}
                      contentStyle={{
                        backgroundColor: "var(--color-card)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "0.5rem",
                        fontSize: "0.875rem",
                      }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="roas"
                      stroke="var(--color-primary)"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      activeDot={{ r: 5 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="spend"
                      stroke="#ef4444"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="revenue"
                      stroke="#22c55e"
                      strokeWidth={1.5}
                      strokeDasharray="4 4"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-12 text-center text-sm text-muted-foreground">
                  No ROAS trend data available.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Top hooks + Winning vs Losing patterns */}
      {!loading && dashboard && (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Top Performing Hooks */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Trophy className="h-4 w-4" />
                Top Performing Hooks
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard.top_hooks.length > 0 ? (
                <div className="space-y-3">
                  {dashboard.top_hooks.map((hook, idx) => (
                    <div
                      key={hook.hook}
                      className="flex items-center gap-3 rounded-lg border p-3"
                    >
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                        {idx + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {hook.hook}
                        </p>
                        <div className="mt-1 flex gap-3 text-xs text-muted-foreground">
                          <span>CTR: {fmtPct(hook.ctr)}</span>
                          <span>Conv: {fmtNum(hook.conversions)}</span>
                          <span>ROAS: {fmtRoas(hook.roas)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No hook performance data available.
                </p>
              )}
            </CardContent>
          </Card>

          {/* Winning vs Losing Patterns */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Zap className="h-4 w-4" />
                Winning vs Losing Patterns
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dashboard.patterns.length > 0 ? (
                <div className="space-y-3">
                  {dashboard.patterns.map((p) => {
                    const diff = p.value - p.benchmark;
                    const diffPct =
                      p.benchmark !== 0
                        ? ((diff / p.benchmark) * 100).toFixed(1)
                        : "0";
                    return (
                      <div
                        key={p.pattern}
                        className="flex items-center justify-between rounded-lg border p-3"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            {p.winning ? (
                              <Badge className="bg-emerald-600/15 text-emerald-700 border-emerald-600/20 hover:bg-emerald-600/15">
                                <ArrowUpRight className="mr-0.5 h-3 w-3" />
                                Winner
                              </Badge>
                            ) : (
                              <Badge className="bg-red-600/15 text-red-700 border-red-600/20 hover:bg-red-600/15">
                                <ArrowDownRight className="mr-0.5 h-3 w-3" />
                                Loser
                              </Badge>
                            )}
                            <span className="truncate text-sm font-medium">
                              {p.pattern}
                            </span>
                          </div>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {p.metric}: {p.value.toFixed(2)} vs benchmark{" "}
                            {p.benchmark.toFixed(2)}
                          </p>
                        </div>
                        <span
                          className={`text-sm font-semibold ${p.winning ? "text-emerald-600" : "text-red-600"}`}
                        >
                          {p.winning ? "+" : ""}
                          {diffPct}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No pattern comparison data available.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Insights Panel + Simulate */}
      {!loading && (
        <Card>
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4" />
              Accumulated Insights
            </CardTitle>
            <div className="flex items-center gap-2">
              {simResult && (
                <div className="flex items-center gap-3 rounded-md bg-primary/5 px-3 py-1.5 text-xs">
                  <span>
                    Proj. CTR: <strong>{fmtPct(simResult.projected_ctr)}</strong>
                  </span>
                  <span>
                    Proj. ROAS:{" "}
                    <strong>{fmtRoas(simResult.projected_roas)}</strong>
                  </span>
                  <span>
                    Confidence:{" "}
                    <strong>{(simResult.confidence * 100).toFixed(0)}%</strong>
                  </span>
                </div>
              )}
              <Button
                size="sm"
                onClick={handleSimulate}
                disabled={simulating}
              >
                {simulating ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <PlayCircle className="mr-1.5 h-3.5 w-3.5" />
                )}
                Simulate
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {insights.length > 0 ? (
              <div className="space-y-3">
                {insights.map((insight) => (
                  <div
                    key={insight.id}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant="secondary">{insight.metric}</Badge>
                          <span className="text-sm font-medium">
                            {insight.pattern}
                          </span>
                          <ConfidenceBadge confidence={insight.confidence} />
                        </div>
                        <p className="mt-1.5 text-sm text-muted-foreground">
                          {insight.description}
                        </p>
                        {Object.keys(insight.source_metrics).length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-2">
                            {Object.entries(insight.source_metrics).map(
                              ([key, val]) => (
                                <span
                                  key={key}
                                  className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground"
                                >
                                  {key}: {typeof val === "number" ? val.toFixed(2) : val}
                                </span>
                              ),
                            )}
                          </div>
                        )}
                      </div>
                      <span
                        className={`shrink-0 text-sm font-semibold ${insight.impact >= 0 ? "text-emerald-600" : "text-red-600"}`}
                      >
                        {insight.impact >= 0 ? "+" : ""}
                        {(insight.impact * 100).toFixed(1)}% impact
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No insights available yet. Run pipelines to generate data.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const pct = (confidence * 100).toFixed(0);
  let className: string;

  if (confidence >= 0.8) {
    className =
      "bg-emerald-600/15 text-emerald-700 border-emerald-600/20 hover:bg-emerald-600/15";
  } else if (confidence >= 0.5) {
    className =
      "bg-amber-600/15 text-amber-700 border-amber-600/20 hover:bg-amber-600/15";
  } else {
    className =
      "bg-zinc-600/15 text-zinc-600 border-zinc-600/20 hover:bg-zinc-600/15";
  }

  return <Badge className={className}>{pct}% confidence</Badge>;
}
