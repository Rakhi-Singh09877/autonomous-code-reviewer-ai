"use client";

/**
 * RefactorDiffViewer
 *
 * Side-by-side diff panel displayed beneath the Monaco editor when an issue
 * is selected. Shows the original problematic snippet (left) and the AI's
 * suggested fix (right).
 *
 * Security:
 * - Code snippets are rendered inside <pre> tags as plain text.
 * - DOMPurify is used to sanitise explanation text before injecting it as
 *   innerHTML because it may contain markdown-like HTML from the backend.
 */

import React, { useEffect, useRef } from "react";
import DOMPurify from "dompurify";
import { Code2, Wand2, X } from "lucide-react";
import { ReviewIssue } from "@/domain/entities";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Render explanation HTML via DOMPurify to mitigate XSS */
function SafeHtml({ html }: { html: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.innerHTML = DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ["p", "strong", "em", "code", "ul", "li", "ol", "br"],
        ALLOWED_ATTR: [],
      });
    }
  }, [html]);

  return <div ref={ref} className="text-xs text-muted-foreground leading-relaxed" />;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface RefactorDiffViewerProps {
  issue: ReviewIssue;
  onClose: () => void;
}

export function RefactorDiffViewer({ issue, onClose }: RefactorDiffViewerProps) {
  const originalLines = issue.snippet.split("\n");
  const fixLines = issue.suggestedFix.split("\n");

  return (
    <div
      className="flex flex-col bg-card border-t border-border"
      id="refactor-diff-viewer"
      role="region"
      aria-label="Refactoring suggestion"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Wand2 className="w-4 h-4 text-violet-400" />
          AI Suggested Fix
          <span className="text-[11px] text-muted-foreground font-normal">
            — {issue.filePath}:{issue.lineStart}–{issue.lineEnd}
          </span>
        </div>
        <button
          id="close-diff-viewer"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded hover:bg-muted/50"
          aria-label="Close diff viewer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Explanation */}
      <div className="px-4 py-2 border-b border-border">
        <SafeHtml html={issue.explanation} />
      </div>

      {/* Diff panels */}
      <div className="grid grid-cols-2 divide-x divide-border overflow-hidden">
        {/* Original */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-red-500/10 border-b border-border">
            <Code2 className="w-3.5 h-3.5 text-red-400" />
            <span className="text-[11px] font-medium text-red-400">Original</span>
          </div>
          <pre
            className="flex-1 overflow-auto p-3 text-xs font-mono leading-relaxed bg-red-500/5 text-foreground/80 whitespace-pre-wrap"
            aria-label="Original code snippet"
          >
            {originalLines.map((line, i) => (
              <div
                key={i}
                className="flex"
              >
                <span className="select-none w-8 shrink-0 text-right pr-2 text-muted-foreground/50 text-[10px]">
                  {issue.lineStart + i}
                </span>
                <span className="flex-1 text-red-300/80">{line}</span>
              </div>
            ))}
          </pre>
        </div>

        {/* Suggested fix */}
        <div className="flex flex-col overflow-hidden">
          <div className="flex items-center gap-1.5 px-3 py-1 bg-green-500/10 border-b border-border">
            <Wand2 className="w-3.5 h-3.5 text-green-400" />
            <span className="text-[11px] font-medium text-green-400">Suggested Fix</span>
          </div>
          <pre
            className="flex-1 overflow-auto p-3 text-xs font-mono leading-relaxed bg-green-500/5 text-foreground/80 whitespace-pre-wrap"
            aria-label="Suggested code fix"
          >
            {fixLines.map((line, i) => (
              <div key={i} className="flex">
                <span className="select-none w-8 shrink-0 text-right pr-2 text-muted-foreground/50 text-[10px]">
                  {i + 1}
                </span>
                <span className="flex-1 text-green-300/80">{line}</span>
              </div>
            ))}
          </pre>
        </div>
      </div>
    </div>
  );
}
