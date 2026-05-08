/** API client for communicating with the backend. */

import type {
  GenerateResponse,
  StatusResponse,
  CompletedAppSchema,
  CodeGenerationResult,
  ValidationReport,
  PromptResult,
  EvaluationSummary,
} from "@/types/schema";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class APIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new APIError(res.status, body.detail || "Request failed");
  }

  return res.json();
}

/** Start a new app generation job. */
export async function generateApp(
  prompt: string,
  options?: { skip_codegen?: boolean; fast_mode?: boolean },
): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/generate", {
    method: "POST",
    body: JSON.stringify({ prompt, options }),
  });
}

/** Get the current status of a job. */
export async function getJobStatus(jobId: string): Promise<StatusResponse> {
  return request<StatusResponse>(`/api/status/${jobId}`);
}

/** Get the full result of a completed job. */
export async function getJobResult(jobId: string): Promise<{
  job_id: string;
  schema: CompletedAppSchema;
  code_result: CodeGenerationResult | null;
  validation_report: ValidationReport | null;
}> {
  return request(`/api/result/${jobId}`);
}

/** Get the download URL for a generated project ZIP. */
export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/result/${jobId}/download`;
}

/** Start an evaluation run. */
export async function startEvaluation(promptIds?: string[]): Promise<{
  eval_id: string;
  status: string;
  total_prompts: number;
}> {
  return request("/api/evaluate", {
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
  return request(`/api/evaluate/${evalId}/results`);
}

/** Health check. */
export async function checkHealth(): Promise<{
  status: string;
  version: string;
  uptime_seconds: number;
  llm_available: boolean;
}> {
  return request("/api/health");
}

export { APIError };
