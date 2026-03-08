// Auth
export interface AuthValidateRequest {
  api_key: string;
}

export interface AuthValidateResponse {
  valid: boolean;
  token?: string;
}

// Brands
export interface Brand {
  id: string;
  name: string;
  description: string;
  products: Product[];
  audiences: Audience[];
  voice: string;
  visual_guidelines: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface Product {
  id: string;
  brand_id: string;
  name: string;
  description: string;
  price: number;
  features: string[];
  offers: string[];
}

export interface Audience {
  id: string;
  brand_id: string;
  name: string;
  description: string;
  demographics: Record<string, string>;
}

// Pipelines & Jobs
export type PipelineName =
  | "video_ugc"
  | "static_ads"
  | "briefs"
  | "landing_pages"
  | "ad_copy"
  | "feedback_loop";

export interface PipelineRunRequest {
  brand_id: string;
  config: Record<string, unknown>;
}

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface Job {
  id: string;
  pipeline: PipelineName;
  brand_id: string;
  status: JobStatus;
  steps: JobStep[];
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface JobStep {
  name: string;
  status: JobStatus;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface JobEvent {
  type: "step_started" | "step_completed" | "step_failed" | "job_completed" | "job_failed";
  job_id: string;
  step?: string;
  data?: Record<string, unknown>;
  timestamp: string;
}

// Outputs
export type OutputType = "image" | "video" | "text" | "html" | "json";

export interface Output {
  id: string;
  job_id: string;
  pipeline: PipelineName;
  type: OutputType;
  filename: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

// Performance
export interface PerformanceMetrics {
  impressions: number;
  clicks: number;
  ctr: number;
  conversions: number;
  cpa: number;
  roas: number;
}

export interface Insight {
  id: string;
  pattern: string;
  metric: string;
  impact: number;
  confidence: number;
  description: string;
  source_metrics: Record<string, number>;
  created_at: string;
}

export interface CreativeAngleMetric {
  angle: string;
  ctr: number;
  impressions: number;
}

export interface RoasTrend {
  date: string;
  roas: number;
  spend: number;
  revenue: number;
}

export interface TopHook {
  hook: string;
  ctr: number;
  conversions: number;
  roas: number;
}

export interface PatternComparison {
  pattern: string;
  winning: boolean;
  metric: string;
  value: number;
  benchmark: number;
}

export interface PerformanceDashboard {
  summary: PerformanceMetrics;
  ctr_by_angle: CreativeAngleMetric[];
  roas_trend: RoasTrend[];
  top_hooks: TopHook[];
  patterns: PatternComparison[];
}

export interface SimulateResponse {
  projected_ctr: number;
  projected_roas: number;
  projected_conversions: number;
  confidence: number;
}

// Deployment
export interface DeploymentPreview {
  platform: "meta" | "tiktok";
  campaign: Record<string, unknown>;
  ad_sets: Record<string, unknown>[];
  ads: Record<string, unknown>[];
}

export interface TestingMatrix {
  id: string;
  angles: string[];
  copy_variants: string[];
  audiences: string[];
  combinations: number;
}

// API
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface ApiError {
  detail: string;
}
