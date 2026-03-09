"use client";

import { useState, useEffect, useCallback } from "react";
import {
  ImageIcon,
  Video,
  FileText,
  Globe,
  Code2,
  Download,
  CheckSquare,
  Square,
  Loader2,
  X,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { api, API_BASE_URL } from "@/lib/api";
import type { Output, OutputType, OutputListResponse } from "@/types";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PIPELINE_LABELS: Record<string, string> = {
  video_ugc: "Video UGC",
  static_ads: "Static Ads",
  briefs: "Briefs",
  landing_pages: "Landing Pages",
  ad_copy: "Ad Copy",
  feedback_loop: "Feedback Loop",
};

const OUTPUT_TYPE_CONFIG: Record<
  OutputType,
  { label: string; icon: React.ComponentType<{ className?: string }> }
> = {
  image: { label: "Image", icon: ImageIcon },
  video: { label: "Video", icon: Video },
  text: { label: "Text", icon: FileText },
  html: { label: "HTML", icon: Globe },
  json: { label: "JSON", icon: Code2 },
};

const PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

interface Filters {
  pipeline_name: string;
  output_type: string;
  created_after: string;
  created_before: string;
}

const EMPTY_FILTERS: Filters = {
  pipeline_name: "",
  output_type: "",
  created_after: "",
  created_before: "",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function outputTypeIcon(
  type: string,
): React.ComponentType<{ className?: string }> {
  return (
    OUTPUT_TYPE_CONFIG[type as OutputType]?.icon ?? FileText
  );
}

function outputTypeLabel(type: string): string {
  return OUTPUT_TYPE_CONFIG[type as OutputType]?.label ?? type;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function OutputCard({
  output,
  isSelected,
  onToggleSelect,
  onPreview,
  onDownload,
}: {
  output: Output;
  isSelected: boolean;
  onToggleSelect: () => void;
  onPreview: () => void;
  onDownload: () => void;
}) {
  const TypeIcon = outputTypeIcon(output.output_type);

  return (
    <Card
      className={cn(
        "group relative cursor-pointer overflow-hidden transition-all hover:shadow-md",
        isSelected && "ring-2 ring-primary",
      )}
      onClick={onPreview}
    >
      {/* Selection toggle */}
      <button
        type="button"
        className={cn(
          "absolute left-2 top-2 z-10 rounded-md p-1 transition-opacity",
          "bg-background/80 backdrop-blur-sm",
          isSelected
            ? "opacity-100"
            : "opacity-0 group-hover:opacity-100",
        )}
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelect();
        }}
      >
        {isSelected ? (
          <CheckSquare className="h-4 w-4 text-primary" />
        ) : (
          <Square className="h-4 w-4 text-muted-foreground" />
        )}
      </button>

      {/* Download button */}
      <button
        type="button"
        className="absolute right-2 top-2 z-10 rounded-md bg-background/80 p-1 opacity-0 backdrop-blur-sm transition-opacity group-hover:opacity-100"
        onClick={(e) => {
          e.stopPropagation();
          onDownload();
        }}
      >
        <Download className="h-4 w-4 text-muted-foreground" />
      </button>

      {/* Thumbnail area */}
      <div className="flex h-40 items-center justify-center bg-muted/30">
        {output.output_type === "image" && output.file_path ? (
          <img
            src={`${API_BASE_URL}/api/outputs/${output.id}/file`}
            className="h-full w-full object-cover"
            alt=""
            loading="lazy"
          />
        ) : output.output_type === "video" ? (
          <div className="relative flex items-center justify-center">
            <Video className="h-12 w-12 text-muted-foreground/40" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="rounded-full bg-background/60 p-2">
                <Eye className="h-5 w-5 text-muted-foreground" />
              </div>
            </div>
          </div>
        ) : (
          <TypeIcon className="h-12 w-12 text-muted-foreground/40" />
        )}
      </div>

      {/* Info */}
      <CardContent className="p-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary" className="text-xs">
            {outputTypeLabel(output.output_type)}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {PIPELINE_LABELS[output.pipeline_name] ?? output.pipeline_name}
          </Badge>
        </div>
        <p className="mt-2 truncate text-xs text-muted-foreground">
          {formatDate(output.created_at)}
        </p>
      </CardContent>
    </Card>
  );
}

function TextPreview({ output }: { output: Output }) {
  const [content, setContent] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/outputs/${output.id}/file`)
      .then((r) => r.text())
      .then(setContent)
      .catch(() => setContent("Failed to load content"));
  }, [output.id]);

  if (content === null) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (output.output_type === "json") {
    let formatted = content;
    try {
      formatted = JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      // use raw content
    }
    return (
      <pre className="max-h-[60vh] overflow-auto rounded-lg bg-muted p-4 text-sm">
        {formatted}
      </pre>
    );
  }

  if (output.output_type === "html") {
    return (
      <iframe
        srcDoc={content}
        className="h-[60vh] w-full rounded-lg border"
        sandbox=""
        title="HTML Preview"
      />
    );
  }

  return (
    <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-4 text-sm">
      {content}
    </pre>
  );
}

function PreviewContent({ output }: { output: Output }) {
  if (output.output_type === "image" && output.file_path) {
    return (
      <img
        src={`${API_BASE_URL}/api/outputs/${output.id}/file`}
        className="max-h-[60vh] w-full rounded-lg object-contain"
        alt=""
      />
    );
  }

  if (output.output_type === "video" && output.file_path) {
    return (
      <video
        src={`${API_BASE_URL}/api/outputs/${output.id}/file`}
        controls
        className="max-h-[60vh] w-full rounded-lg"
      />
    );
  }

  if (output.file_path) {
    return <TextPreview output={output} />;
  }

  return (
    <p className="py-8 text-center text-sm text-muted-foreground">
      No file associated with this output.
    </p>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function GalleryPage() {
  const [outputs, setOutputs] = useState<Output[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [previewOutput, setPreviewOutput] = useState<Output | null>(null);

  const fetchOutputs = useCallback(
    async (pageNum: number, append = false) => {
      try {
        if (append) setLoadingMore(true);
        else setLoading(true);

        const params = new URLSearchParams();
        params.set("page", String(pageNum));
        params.set("page_size", String(PAGE_SIZE));
        if (filters.pipeline_name)
          params.set("pipeline_name", filters.pipeline_name);
        if (filters.output_type)
          params.set("output_type", filters.output_type);
        if (filters.created_after)
          params.set("created_after", filters.created_after);
        if (filters.created_before)
          params.set("created_before", filters.created_before);

        const data = await api.get<OutputListResponse>(
          `/api/outputs?${params}`,
        );

        setOutputs((prev) =>
          append ? [...prev, ...data.items] : data.items,
        );
        setTotal(data.total);
        setPage(pageNum);
        setError(null);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load outputs",
        );
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [filters],
  );

  useEffect(() => {
    setSelected(new Set());
    fetchOutputs(1);
  }, [fetchOutputs]);

  // ------- Actions -------

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selected.size === outputs.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(outputs.map((o) => o.id)));
    }
  }

  function downloadOne(id: string) {
    window.open(`${API_BASE_URL}/api/outputs/${id}/file?download=true`, "_blank");
  }

  function downloadBatch() {
    for (const id of selected) {
      downloadOne(id);
    }
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
  }

  const hasMore = outputs.length < total;
  const hasFilters = Object.values(filters).some(Boolean);

  // ------- Render -------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Gallery</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse generated creative assets.
          </p>
        </div>
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selected.size} selected
            </span>
            <Button size="sm" onClick={downloadBatch}>
              <Download className="mr-1.5 h-4 w-4" />
              Download
            </Button>
          </div>
        )}
      </div>

      {/* Filter bar */}
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-4">
          <div className="space-y-1">
            <Label className="text-xs">Pipeline</Label>
            <Select
              value={filters.pipeline_name || "all"}
              onValueChange={(v) =>
                setFilters((f) => ({
                  ...f,
                  pipeline_name: v === "all" ? "" : v,
                }))
              }
            >
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All Pipelines" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Pipelines</SelectItem>
                {Object.entries(PIPELINE_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Output Type</Label>
            <Select
              value={filters.output_type || "all"}
              onValueChange={(v) =>
                setFilters((f) => ({
                  ...f,
                  output_type: v === "all" ? "" : v,
                }))
              }
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {(
                  Object.entries(OUTPUT_TYPE_CONFIG) as [
                    OutputType,
                    (typeof OUTPUT_TYPE_CONFIG)[OutputType],
                  ][]
                ).map(([key, cfg]) => (
                  <SelectItem key={key} value={key}>
                    {cfg.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">From</Label>
            <Input
              type="date"
              className="w-[150px]"
              value={filters.created_after}
              onChange={(e) =>
                setFilters((f) => ({ ...f, created_after: e.target.value }))
              }
            />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">To</Label>
            <Input
              type="date"
              className="w-[150px]"
              value={filters.created_before}
              onChange={(e) =>
                setFilters((f) => ({ ...f, created_before: e.target.value }))
              }
            />
          </div>

          {hasFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearFilters}
              className="mb-0.5"
            >
              <X className="mr-1 h-3 w-3" />
              Clear
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Results count + select all */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {loading
            ? "Loading\u2026"
            : `${total} output${total !== 1 ? "s" : ""}`}
        </p>
        {outputs.length > 0 && (
          <Button variant="ghost" size="sm" onClick={toggleSelectAll}>
            {selected.size === outputs.length ? (
              <CheckSquare className="mr-1.5 h-4 w-4" />
            ) : (
              <Square className="mr-1.5 h-4 w-4" />
            )}
            {selected.size === outputs.length ? "Deselect All" : "Select All"}
          </Button>
        )}
      </div>

      {/* Error */}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {/* Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : outputs.length === 0 ? (
        <div className="py-16 text-center">
          <ImageIcon className="mx-auto h-12 w-12 text-muted-foreground/30" />
          <p className="mt-4 text-sm text-muted-foreground">
            {hasFilters
              ? "No outputs match your filters."
              : "No outputs yet. Run a pipeline to generate creative assets."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {outputs.map((output) => (
            <OutputCard
              key={output.id}
              output={output}
              isSelected={selected.has(output.id)}
              onToggleSelect={() => toggleSelect(output.id)}
              onPreview={() => setPreviewOutput(output)}
              onDownload={() => downloadOne(output.id)}
            />
          ))}
        </div>
      )}

      {/* Load more */}
      {hasMore && !loading && (
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={() => fetchOutputs(page + 1, true)}
            disabled={loadingMore}
          >
            {loadingMore && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Load More
          </Button>
        </div>
      )}

      {/* Preview dialog */}
      <Dialog
        open={!!previewOutput}
        onOpenChange={(open) => {
          if (!open) setPreviewOutput(null);
        }}
      >
        <DialogContent className="max-w-3xl">
          {previewOutput && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {outputTypeLabel(previewOutput.output_type)} Output
                </DialogTitle>
                <DialogDescription>
                  {PIPELINE_LABELS[previewOutput.pipeline_name] ??
                    previewOutput.pipeline_name}{" "}
                  &middot; {formatDate(previewOutput.created_at)}
                </DialogDescription>
              </DialogHeader>

              <PreviewContent output={previewOutput} />

              <Separator />

              {/* Metadata panel */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Details</h3>
                <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Pipeline: </span>
                    {PIPELINE_LABELS[previewOutput.pipeline_name] ??
                      previewOutput.pipeline_name}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Type: </span>
                    {outputTypeLabel(previewOutput.output_type)}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Created: </span>
                    {formatDate(previewOutput.created_at)}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Job: </span>
                    <span className="font-mono text-xs">
                      {previewOutput.job_id.slice(0, 8)}
                    </span>
                  </div>
                  {previewOutput.metadata &&
                    Object.entries(previewOutput.metadata).map(([key, val]) => (
                      <div key={key}>
                        <span className="text-muted-foreground">{key}: </span>
                        {typeof val === "object"
                          ? JSON.stringify(val)
                          : String(val)}
                      </div>
                    ))}
                </div>
              </div>

              {/* Download */}
              {previewOutput.file_path && (
                <div className="flex justify-end">
                  <Button onClick={() => downloadOne(previewOutput.id)}>
                    <Download className="mr-2 h-4 w-4" />
                    Download
                  </Button>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
