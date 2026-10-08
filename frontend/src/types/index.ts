export type ConfidenceLevel = "red" | "yellow" | "green";

export interface BoundingBox {
  0: number; // x0
  1: number; // y0
  2: number; // x1
  3: number; // y1
}

export interface DocumentBlock {
  id: string;
  type:
    | "heading"
    | "paragraph"
    | "list"
    | "table"
    | "figure"
    | "image"
    | "chart"
    | "caption"
    | "equation"
    | "header_footer"
    | "footnote"
    | "form_field"
    | "code";
  reading_order: number;
  page: number;
  bbox: number[];
  content: string;
  confidence: number;
  confidence_level: ConfidenceLevel;
  extractor: string;
  source_reference: string;
  bbox_unit?: string;
  origin?: "top-left";
  spans_pages?: number[];
  routing?: { tried: string; confidence: number }[];
  provenance?: {
    file_sha256: string;
    source_format: string;
    page_type: string;
    timestamp: string;
  };
  flags?: string[];
  metadata?: {
    chart_type?: string;
    series?: any[];
    latex?: string;
    rows?: number;
    columns?: number;
    raw_table?: any[][];
    sheet_name?: string;
  };
}

export interface DocumentPage {
  page_number: number;
  page_type?: string;
  width: number;
  height: number;
  image_data: string;
  blocks: DocumentBlock[];
}

export interface SemanticChunk {
  chunk_id: string;
  text: string;
  page_range: [number, number];
  bounding_boxes: number[][];
  section_path: string;
  block_ids: string[];
  confidence: number;
  token_count?: number;
  score?: number;
}

export interface PipelineStage {
  id: number;
  name: string;
  description?: string;
  status: "pending" | "running" | "done" | "failed";
  summary?: string;
  timing_ms?: number;
}

export interface ValidationCheck {
  name: string;
  passed: boolean;
  message: string;
}

export interface ValidationReport {
  file_id: string;
  is_valid: boolean;
  filename: string;
  file_size: number;
  saved_path?: string;
  checks: ValidationCheck[];
  banner_message: string;
}

export interface JobResult {
  document_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  total_pages: number;
  overall_confidence: number;
  overall_confidence_level: ConfidenceLevel;
  created_at: string;
  processing_time_seconds: number;
  pages: DocumentPage[];
  child_documents?: JobResult[];
  markdown: string;
  ocr_text: string;
  chunks: SemanticChunk[];
  stages: PipelineStage[];
}
