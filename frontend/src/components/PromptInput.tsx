"use client";

import { useState } from "react";

interface PromptInputProps {
  onSubmit: (prompt: string, options: { fast_mode: boolean; skip_codegen: boolean }) => void;
  isLoading: boolean;
}

const EXAMPLE_PROMPTS = [
  {
    label: "CRM with Payments",
    prompt: "Build a CRM with login, contacts, deals pipeline, dashboard, admin and sales roles, email tracking, and Stripe payment for premium plan",
  },
  {
    label: "Project Management",
    prompt: "Create a project management tool like Linear with teams, issues, sprints, priorities, assignees, and GitHub integration",
  },
  {
    label: "E-Commerce Platform",
    prompt: "Build an e-commerce platform with products, cart, checkout, orders, seller dashboard, buyer dashboard, and Stripe payments",
  },
  {
    label: "Learning Management",
    prompt: "Create a learning management system with courses, lessons, quizzes, student progress tracking, instructor and student roles",
  },
  {
    label: "Analytics Dashboard",
    prompt: "Build a multi-tenant SaaS analytics dashboard with workspaces, data sources, charts, alerts, and team collaboration",
  },
];

export default function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const [fastMode, setFastMode] = useState(false);
  const [skipCodegen, setSkipCodegen] = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim().length < 3) return;
    onSubmit(prompt, { fast_mode: fastMode, skip_codegen: skipCodegen });
  };

  const selectExample = (examplePrompt: string) => {
    setPrompt(examplePrompt);
    setShowExamples(false);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative">
        <textarea
          id="prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe your app in natural language... e.g. 'Build a CRM with login, contacts, dashboard, and role-based access'"
          className="w-full h-36 p-4 bg-surface-800/50 border border-surface-600/50 rounded-xl text-white placeholder-surface-500 resize-none focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500/50 transition-all font-sans text-sm leading-relaxed"
          disabled={isLoading}
        />
        <div className="absolute bottom-3 right-3 text-xs text-surface-500">
          {prompt.length}/5000
        </div>
      </div>

      {/* Example prompts dropdown */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setShowExamples(!showExamples)}
          className="text-sm text-brand-400 hover:text-brand-300 transition-colors flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Try an example
          <svg className={`w-3 h-3 transition-transform ${showExamples ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showExamples && (
          <div className="absolute z-10 mt-2 w-full bg-surface-800 border border-surface-600/50 rounded-xl shadow-2xl overflow-hidden animate-fade-in">
            {EXAMPLE_PROMPTS.map((example) => (
              <button
                key={example.label}
                type="button"
                onClick={() => selectExample(example.prompt)}
                className="w-full text-left px-4 py-3 hover:bg-surface-700/50 transition-colors border-b border-surface-700/30 last:border-0"
              >
                <div className="text-sm font-medium text-white">{example.label}</div>
                <div className="text-xs text-surface-400 mt-0.5 line-clamp-1">{example.prompt}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Options */}
      <div className="flex items-center gap-6">
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={fastMode}
            onChange={(e) => setFastMode(e.target.checked)}
            className="w-4 h-4 rounded border-surface-500 bg-surface-700 text-brand-500 focus:ring-brand-500/50"
          />
          <span className="text-sm text-surface-400 group-hover:text-surface-300 transition-colors">
            Fast Mode
            <span className="text-xs text-surface-500 ml-1">(~40% cheaper)</span>
          </span>
        </label>

        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            checked={skipCodegen}
            onChange={(e) => setSkipCodegen(e.target.checked)}
            className="w-4 h-4 rounded border-surface-500 bg-surface-700 text-brand-500 focus:ring-brand-500/50"
          />
          <span className="text-sm text-surface-400 group-hover:text-surface-300 transition-colors">
            Skip Code Generation
          </span>
        </label>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading || prompt.trim().length < 3}
        className="w-full py-3 px-6 bg-gradient-to-r from-brand-600 to-brand-500 hover:from-brand-500 hover:to-brand-400 disabled:from-surface-700 disabled:to-surface-700 disabled:text-surface-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-lg shadow-brand-500/20 hover:shadow-brand-500/30 disabled:shadow-none flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Compiling...
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Compile App
          </>
        )}
      </button>
    </form>
  );
}
