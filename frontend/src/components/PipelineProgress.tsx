"use client";

import type { SSEEvent, PipelineStage } from "@/types/schema";

interface RepairEvent {
  layer: string;
  description: string;
}

interface PipelineProgressProps {
  events: SSEEvent[];
  currentStage: PipelineStage | null;
  repairs: RepairEvent[];
  totalCost: number;
}

const STAGES: { key: PipelineStage; label: string; icon: string }[] = [
  { key: "intent", label: "Intent Extraction", icon: "🎯" },
  { key: "design", label: "System Design", icon: "📐" },
  { key: "schemas", label: "Schema Generation", icon: "📋" },
  { key: "validation", label: "Validation & Repair", icon: "🔍" },
  { key: "refinement", label: "Refinement", icon: "✨" },
  { key: "codegen", label: "Code Generation", icon: "⚙️" },
];

function getStageStatus(
  stageKey: PipelineStage,
  events: SSEEvent[],
  currentStage: PipelineStage | null,
): { status: "pending" | "running" | "completed" | "skipped"; durationMs: number } {
  const completeEvent = events.find(
    (e) => e.event === "stage_complete" && e.data.stage === stageKey,
  );

  if (completeEvent) {
    if (completeEvent.data.skipped) {
      return { status: "skipped", durationMs: 0 };
    }
    return { status: "completed", durationMs: completeEvent.data.duration_ms || 0 };
  }

  if (currentStage === stageKey) {
    return { status: "running", durationMs: 0 };
  }

  return { status: "pending", durationMs: 0 };
}

export default function PipelineProgress({
  events,
  currentStage,
  repairs,
  totalCost,
}: PipelineProgressProps) {
  const isDone = events.some((e) => e.event === "done");
  const hasError = events.some((e) => e.event === "error");
  const errorMsg = events.find((e) => e.event === "error")?.data.message;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-surface-300 uppercase tracking-wider">Pipeline</h3>
        {totalCost > 0 && (
          <span className="text-xs text-surface-400 bg-surface-800/50 px-2 py-1 rounded-lg">
            💰 ${totalCost.toFixed(4)}
          </span>
        )}
      </div>

      {STAGES.map((stage) => {
        const { status, durationMs } = getStageStatus(stage.key, events, currentStage);

        return (
          <div
            key={stage.key}
            className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
              status === "running"
                ? "bg-brand-500/10 border border-brand-500/30"
                : status === "completed"
                ? "bg-emerald-500/5 border border-emerald-500/20"
                : status === "skipped"
                ? "bg-surface-800/30 border border-surface-700/20 opacity-50"
                : "bg-surface-800/20 border border-transparent"
            }`}
          >
            {/* Status indicator */}
            <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center">
              {status === "completed" && (
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center">
                  <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              )}
              {status === "running" && (
                <div className="w-6 h-6 rounded-full border-2 border-brand-400 border-t-transparent animate-spin" />
              )}
              {status === "pending" && (
                <div className="w-6 h-6 rounded-full border-2 border-surface-600" />
              )}
              {status === "skipped" && (
                <div className="w-6 h-6 rounded-full bg-surface-700/50 flex items-center justify-center text-xs text-surface-500">—</div>
              )}
            </div>

            {/* Label */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm">{stage.icon}</span>
                <span className={`text-sm font-medium ${
                  status === "completed" ? "text-emerald-400" :
                  status === "running" ? "text-brand-400" :
                  "text-surface-400"
                }`}>
                  {stage.label}
                </span>
              </div>
            </div>

            {/* Duration */}
            {status === "completed" && durationMs > 0 && (
              <span className="text-xs text-surface-500 font-mono">
                {durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`}
              </span>
            )}
            {status === "skipped" && (
              <span className="text-xs text-surface-600">skipped</span>
            )}
          </div>
        );
      })}

      {/* Repair events */}
      {repairs.length > 0 && (
        <div className="mt-3 space-y-1">
          {repairs.map((repair, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-lg animate-fade-in"
            >
              <span className="text-amber-400 text-xs">⚡</span>
              <span className="text-xs text-amber-300/80 truncate">
                Repaired: {repair.description}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Done/Error status */}
      {isDone && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg animate-slide-up">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-emerald-400">Compilation Complete</span>
          </div>
        </div>
      )}

      {hasError && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg animate-slide-up">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm font-medium text-red-400">Pipeline Error</span>
          </div>
          {errorMsg && <p className="text-xs text-red-300/70 mt-1 ml-7">{errorMsg}</p>}
        </div>
      )}
    </div>
  );
}
