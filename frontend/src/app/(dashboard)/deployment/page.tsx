"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Loader2,
  Copy,
  Check,
  Sparkles,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import type { DeploymentPreview, TestingMatrix } from "@/types";

// ---------------------------------------------------------------------------
// Mock campaign data
// ---------------------------------------------------------------------------

const MOCK_PREVIEWS: DeploymentPreview[] = [
  {
    platform: "meta",
    campaign: {
      id: "camp_meta_001",
      name: "Summer Sale 2026 - Conversions",
      objective: "CONVERSIONS",
      status: "PAUSED",
      budget_optimization: "CAMPAIGN_BUDGET_OPTIMIZATION",
      daily_budget: 150.0,
      bid_strategy: "LOWEST_COST_WITH_BID_CAP",
    },
    ad_sets: [
      {
        id: "adset_meta_001",
        name: "Broad - US 25-45 - Interest Stack",
        campaign_id: "camp_meta_001",
        targeting: {
          age_min: 25,
          age_max: 45,
          genders: ["all"],
          geo_locations: { countries: ["US"] },
          interests: [
            { id: "6003139266461", name: "Online shopping" },
            { id: "6003107902433", name: "Fashion" },
          ],
        },
        optimization_goal: "OFFSITE_CONVERSIONS",
        billing_event: "IMPRESSIONS",
        daily_budget: 75.0,
        status: "ACTIVE",
      },
      {
        id: "adset_meta_002",
        name: "Lookalike 1% - Purchasers",
        campaign_id: "camp_meta_001",
        targeting: {
          age_min: 18,
          age_max: 65,
          custom_audiences: [{ id: "lal_001", name: "1% Lookalike - Purchasers 180d" }],
          geo_locations: { countries: ["US"] },
        },
        optimization_goal: "OFFSITE_CONVERSIONS",
        billing_event: "IMPRESSIONS",
        daily_budget: 75.0,
        status: "ACTIVE",
      },
    ],
    ads: [
      {
        id: "ad_meta_001",
        name: "Social Proof - Carousel - V1",
        adset_id: "adset_meta_001",
        creative: {
          type: "CAROUSEL",
          headline: "Join 50,000+ Happy Customers",
          body: "See why people are switching. Limited-time summer pricing.",
          call_to_action: "SHOP_NOW",
          image_count: 5,
        },
        status: "ACTIVE",
      },
      {
        id: "ad_meta_002",
        name: "Urgency - Single Image - V1",
        adset_id: "adset_meta_001",
        creative: {
          type: "SINGLE_IMAGE",
          headline: "Summer Sale Ends Sunday",
          body: "Don't miss 40% off everything. Your cart is waiting.",
          call_to_action: "SHOP_NOW",
        },
        status: "ACTIVE",
      },
      {
        id: "ad_meta_003",
        name: "Social Proof - Video - V1",
        adset_id: "adset_meta_002",
        creative: {
          type: "VIDEO",
          headline: "Real Reviews from Real Customers",
          body: "Hear what our customers have to say.",
          call_to_action: "LEARN_MORE",
          video_duration: 30,
        },
        status: "ACTIVE",
      },
    ],
  },
  {
    platform: "tiktok",
    campaign: {
      id: "camp_tt_001",
      name: "Summer Collection - Traffic",
      objective_type: "TRAFFIC",
      budget_mode: "BUDGET_MODE_DAY",
      budget: 100.0,
      operation_status: "DISABLE",
    },
    ad_sets: [
      {
        id: "adgroup_tt_001",
        name: "US Gen-Z - Interest Targeting",
        campaign_id: "camp_tt_001",
        placement_type: "PLACEMENT_TYPE_AUTOMATIC",
        age_groups: ["AGE_18_24", "AGE_25_34"],
        gender: "GENDER_UNLIMITED",
        location_ids: ["6252001"],
        interest_category_ids: ["20001", "20002"],
        budget: 50.0,
        schedule_type: "SCHEDULE_FROM_NOW",
        optimization_goal: "CLICK",
        bid_type: "BID_TYPE_NO_BID",
      },
      {
        id: "adgroup_tt_002",
        name: "Custom Audience - Site Visitors",
        campaign_id: "camp_tt_001",
        placement_type: "PLACEMENT_TYPE_AUTOMATIC",
        audience_ids: ["aud_tt_retarget_30d"],
        budget: 50.0,
        schedule_type: "SCHEDULE_FROM_NOW",
        optimization_goal: "CLICK",
        bid_type: "BID_TYPE_NO_BID",
      },
    ],
    ads: [
      {
        id: "ad_tt_001",
        name: "UGC Style - Trending Sound",
        adgroup_id: "adgroup_tt_001",
        creative: {
          type: "SINGLE_VIDEO",
          display_name: "Summer Vibes",
          call_to_action: "SHOP_NOW",
          landing_page_url: "https://example.com/summer",
          identity_type: "CUSTOMIZED_USER",
        },
        status: "ENABLE",
      },
      {
        id: "ad_tt_002",
        name: "Product Demo - Before/After",
        adgroup_id: "adgroup_tt_002",
        creative: {
          type: "SINGLE_VIDEO",
          display_name: "See the Difference",
          call_to_action: "LEARN_MORE",
          landing_page_url: "https://example.com/demo",
          identity_type: "CUSTOMIZED_USER",
        },
        status: "ENABLE",
      },
    ],
  },
];

const MOCK_MATRIX: TestingMatrix = {
  id: "matrix_001",
  angles: ["Social Proof", "Urgency / Scarcity", "Lifestyle Aspiration"],
  copy_variants: ["Short & Punchy", "Story-led", "Data-driven"],
  audiences: [
    "Broad Interest - US 25-45",
    "Lookalike 1% - Purchasers",
    "Retarget - Site Visitors 30d",
  ],
  combinations: 27,
};

// Projected metrics per combination (mock)
function projectedMetrics(
  angleIdx: number,
  copyIdx: number,
  audienceIdx: number,
) {
  // Deterministic pseudo-random based on indices
  const seed = (angleIdx * 7 + copyIdx * 13 + audienceIdx * 19) % 100;
  const impressions = 8000 + seed * 120;
  const ctr = 1.2 + (seed % 30) * 0.08;
  const cpa = 12 + (seed % 20) * 0.8;
  const roas = 2.0 + (seed % 25) * 0.12;
  return {
    impressions: Math.round(impressions),
    ctr: Math.round(ctr * 100) / 100,
    cpa: Math.round(cpa * 100) / 100,
    roas: Math.round(roas * 100) / 100,
  };
}

// ---------------------------------------------------------------------------
// JSON syntax highlighting (simple tokenizer)
// ---------------------------------------------------------------------------

function highlightJson(json: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  // Regex to match JSON tokens
  const tokenRe =
    /("(?:[^"\\]|\\.)*")\s*:|("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b|(true|false|null)\b|([{}[\],:])/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = tokenRe.exec(json)) !== null) {
    // Whitespace before token
    if (match.index > lastIndex) {
      nodes.push(json.slice(lastIndex, match.index));
    }

    if (match[1]) {
      // Key
      nodes.push(
        <span key={nodes.length} className="text-foreground">
          {match[1]}
        </span>,
      );
      nodes.push(":");
    } else if (match[2]) {
      // String value
      nodes.push(
        <span key={nodes.length} className="text-muted-foreground">
          {match[2]}
        </span>,
      );
    } else if (match[3]) {
      // Number
      nodes.push(
        <span key={nodes.length} className="text-accent">
          {match[3]}
        </span>,
      );
    } else if (match[4]) {
      // Boolean/null
      nodes.push(
        <span key={nodes.length} className="text-accent">
          {match[4]}
        </span>,
      );
    } else if (match[5]) {
      // Punctuation
      nodes.push(
        <span key={nodes.length} className="text-muted-foreground/50">
          {match[5]}
        </span>,
      );
    }

    lastIndex = match.index + match[0].length;
  }

  // Trailing whitespace
  if (lastIndex < json.length) {
    nodes.push(json.slice(lastIndex));
  }

  return nodes;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PlatformBadge({ platform }: { platform: "meta" | "tiktok" }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        platform === "meta"
          ? "border-blue-600"
          : "border-pink-600",
      )}
    >
      {platform === "meta" ? "Meta Ads" : "TikTok Ads"}
    </Badge>
  );
}

function CampaignTreeNode({
  label,
  type,
  children,
  detail,
}: {
  label: string;
  type: "campaign" | "ad_set" | "ad";
  children?: React.ReactNode;
  detail?: string;
}) {
  const typeLabels = {
    campaign: "Campaign",
    ad_set: "Ad Set",
    ad: "Ad",
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {typeLabels[type]}
        </Badge>
        <span className="text-sm font-medium">{label}</span>
        {detail && (
          <span className="text-xs text-muted-foreground">{detail}</span>
        )}
      </div>
      {children && (
        <div className="ml-4 border-l border-border pl-4">{children}</div>
      )}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [text]);

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy}>
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-500" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
      {copied ? "Copied" : "Copy"}
    </Button>
  );
}

function JsonViewer({ data, title }: { data: unknown; title: string }) {
  const json = JSON.stringify(data, null, 2);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-label">{title}</span>
        <CopyButton text={json} />
      </div>
      <pre className="max-h-80 overflow-auto border border-border bg-[#F7F5F2] p-4 font-mono text-xs leading-relaxed dark:bg-[#1A1816]">
        <code>{highlightJson(json)}</code>
      </pre>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Tab = "campaigns" | "matrix" | "payloads";

export default function DeploymentPage() {
  const [activeTab, setActiveTab] = useState<Tab>("campaigns");
  const [previews, setPreviews] = useState<DeploymentPreview[]>(MOCK_PREVIEWS);
  const [matrix, setMatrix] = useState<TestingMatrix>(MOCK_MATRIX);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPayload, setSelectedPayload] = useState<
    "meta" | "tiktok"
  >("meta");

  // Fetch matrices on mount
  useEffect(() => {
    let cancelled = false;
    api
      .get<{ items: TestingMatrix[]; total: number }>("/api/deployment/matrices")
      .then((data) => {
        if (!cancelled && data.items.length > 0) setMatrix(data.items[0]);
      })
      .catch(() => {
        // Fall back to mock data silently
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function generatePreview() {
    setGenerating(true);
    setError(null);
    try {
      const data = await api.post<DeploymentPreview[]>(
        "/api/deployment/preview",
        { matrix_id: matrix.id },
      );
      setPreviews(data);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Failed to generate preview",
      );
      // Keep existing mock data on error
    } finally {
      setGenerating(false);
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "campaigns", label: "Structure" },
    { key: "matrix", label: "Matrix" },
    { key: "payloads", label: "Payloads" },
  ];

  const selectedPreview = previews.find((p) => p.platform === selectedPayload);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <h1 className="text-page-title">DEPLOYMENT</h1>
        <Button onClick={generatePreview} disabled={generating}>
          {generating ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {generating ? "Generating..." : "Generate Preview"}
        </Button>
      </div>

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {/* Tab navigation */}
      <div className="flex gap-6 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              "pb-2 font-mono text-xs uppercase tracking-wider transition-colors",
              activeTab === tab.key
                ? "border-b-2 border-accent text-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ---- Tab: Campaign Structure ---- */}
      {activeTab === "campaigns" && (
        <div className="grid gap-6 lg:grid-cols-2">
          {previews.map((preview) => (
            <Card key={preview.platform}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <PlatformBadge platform={preview.platform} />
                  <CardTitle className="text-base">
                    {(preview.campaign as Record<string, string>).name}
                  </CardTitle>
                </div>
                <CardDescription>
                  {preview.ad_sets.length} ad set{preview.ad_sets.length !== 1 && "s"},{" "}
                  {preview.ads.length} ad{preview.ads.length !== 1 && "s"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {/* Campaign level */}
                  <CampaignTreeNode
                    label={(preview.campaign as Record<string, string>).name}
                    type="campaign"
                    detail={`Objective: ${(preview.campaign as Record<string, string>).objective || (preview.campaign as Record<string, string>).objective_type}`}
                  >
                    {/* Ad Sets */}
                    <div className="space-y-3 py-2">
                      {preview.ad_sets.map((adSet) => {
                        const adSetId = (adSet as Record<string, string>).id;
                        const adSetName = (adSet as Record<string, string>).name;
                        const adsInSet = preview.ads.filter(
                          (ad) =>
                            (ad as Record<string, string>).adset_id === adSetId ||
                            (ad as Record<string, string>).adgroup_id === adSetId,
                        );
                        return (
                          <CampaignTreeNode
                            key={adSetId}
                            label={adSetName}
                            type="ad_set"
                            detail={`${adsInSet.length} ad${adsInSet.length !== 1 ? "s" : ""}`}
                          >
                            <div className="space-y-2 py-1">
                              {adsInSet.map((ad) => (
                                <CampaignTreeNode
                                  key={(ad as Record<string, string>).id}
                                  label={(ad as Record<string, string>).name}
                                  type="ad"
                                  detail={
                                    ((ad as Record<string, Record<string, string>>).creative)
                                      ?.type
                                  }
                                />
                              ))}
                            </div>
                          </CampaignTreeNode>
                        );
                      })}
                    </div>
                  </CampaignTreeNode>

                  {/* Targeting Summary */}
                  <div className="space-y-3 border-t border-border pt-4">
                    <span className="text-label text-muted-foreground">Targeting</span>
                    {preview.ad_sets.map((adSet) => {
                      const s = adSet as Record<string, unknown>;
                      const name = String(s.name ?? "");
                      const targeting = s.targeting as
                        | Record<string, unknown>
                        | undefined;
                      return (
                        <div key={String(s.id)} className="space-y-1">
                          <p className="text-sm font-medium">{name}</p>
                          {targeting ? (
                            <div className="flex flex-wrap gap-1.5">
                              {targeting.age_min != null && (
                                <Badge variant="secondary">
                                  Ages {String(targeting.age_min)}-{String(targeting.age_max)}
                                </Badge>
                              )}
                              {(targeting.geo_locations as Record<string, string[]> | undefined)
                                ?.countries?.map((c) => (
                                  <Badge key={c} variant="secondary">
                                    {c}
                                  </Badge>
                                ))}
                              {(targeting.interests as { name: string }[] | undefined)?.map(
                                (i) => (
                                  <Badge key={i.name} variant="outline">
                                    {i.name}
                                  </Badge>
                                ),
                              )}
                              {(targeting.custom_audiences as { name: string }[] | undefined)?.map(
                                (a) => (
                                  <Badge key={a.name} variant="outline">
                                    {a.name}
                                  </Badge>
                                ),
                              )}
                            </div>
                          ) : (
                            <div className="flex flex-wrap gap-1.5">
                              {(s.age_groups as string[] | undefined)?.map(
                                (g) => (
                                  <Badge key={g} variant="secondary">
                                    {g.replace("AGE_", "").replace("_", "-")}
                                  </Badge>
                                ),
                              )}
                              {(s.audience_ids as string[] | undefined)?.map(
                                (id) => (
                                  <Badge key={id} variant="outline">
                                    {id}
                                  </Badge>
                                ),
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ---- Tab: Testing Matrix ---- */}
      {activeTab === "matrix" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">Testing Matrix</CardTitle>
                <CardDescription>
                  {matrix.angles.length} angles &times; {matrix.copy_variants.length} copy
                  variants &times; {matrix.audiences.length} audiences ={" "}
                  <strong>{matrix.combinations} combinations</strong>
                </CardDescription>
              </div>
              {loading && (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="min-w-[140px]">Angle</TableHead>
                    <TableHead className="min-w-[120px]">Copy Variant</TableHead>
                    <TableHead className="min-w-[160px]">Audience</TableHead>
                    <TableHead className="text-right">Impressions</TableHead>
                    <TableHead className="text-right">CTR %</TableHead>
                    <TableHead className="text-right">CPA</TableHead>
                    <TableHead className="text-right">ROAS</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {matrix.angles.flatMap((angle, ai) =>
                    matrix.copy_variants.flatMap((copy, ci) =>
                      matrix.audiences.map((audience, aui) => {
                        const m = projectedMetrics(ai, ci, aui);
                        return (
                          <TableRow key={`${ai}-${ci}-${aui}`}>
                            {ci === 0 && aui === 0 && (
                              <TableCell
                                rowSpan={
                                  matrix.copy_variants.length *
                                  matrix.audiences.length
                                }
                                className="align-top font-medium"
                              >
                                {angle}
                              </TableCell>
                            )}
                            {aui === 0 && (
                              <TableCell
                                rowSpan={matrix.audiences.length}
                                className="align-top"
                              >
                                {copy}
                              </TableCell>
                            )}
                            <TableCell>{audience}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {m.impressions.toLocaleString()}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              <span
                                className={cn(
                                  m.ctr >= 2.5
                                    ? "text-emerald-600"
                                    : m.ctr < 1.5
                                      ? "text-red-500"
                                      : "",
                                )}
                              >
                                {m.ctr.toFixed(2)}%
                              </span>
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              ${m.cpa.toFixed(2)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">
                              <span
                                className={cn(
                                  m.roas >= 3.5
                                    ? "text-emerald-600 font-medium"
                                    : m.roas < 2.5
                                      ? "text-red-500"
                                      : "",
                                )}
                              >
                                {m.roas.toFixed(2)}x
                              </span>
                            </TableCell>
                          </TableRow>
                        );
                      }),
                    ),
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- Tab: JSON Payloads ---- */}
      {activeTab === "payloads" && (
        <div className="space-y-4">
          {/* Platform selector */}
          <div className="flex gap-2">
            <Button
              variant={selectedPayload === "meta" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedPayload("meta")}
            >
              Meta Ads
            </Button>
            <Button
              variant={selectedPayload === "tiktok" ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedPayload("tiktok")}
            >
              TikTok Ads
            </Button>
          </div>

          {selectedPreview && (
            <div className="grid gap-6 xl:grid-cols-2">
              <JsonViewer
                data={selectedPreview.campaign}
                title="Campaign Payload"
              />
              <JsonViewer
                data={selectedPreview.ad_sets}
                title={`Ad Sets (${selectedPreview.ad_sets.length})`}
              />
              <JsonViewer
                data={selectedPreview.ads}
                title={`Ads (${selectedPreview.ads.length})`}
              />
              <JsonViewer
                data={{
                  platform: selectedPreview.platform,
                  campaign: selectedPreview.campaign,
                  ad_sets: selectedPreview.ad_sets,
                  ads: selectedPreview.ads,
                }}
                title="Full Deployment Payload"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
