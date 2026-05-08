"use client";

import type { ValidationReport } from "@/types/schema";

interface ValidationReportProps {
  report: ValidationReport | null;
}

export default function ValidationReportView({ report }: ValidationReportProps) {
  if (!report) return null;

  const hasIssues = report.total_errors > 0;
  if (!hasIssues) {
    return (
      <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-emerald-400">All validations passed</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-red-400">{report.total_errors}</div>
          <div className="text-xs text-red-300/70">Errors Found</div>
        </div>
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
          <div className="text-2xl font-bold text-amber-400">{report.total_repaired}</div>
          <div className="text-xs text-amber-300/70">Repaired</div>
        </div>
        <div className={`${report.total_unresolved > 0 ? "bg-red-500/10 border-red-500/20" : "bg-emerald-500/10 border-emerald-500/20"} border rounded-lg p-3 text-center`}>
          <div className={`text-2xl font-bold ${report.total_unresolved > 0 ? "text-red-400" : "text-emerald-400"}`}>
            {report.total_unresolved}
          </div>
          <div className="text-xs text-surface-400">Unresolved</div>
        </div>
      </div>

      {/* Repairs made */}
      {report.repairs_made.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-surface-300 mb-2">Repairs Made</h4>
          <div className="space-y-1.5">
            {report.repairs_made.map((repair, i) => (
              <div
                key={i}
                className="flex items-start gap-2 p-2.5 bg-emerald-500/5 border border-emerald-500/10 rounded-lg"
              >
                <span className="text-emerald-400 mt-0.5">✓</span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-emerald-300">{repair.description}</div>
                  <div className="text-xs text-surface-500 mt-0.5">
                    {repair.layer} • {repair.method} • {repair.duration_ms}ms
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unresolved issues */}
      {report.unresolved_issues.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-red-400 mb-2">Unresolved Issues</h4>
          <div className="space-y-1.5">
            {report.unresolved_issues.map((issue, i) => (
              <div
                key={i}
                className="flex items-start gap-2 p-2.5 bg-red-500/5 border border-red-500/10 rounded-lg"
              >
                <span className="text-red-400 mt-0.5">✕</span>
                <div className="min-w-0 flex-1">
                  <div className="text-xs text-red-300">{issue.message}</div>
                  <div className="text-xs text-surface-500 mt-0.5">
                    {issue.layer} • {issue.path} • {issue.error_type}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timing */}
      <div className="text-xs text-surface-500 flex gap-4">
        <span>Validation: {report.validation_time_ms}ms</span>
        <span>Repair: {report.repair_time_ms}ms</span>
      </div>
    </div>
  );
}
