"use client";

import { useState, useCallback } from "react";
import PromptInput from "@/components/PromptInput";
import PipelineProgress from "@/components/PipelineProgress";
import SchemaViewer from "@/components/SchemaViewer";
import ValidationReportView from "@/components/ValidationReport";
import CodePreview from "@/components/CodePreview";
import EvalDashboard from "@/components/EvalDashboard";
import { generateApp, getJobResult, downloadProjectZip } from "@/lib/api";
import { connectSSE } from "@/lib/sse";
import type {
  SSEEvent,
  CompletedAppSchema,
  CodeGenerationResult,
  ValidationReport,
  PipelineStage,
} from "@/types/schema";

type ViewTab = "schema" | "validation" | "code" | "eval";

export default function HomePage() {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [currentStage, setCurrentStage] = useState<PipelineStage | null>(null);
  const [repairs, setRepairs] = useState<Array<{ layer: string; description: string }>>([]);
  const [totalCost, setTotalCost] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [schema, setSchema] = useState<CompletedAppSchema | null>(null);
  const [codeResult, setCodeResult] = useState<CodeGenerationResult | null>(null);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [viewTab, setViewTab] = useState<ViewTab>("schema");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (prompt: string, options: { fast_mode: boolean; skip_codegen: boolean }) => {
      // Reset state
      setEvents([]);
      setCurrentStage(null);
      setRepairs([]);
      setTotalCost(0);
      setSchema(null);
      setCodeResult(null);
      setValidationReport(null);
      setError(null);
      setIsLoading(true);

      try {
        const response = await generateApp(prompt, options);
        setJobId(response.job_id);

        // Connect SSE
        connectSSE(response.job_id, {
          onEvent: (event) => {
            setEvents((prev) => [...prev, event]);

            if (event.event === "stage_start") {
              setCurrentStage(event.data.stage as PipelineStage);
            }

            if (event.event === "stage_complete") {
              setCurrentStage(null);
            }

            if (event.event === "repair") {
              setRepairs((prev) => [
                ...prev,
                {
                  layer: event.data.layer || "",
                  description: event.data.description || "",
                },
              ]);
            }

            if (event.event === "done") {
              setTotalCost(event.data.total_cost_usd || 0);
              // Fetch full result
              getJobResult(response.job_id)
                .then((result) => {
                  setSchema(result.schema);
                  setCodeResult(result.code_result);
                  setValidationReport(result.validation_report);
                })
                .catch((err) => setError(err.message))
                .finally(() => setIsLoading(false));
            }

            if (event.event === "error") {
              setError(event.data.message || "Pipeline error");
              setIsLoading(false);
            }
          },
          onError: (err) => {
            setError(err.message);
            setIsLoading(false);
          },
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start generation");
        setIsLoading(false);
      }
    },
    [],
  );

  const handleDownloadJson = useCallback(
    (layer: string) => {
      if (!schema) return;
      const data = (schema as unknown as Record<string, unknown>)[layer];
      if (!data) return;
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${schema.meta.app_name}_${layer}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },
    [schema],
  );

  const handleDownloadZip = useCallback(async () => {
    if (!jobId || !schema) return;
    try {
      await downloadProjectZip(jobId, `${schema.meta.app_name}.zip`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    }
  }, [jobId, schema]);

  return (
    <div className="min-h-screen gradient-mesh">
      {/* Header */}
      <header className="border-b border-surface-700/30 glass sticky top-0 z-50">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight">AppCompiler</h1>
              <p className="text-[10px] text-surface-500 uppercase tracking-widest">NL → App Generator</p>
            </div>
          </div>
          <nav className="flex items-center gap-1">
            {(["schema", "validation", "code", "eval"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setViewTab(tab)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  viewTab === tab
                    ? "bg-brand-600/20 text-brand-400"
                    : "text-surface-400 hover:text-surface-300 hover:bg-surface-800/30"
                }`}
              >
                {tab === "schema" && "📋 Schema"}
                {tab === "validation" && "🔍 Validation"}
                {tab === "code" && "💻 Code"}
                {tab === "eval" && "📊 Eval"}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-[1600px] mx-auto px-6 py-8">
        {viewTab === "eval" ? (
          <div className="max-w-5xl mx-auto">
            <EvalDashboard />
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-8">
            {/* Left panel — Input + Progress */}
            <div className="space-y-6">
              <div className="glass rounded-2xl p-6 glow-brand">
                <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-wider mb-4">
                  Describe Your App
                </h2>
                <PromptInput onSubmit={handleSubmit} isLoading={isLoading} />
              </div>

              {(events.length > 0 || isLoading) && (
                <div className="glass rounded-2xl p-6 animate-fade-in">
                  <PipelineProgress
                    events={events}
                    currentStage={currentStage}
                    repairs={repairs}
                    totalCost={totalCost}
                  />
                </div>
              )}

              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl animate-slide-up">
                  <div className="flex items-center gap-2 text-red-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium">Error</span>
                  </div>
                  <p className="text-xs text-red-300/70 mt-1 ml-7">{error}</p>
                </div>
              )}
            </div>

            {/* Right panel — Output */}
            <div className="glass rounded-2xl p-6 min-h-[500px]">
              {viewTab === "schema" && (
                <SchemaViewer
                  schema={schema}
                  onDownloadJson={handleDownloadJson}
                  onDownloadZip={handleDownloadZip}
                />
              )}
              {viewTab === "validation" && (
                <div>
                  <h2 className="text-lg font-bold text-white mb-4">Validation Report</h2>
                  <ValidationReportView report={validationReport} />
                </div>
              )}
              {viewTab === "code" && (
                <div>
                  <h2 className="text-lg font-bold text-white mb-4">Generated Code</h2>
                  <CodePreview codeResult={codeResult} />
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
