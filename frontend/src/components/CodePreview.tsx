"use client";

import { useState } from "react";
import type { CodeGenerationResult } from "@/types/schema";

interface CodePreviewProps {
  codeResult: CodeGenerationResult | null;
}

export default function CodePreview({ codeResult }: CodePreviewProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  if (!codeResult || codeResult.generated_files.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-surface-500">
        <div className="text-center">
          <div className="text-3xl mb-2 opacity-30">💻</div>
          <p className="text-sm">No generated code available</p>
        </div>
      </div>
    );
  }

  const files = codeResult.generated_files;
  const activeFile = selectedFile ? files.find((f) => f.path === selectedFile) : files[0];
  const report = codeResult.execution_report;

  // Group files by directory
  const fileTree: Record<string, string[]> = {};
  for (const file of files) {
    const parts = file.path.split("/");
    const dir = parts.length > 1 ? parts.slice(0, -1).join("/") : ".";
    if (!fileTree[dir]) fileTree[dir] = [];
    fileTree[dir].push(file.path);
  }

  return (
    <div className="space-y-4">
      {/* Compilation status */}
      <div className={`flex items-center gap-2 p-3 rounded-lg border ${
        report.compilation_success
          ? "bg-emerald-500/10 border-emerald-500/20"
          : "bg-amber-500/10 border-amber-500/20"
      }`}>
        {report.compilation_success ? (
          <>
            <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-emerald-400">Compilation checks passed</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <span className="text-sm text-amber-400">Compilation issues detected</span>
          </>
        )}
        <span className="text-xs text-surface-400 ml-auto">
          {codeResult.total_files} files • {codeResult.total_lines} lines
        </span>
      </div>

      {/* Errors */}
      {report.type_errors.length > 0 && (
        <div className="p-3 bg-red-500/5 border border-red-500/10 rounded-lg">
          <h4 className="text-xs font-semibold text-red-400 mb-1">Type Errors</h4>
          {report.type_errors.slice(0, 5).map((err, i) => (
            <div key={i} className="text-xs text-red-300/70 font-mono">{err}</div>
          ))}
        </div>
      )}

      {report.checks_skipped.length > 0 && (
        <div className="text-xs text-surface-500">
          Checks skipped: {report.checks_skipped.join(", ")}
        </div>
      )}

      {/* File browser */}
      <div className="grid grid-cols-[200px_1fr] gap-3 h-[400px]">
        {/* File tree */}
        <div className="bg-surface-900/50 border border-surface-700/30 rounded-lg overflow-auto p-2">
          {Object.entries(fileTree).sort().map(([dir, filePaths]) => (
            <div key={dir} className="mb-2">
              <div className="text-xs text-surface-500 font-mono px-2 py-1">{dir}/</div>
              {filePaths.sort().map((path) => {
                const fileName = path.split("/").pop() || path;
                const isActive = activeFile?.path === path;
                return (
                  <button
                    key={path}
                    onClick={() => setSelectedFile(path)}
                    className={`w-full text-left text-xs font-mono px-3 py-1.5 rounded transition-colors truncate ${
                      isActive
                        ? "bg-brand-600/20 text-brand-400"
                        : "text-surface-400 hover:text-surface-300 hover:bg-surface-800/50"
                    }`}
                  >
                    {fileName}
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* Code viewer */}
        <div className="bg-surface-900/50 border border-surface-700/30 rounded-lg overflow-auto">
          {activeFile ? (
            <div>
              <div className="sticky top-0 bg-surface-800/80 backdrop-blur-sm px-4 py-2 border-b border-surface-700/30 flex items-center justify-between">
                <span className="text-xs font-mono text-surface-400">{activeFile.path}</span>
                <span className="text-xs text-surface-600">{activeFile.language}</span>
              </div>
              <pre className="p-4 text-xs font-mono text-surface-300 whitespace-pre-wrap">
                {activeFile.content}
              </pre>
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-surface-500 text-sm">
              Select a file to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
