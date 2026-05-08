"use client";

import { useState } from "react";
import type { CompletedAppSchema } from "@/types/schema";

interface SchemaViewerProps {
  schema: CompletedAppSchema | null;
  onDownloadJson: (layer: string) => void;
  onDownloadZip: () => void;
}

type TabKey = "intent" | "architecture" | "ui" | "api" | "database" | "auth";

const TABS: { key: TabKey; label: string; icon: string }[] = [
  { key: "intent", label: "Intent", icon: "🎯" },
  { key: "architecture", label: "Architecture", icon: "📐" },
  { key: "ui", label: "UI", icon: "🖥️" },
  { key: "api", label: "API", icon: "🔗" },
  { key: "database", label: "Database", icon: "🗄️" },
  { key: "auth", label: "Auth", icon: "🔐" },
];

function JsonView({ data }: { data: unknown }) {
  const jsonStr = JSON.stringify(data, null, 2);
  return (
    <pre className="text-xs font-mono text-surface-300 bg-surface-900/50 p-4 rounded-lg overflow-auto max-h-[60vh] whitespace-pre-wrap border border-surface-700/30">
      {jsonStr}
    </pre>
  );
}

export default function SchemaViewer({ schema, onDownloadJson, onDownloadZip }: SchemaViewerProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("intent");

  if (!schema) {
    return (
      <div className="flex items-center justify-center h-64 text-surface-500">
        <div className="text-center">
          <div className="text-4xl mb-3 opacity-30">📋</div>
          <p className="text-sm">Submit a prompt to see the compiled schema</p>
        </div>
      </div>
    );
  }

  const getTabData = (tab: TabKey): unknown => {
    switch (tab) {
      case "intent": return schema.intent;
      case "architecture": return schema.architecture;
      case "ui": return schema.ui;
      case "api": return schema.api;
      case "database": return schema.database;
      case "auth": return schema.auth;
    }
  };

  return (
    <div className="space-y-4">
      {/* App info header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">{schema.meta.app_name}</h2>
          <p className="text-xs text-surface-400">{schema.intent.app_type} • {schema.intent.entities.length} entities • {schema.ui.pages.length} pages</p>
        </div>
        <button
          onClick={onDownloadZip}
          className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Download ZIP
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface-800/50 p-1 rounded-xl overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
              activeTab === tab.key
                ? "bg-brand-600/20 text-brand-400 shadow-sm"
                : "text-surface-400 hover:text-surface-300 hover:bg-surface-700/30"
            }`}
          >
            <span className="text-xs">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        <div className="flex justify-end mb-2">
          <button
            onClick={() => onDownloadJson(activeTab)}
            className="text-xs text-surface-400 hover:text-brand-400 transition-colors flex items-center gap-1"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download JSON
          </button>
        </div>
        <JsonView data={getTabData(activeTab)} />
      </div>

      {/* Generation meta */}
      <div className="grid grid-cols-3 gap-3 mt-4">
        <div className="bg-surface-800/30 rounded-lg p-3 border border-surface-700/20">
          <div className="text-xs text-surface-500">Duration</div>
          <div className="text-sm font-semibold text-white mt-1">
            {(schema.generation_meta.total_duration_ms / 1000).toFixed(1)}s
          </div>
        </div>
        <div className="bg-surface-800/30 rounded-lg p-3 border border-surface-700/20">
          <div className="text-xs text-surface-500">Cost</div>
          <div className="text-sm font-semibold text-white mt-1">
            ${schema.generation_meta.total_cost_usd.toFixed(4)}
          </div>
        </div>
        <div className="bg-surface-800/30 rounded-lg p-3 border border-surface-700/20">
          <div className="text-xs text-surface-500">Repairs</div>
          <div className="text-sm font-semibold text-white mt-1">
            {schema.generation_meta.errors_repaired}/{schema.generation_meta.errors_found}
          </div>
        </div>
      </div>
    </div>
  );
}
