"use client";

/**
 * IssueNavigatorPane
 *
 * Right-hand sidebar that renders the full review issue list for the active
 * report. Issues are sorted by severity (CRITICAL → LOW → INFO) and can
 * be filtered by category. Clicking an issue calls onSelectIssue so the
 * workspace hook can scroll Monaco to the relevant lines.
 *
 * Security: All user-visible text from the backend (description, explanation)
 * is rendered as plain text, NOT via dangerouslySetInnerHTML.
 */

import React, { useMemo, useState } from "react";
import {
  AlertTriangle,
  ShieldAlert,
  Zap,
  Bug,
  Info,
  Filter,
} from "lucide-react";
import {
  ReviewIssue,
  ReviewIssueSeverity,
  ReviewIssueCategory,
} from "@/domain/entities";
import { useWorkspaceStore } from "@/stores";

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_ORDER: Record<ReviewIssueSeverity, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
  INFO: 4,
};

const SEVERITY_STYLES: Record<ReviewIssueSeverity, string> = {
  CRITICAL: "bg-red-500/15 text-red-400 border-red-500/30",
  HIGH: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  MEDIUM: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  LOW: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  INFO: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
};

function SeverityIcon({ severity }: { severity: ReviewIssueSeverity }) {
  const cls = "w-3.5 h-3.5 shrink-0";
  switch (severity) {
    case "CRITICAL":
    case "HIGH":
      return <ShieldAlert className={cls} />;
    case "MEDIUM":
      return <AlertTriangle className={cls} />;
    case "LOW":
      return <Bug className={cls} />;
    default:
      return <Info className={cls} />;
  }
}

const CATEGORY_LABELS: Record<ReviewIssueCategory, string> = {
  CODE_QUALITY: "Quality",
  BUG_DETECTION: "Bug",
  SECURITY: "Security",
  PERFORMANCE: "Performance",
  BEST_PRACTICES: "Best Practices",
  MAINTAINABILITY: "Maintainability",
  CODE_SMELLS: "Code Smells",
  COMPLEXITY: "Complexity",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface IssueNavigatorPaneProps {
  issues: ReviewIssue[];
  onSelectIssue: (issue: ReviewIssue) => void;
}

export function IssueNavigatorPane({
  issues,
  onSelectIssue,
}: IssueNavigatorPaneProps) {
  const { selectedIssueId } = useWorkspaceStore();
  const [activeCategory, setActiveCategory] = useState<ReviewIssueCategory | "ALL">("ALL");

  // Unique categories found in the issue list
  const categories = useMemo<Array<ReviewIssueCategory | "ALL">>(() => {
    const unique = Array.from(new Set(issues.map((i) => i.category)));
    return ["ALL", ...unique] as Array<ReviewIssueCategory | "ALL">;
  }, [issues]);

  // Filtered + sorted issue list
  const visibleIssues = useMemo(() => {
    return issues
      .filter((i) => activeCategory === "ALL" || i.category === activeCategory)
      .sort(
        (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
      );
  }, [issues, activeCategory]);

  if (issues.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 h-40 text-muted-foreground">
        <Zap className="w-6 h-6 text-green-400" />
        <p className="text-sm">No issues found</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Category filter strip */}
      <div className="flex items-center gap-1 px-2 py-1.5 border-b border-border overflow-x-auto shrink-0">
        <Filter className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        {categories.map((cat) => (
          <button
            key={cat}
            id={`issue-filter-${cat.toLowerCase()}`}
            onClick={() => setActiveCategory(cat)}
            className={`text-[11px] px-2 py-0.5 rounded-full shrink-0 transition-colors ${
              activeCategory === cat
                ? "bg-primary text-primary-foreground font-medium"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            {cat === "ALL" ? "All" : CATEGORY_LABELS[cat]}
          </button>
        ))}
      </div>

      {/* Scrollable issue list */}
      <div className="flex-1 overflow-y-auto divide-y divide-border/50">
        {visibleIssues.map((issue) => {
          const isSelected = selectedIssueId === issue.id;
          return (
            <button
              key={issue.id}
              id={`issue-card-${issue.id}`}
              onClick={() => onSelectIssue(issue)}
              className={`w-full text-left px-3 py-2.5 flex flex-col gap-1 transition-colors ${
                isSelected
                  ? "bg-primary/10 border-l-2 border-l-primary"
                  : "hover:bg-muted/40 border-l-2 border-l-transparent"
              }`}
            >
              {/* Severity badge + file */}
              <div className="flex items-center gap-2">
                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded border ${SEVERITY_STYLES[issue.severity]}`}
                >
                  <SeverityIcon severity={issue.severity} />
                  {issue.severity}
                </span>
                <span className="text-[10px] text-muted-foreground truncate">
                  {issue.filePath}:{issue.lineStart}
                </span>
              </div>
              {/* Description — plain text only, never innerHTML */}
              <p className="text-xs text-foreground/90 leading-snug line-clamp-2">
                {issue.description}
              </p>
              {/* Category label */}
              <span className="text-[10px] text-muted-foreground">
                {CATEGORY_LABELS[issue.category]}
              </span>
            </button>
          );
        })}
      </div>

      {/* Summary footer */}
      <div className="shrink-0 px-3 py-1.5 border-t border-border text-[11px] text-muted-foreground flex items-center justify-between">
        <span>
          {visibleIssues.length} / {issues.length} issues
        </span>
        <span className="text-red-400 font-medium">
          {issues.filter((i) => i.isCritical).length} critical
        </span>
      </div>
    </div>
  );
}
