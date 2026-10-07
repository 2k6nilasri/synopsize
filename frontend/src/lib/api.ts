const API_BASE = "http://127.0.0.1:8000/api";

export async function validateFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/validate`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.banner_message || errorData.detail || "Validation failed");
  }
  return res.json();
}

export async function startParseJob(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/parse`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail?.banner_message || errorData.detail?.message || "Parsing failed to start");
  }
  return res.json();
}

export async function getJobResult(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
  if (!res.ok) {
    throw new Error("Failed to fetch job result");
  }
  return res.json();
}

export function getExportUrl(jobId: string, format: "md" | "json" | "txt" | "zip") {
  return `${API_BASE}/jobs/${jobId}/export?format=${format}`;
}

export async function deleteJobData(jobId: string) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function searchSemanticChunks(jobId: string, query: string) {
  const formData = new FormData();
  formData.append("job_id", jobId);
  formData.append("query", query);
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function saveCorrection(data: {
  original_text: string;
  corrected_text: string;
  page: number;
  extractor: string;
  confidence: number;
  bbox?: number[];
}) {
  const formData = new FormData();
  formData.append("original_text", data.original_text);
  formData.append("corrected_text", data.corrected_text);
  formData.append("page", data.page.toString());
  formData.append("extractor", data.extractor);
  formData.append("confidence", data.confidence.toString());
  formData.append("bbox_json", JSON.stringify(data.bbox || []));
  
  const res = await fetch(`${API_BASE}/corrections`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function applyImageTool(toolName: string, file: File, extraParams: Record<string, any> = {}) {
  const formData = new FormData();
  formData.append("file", file);
  Object.keys(extraParams).forEach((k) => {
    formData.append(k, extraParams[k]);
  });
  
  const res = await fetch(`${API_BASE}/tools/${toolName}`, {
    method: "POST",
    body: formData,
  });
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Tool processing failed");
  }
  
  // Return JSON for JSON endpoints or Blob for Image/ZIP
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  return res.blob();
}
