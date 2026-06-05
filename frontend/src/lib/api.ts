/** API client — uses same-origin BFF proxy by default (no API key in browser). */

import type {
  GenerateResponse,
  StatusResponse,
  CompletedAppSchema,
  CodeGenerationResult,
  ValidationReport,
  PromptResult,
  EvaluationSummary,
} from "@/types/schema";

/** Proxy mode: requests go to /api/backend/* (server adds Bearer token). */
const USE_PROXY = process.env.NEXT_PUBLIC_USE_API_PROXY !== "false";

const DIRECT_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

class APIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

function apiUrl(endpoint: string): string {
  if (USE_PROXY) {
    return `/api/backend/${endpoint}`;
  }
  return `${DIRECT_BASE}/api/${endpoint}`;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (!USE_PROXY && API_KEY) {
    headers.Authorization = `Bearer ${API_KEY}`;
  }
  return headers;
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(endpoint), {
    headers: { ...authHeaders(), ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body.detail || body.error || "Request failed";
    throw new APIError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return res.json();
}

/** Start a new app generation job. */
export async function generateApp(
  prompt: string,
  options?: { skip_codegen?: boolean; fast_mode?: boolean },
): Promise<GenerateResponse> {
  return request<GenerateResponse>("generate", {
    method: "POST",
    body: JSON.stringify({ prompt, options }),
  });
}

/** Get the current status of a job. */
export async function getJobStatus(jobId: string): Promise<StatusResponse> {
  return request<StatusResponse>(`status/${jobId}`);
}

/** Get the full result of a completed job. */
export async function getJobResult(jobId: string): Promise<{
  job_id: string;
  schema: CompletedAppSchema;
  code_result: CodeGenerationResult | null;
  validation_report: ValidationReport | null;
  token_usage?: {
    total_input_tokens: number;
    total_output_tokens: number;
    estimated_cost_usd: number;
    total_duration_ms: number;
  };
}> {
  return request(`result/${jobId}`);
}

/** Download generated project ZIP. */
export async function downloadProjectZip(
  jobId: string,
  filename = "generated-app.zip",
): Promise<void> {
  const res = await fetch(apiUrl(`result/${jobId}/download`), {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new APIError(res.status, body.detail || "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** SSE stream URL for a job (same-origin proxy). */
export function getStreamUrl(jobId: string): string {
  return apiUrl(`status/${jobId}/stream`);
}

/** Start an evaluation run. */
export async function startEvaluation(promptIds?: string[]): Promise<{
  eval_id: string;
  status: string;
  total_prompts: number;
}> {
  return request("evaluate", {
    method: "POST",
    body: JSON.stringify({ prompt_ids: promptIds || [] }),
  });
}

/** Get evaluation results. */
export async function getEvaluationResults(evalId: string): Promise<{
  eval_id: string;
  status: string;
  results: PromptResult[];
  summary: EvaluationSummary | null;
}> {
  return request(`evaluate/${evalId}/results`);
}

/** Health check. */
export async function checkHealth(): Promise<{
  status: string;
  version: string;
  uptime_seconds: number;
  llm_available: boolean;
}> {
  return request("health");
}

export { APIError, USE_PROXY };
