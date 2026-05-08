"use client";

import { useState, useEffect } from "react";
import { startEvaluation, getEvaluationResults } from "@/lib/api";
import type { PromptResult, EvaluationSummary } from "@/types/schema";

export default function EvalDashboard() {
  const [evalId, setEvalId] = useState<string | null>(null);
  const [results, setResults] = useState<PromptResult[]>([]);
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [isRunning, setIsRunning] = useState(false);
  const [filter, setFilter] = useState<"all" | "real" | "edge" | "failed">("all");

  // Poll for results when running
  useEffect(() => {
    if (!evalId || !isRunning) return;

    const interval = setInterval(async () => {
      try {
        const data = await getEvaluationResults(evalId);
        setResults(data.results);
        setSummary(data.summary);
        setStatus(data.status);

        if (data.status === "completed") {
          setIsRunning(false);
        }
      } catch (err) {
        console.error("Failed to fetch eval results:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [evalId, isRunning]);

  const handleRunEval = async () => {
    setIsRunning(true);
    setResults([]);
    setSummary(null);
    try {
      const data = await startEvaluation();
      setEvalId(data.eval_id);
      setStatus("running");
    } catch (err) {
      setIsRunning(false);
      console.error("Failed to start evaluation:", err);
    }
  };

  const filteredResults = results.filter((r) => {
    if (filter === "all") return true;
    if (filter === "failed") return !r.success;
    const promptNum = parseInt(r.prompt_id.replace("prompt_", ""), 10);
    if (filter === "real") return promptNum <= 10;
    if (filter === "edge") return promptNum > 10;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Evaluation Dashboard</h2>
          <p className="text-sm text-surface-400">Run the 20-prompt test suite</p>
        </div>
        <button
          onClick={handleRunEval}
          disabled={isRunning}
          className="px-5 py-2.5 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 disabled:from-surface-700 disabled:to-surface-700 text-white text-sm font-semibold rounded-xl transition-all flex items-center gap-2"
        >
          {isRunning ? (
            <>
              <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Running...
            </>
          ) : (
            "Run Eval Suite"
          )}
        </button>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-surface-800/50 border border-surface-700/30 rounded-xl p-4">
            <div className="text-xs text-surface-500">Success Rate</div>
            <div className={`text-2xl font-bold mt-1 ${summary.success_rate_pct >= 80 ? "text-emerald-400" : summary.success_rate_pct >= 50 ? "text-amber-400" : "text-red-400"}`}>
              {summary.success_rate_pct}%
            </div>
          </div>
          <div className="bg-surface-800/50 border border-surface-700/30 rounded-xl p-4">
            <div className="text-xs text-surface-500">Avg Latency</div>
            <div className="text-2xl font-bold text-white mt-1">{(summary.avg_latency_ms / 1000).toFixed(1)}s</div>
          </div>
          <div className="bg-surface-800/50 border border-surface-700/30 rounded-xl p-4">
            <div className="text-xs text-surface-500">Avg Retries</div>
            <div className="text-2xl font-bold text-white mt-1">{summary.avg_retries.toFixed(1)}</div>
          </div>
          <div className="bg-surface-800/50 border border-surface-700/30 rounded-xl p-4">
            <div className="text-xs text-surface-500">Total Cost</div>
            <div className="text-2xl font-bold text-white mt-1">${summary.total_cost_usd.toFixed(2)}</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2">
        {(["all", "real", "edge", "failed"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              filter === f
                ? "bg-brand-600/20 text-brand-400"
                : "text-surface-400 hover:text-surface-300 bg-surface-800/30"
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f === "all" && results.length > 0 && ` (${results.length})`}
          </button>
        ))}
      </div>

      {/* Results table */}
      {filteredResults.length > 0 && (
        <div className="bg-surface-800/30 border border-surface-700/20 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700/30">
                <th className="text-left px-4 py-3 text-xs text-surface-500 font-medium">Prompt</th>
                <th className="text-center px-4 py-3 text-xs text-surface-500 font-medium">Status</th>
                <th className="text-right px-4 py-3 text-xs text-surface-500 font-medium">Latency</th>
                <th className="text-right px-4 py-3 text-xs text-surface-500 font-medium">Retries</th>
                <th className="text-right px-4 py-3 text-xs text-surface-500 font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {filteredResults.map((r) => (
                <tr key={r.prompt_id} className="border-b border-surface-700/10 hover:bg-surface-800/20">
                  <td className="px-4 py-3">
                    <div className="text-sm text-white font-medium">{r.prompt_id}</div>
                    <div className="text-xs text-surface-500 truncate max-w-xs">{r.prompt_text}</div>
                  </td>
                  <td className="text-center px-4 py-3">
                    {r.success ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400">Pass</span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400">
                        {r.failure_type || "Fail"}
                      </span>
                    )}
                  </td>
                  <td className="text-right px-4 py-3 text-xs font-mono text-surface-400">
                    {(r.total_latency_ms / 1000).toFixed(1)}s
                  </td>
                  <td className="text-right px-4 py-3 text-xs font-mono text-surface-400">
                    {Object.values(r.retry_counts).reduce((a, b) => a + b, 0)}
                  </td>
                  <td className="text-right px-4 py-3 text-xs font-mono text-surface-400">
                    ${r.estimated_cost_usd.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {results.length === 0 && !isRunning && (
        <div className="flex items-center justify-center h-48 text-surface-500">
          <div className="text-center">
            <div className="text-4xl mb-3 opacity-30">📊</div>
            <p className="text-sm">Click &quot;Run Eval Suite&quot; to start</p>
          </div>
        </div>
      )}
    </div>
  );
}
