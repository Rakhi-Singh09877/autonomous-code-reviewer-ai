"use client";

/**
 * /dashboard/reports/[id]
 *
 * Monaco Review Workspace page — Phase 4 entry point.
 *
 * Layout (three-column resizable split):
 * ┌─────────────────────────────────────────────────────────┐
 * │ FILE NAVIGATOR (left)  │  MONACO EDITOR (centre)        │
 * │                        │                                │
 * │                        ├────────────────────────────────┤
 * │                        │  REFACTOR DIFF VIEWER          │
 * ├────────────────────────┤  (shown when issue selected)   │
 * │ ISSUE NAVIGATOR (right)│                                │
 * └─────────────────────────────────────────────────────────┘
 *
 * This is a Client Component because it consumes the workspace Zustand store
 * and renders Monaco (which needs browser APIs).
 *
 * Data flow: TanStack Query fetches the report → passes down as props to
 * feature components → hooks coordinate Monaco state via the store.
 */

import React, { useEffect } from "react";
import { useParams } from "next/navigation";
import { FileNavigatorTree } from "@/features/reports/components/FileNavigatorTree";
import { IssueNavigatorPane } from "@/features/reports/components/IssueNavigatorPane";
import { MonacoEditorContainer } from "@/features/reports/components/MonacoEditorContainer";
import { RefactorDiffViewer } from "@/features/reports/components/RefactorDiffViewer";
import { useWorkspaceEditor } from "@/features/reports/hooks/useWorkspaceEditor";
import { useWorkspaceStore } from "@/stores";
import {
  RepositoryReviewReport,
  FileReviewResult,
  ReviewIssue,
} from "@/domain/entities";
import { TokenUsage } from "@/domain/value_objects/token-usage.value-object";

// ---------------------------------------------------------------------------
// Mock report factory — replaced by TanStack Query in Phase 5 integration
// ---------------------------------------------------------------------------

function buildMockReport(id: string): RepositoryReviewReport {
  const mockUsage = new TokenUsage(1200, 600, 1800, 0.0054);

  const issues: ReviewIssue[] = [
    new ReviewIssue(
      "issue-1",
      "src/auth/login.py",
      12,
      14,
      "SECURITY",
      "CRITICAL",
      0.97,
      "SQL injection vulnerability in login query.",
      "<p>The login function concatenates user input directly into a raw SQL string.</p>",
      "Use parameterised queries:\n\ncursor.execute('SELECT * FROM users WHERE email = %s', (email,))",
      "query = f\"SELECT * FROM users WHERE email = '{email}'\""
    ),
    new ReviewIssue(
      "issue-2",
      "src/auth/login.py",
      28,
      30,
      "BEST_PRACTICES",
      "MEDIUM",
      0.85,
      "Hardcoded secret key detected.",
      "<p>The SECRET_KEY value is hardcoded in source. Use environment variables instead.</p>",
      "SECRET_KEY = os.environ.get('SECRET_KEY')",
      "SECRET_KEY = 'my-super-secret-key'"
    ),
    new ReviewIssue(
      "issue-3",
      "src/utils/helpers.py",
      5,
      8,
      "PERFORMANCE",
      "LOW",
      0.72,
      "Inefficient list comprehension inside a loop.",
      "<p>The nested list comprehension creates O(n²) complexity.</p>",
      "Flatten the loop using itertools.chain or a generator.",
      "result = [x for x in [y for y in items]]"
    ),
  ];

  const fileResults: FileReviewResult[] = [
    new FileReviewResult(
      "src/auth/login.py",
      issues.slice(0, 2),
      61.5,
      3.2,
      new TokenUsage(800, 400, 1200, 0.0036)
    ),
    new FileReviewResult(
      "src/utils/helpers.py",
      issues.slice(2),
      88.0,
      1.1,
      new TokenUsage(400, 200, 600, 0.0018)
    ),
  ];

  return new RepositoryReviewReport(
    id,
    "repo-abc-123",
    new Date("2026-07-16T08:00:00Z"),
    2,
    3,
    { CRITICAL: 1, HIGH: 0, MEDIUM: 1, LOW: 1, INFO: 0 },
    { SECURITY: 1, BEST_PRACTICES: 1, PERFORMANCE: 1, CODE_QUALITY: 0, BUG_DETECTION: 0, MAINTAINABILITY: 0, CODE_SMELLS: 0, COMPLEXITY: 0 },
    74.75,
    fileResults,
    mockUsage
  );
}

// ---------------------------------------------------------------------------
// Collect all issues across every file result
// ---------------------------------------------------------------------------

function collectAllIssues(report: RepositoryReviewReport): ReviewIssue[] {
  return report.fileResults.flatMap((fr) => fr.issues);
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function ReportWorkspacePage() {
  const params = useParams<{ id: string }>();
  const reportId = params?.id ?? "demo";

  // In Phase 5 this will be: const { data: report } = useQuery(...)
  const report = buildMockReport(reportId);

  const allIssues = collectAllIssues(report);

  const {
    activeFilePath,
    tabs,
    openFileFromReport,
    jumpToIssue,
    closeTab,
    setActiveTab,
    clearWorkspace,
  } = useWorkspaceEditor();

  const { selectedIssueId: storeSelectedIssueId } = useWorkspaceStore();

  // Derive the active tab data
  const activeTab = tabs.find((t) => t.filePath === activeFilePath) ?? null;

  // Derive the selected issue for the diff viewer
  const selectedIssue: ReviewIssue | null =
    storeSelectedIssueId
      ? allIssues.find((i) => i.id === storeSelectedIssueId) ?? null
      : null;

  // Issues scoped to the active file
  const activeFileIssues: ReviewIssue[] = activeFilePath
    ? allIssues.filter((i) => i.filePath === activeFilePath)
    : [];

  // Open first file automatically on mount
  useEffect(() => {
    if (report.fileResults.length > 0 && !activeFilePath) {
      openFileFromReport(report, report.fileResults[0].filePath);
    }
    return () => clearWorkspace();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  return (
    <div
      className="flex h-[calc(100vh-4rem)] overflow-hidden bg-background"
      id="report-workspace"
    >
      {/* ── LEFT: File Navigator ─────────────────────────────────── */}
      <aside
        className="w-56 shrink-0 border-r border-border flex flex-col overflow-hidden"
        aria-label="File navigator"
      >
        <div className="px-3 py-2 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Files ({report.filesReviewed})
        </div>
        <div className="flex-1 overflow-hidden">
          <FileNavigatorTree
            fileResults={report.fileResults}
            onSelectFile={(fp) => openFileFromReport(report, fp)}
            height={600}
          />
        </div>
      </aside>

      {/* ── CENTRE: Editor + Diff Viewer ─────────────────────────── */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Tab strip */}
        {tabs.length > 0 && (
          <div
            className="flex items-center border-b border-border bg-muted/30 overflow-x-auto shrink-0"
            role="tablist"
            aria-label="Open editor tabs"
          >
            {tabs.map((tab) => (
              <div
                key={tab.filePath}
                role="tab"
                aria-selected={tab.filePath === activeFilePath}
                id={`editor-tab-${tab.filePath.replace(/[/\.]/g, "-")}`}
                className={`flex items-center gap-2 px-3 py-1.5 text-xs border-r border-border cursor-pointer shrink-0 transition-colors ${
                  tab.filePath === activeFilePath
                    ? "bg-background text-foreground font-medium border-b-2 border-b-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
                onClick={() => setActiveTab(tab.filePath)}
              >
                <span>{tab.label}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeTab(tab.filePath);
                  }}
                  className="text-muted-foreground/50 hover:text-foreground rounded transition-colors"
                  aria-label={`Close ${tab.label}`}
                  id={`close-tab-${tab.filePath.replace(/[/\.]/g, "-")}`}
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Monaco Editor */}
        <div className="flex-1 overflow-auto p-3 min-h-0">
          {activeTab ? (
            <MonacoEditorContainer
              content={activeTab.content}
              language={activeTab.language}
              issues={activeFileIssues}
              height={selectedIssue ? 300 : 480}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              Select a file from the navigator to begin review.
            </div>
          )}
        </div>

        {/* Refactor Diff Viewer — shown when issue is selected */}
        {selectedIssue && (
          <div className="shrink-0 max-h-64 overflow-hidden border-t border-border">
            <RefactorDiffViewer
              issue={selectedIssue}
              onClose={() => {
                useWorkspaceStore.getState().selectIssue(null);
                useWorkspaceStore.getState().setFocusedLine(null);
              }}
            />
          </div>
        )}
      </main>

      {/* ── RIGHT: Issue Navigator ───────────────────────────────── */}
      <aside
        className="w-72 shrink-0 border-l border-border flex flex-col overflow-hidden"
        aria-label="Issue navigator"
      >
        <div className="px-3 py-2 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
          <span>Issues ({allIssues.length})</span>
          <span className="text-red-400">
            Score: {report.averageScore.toFixed(1)}
          </span>
        </div>
        <div className="flex-1 overflow-hidden">
          <IssueNavigatorPane
            issues={allIssues}
            onSelectIssue={jumpToIssue}
          />
        </div>
      </aside>
    </div>
  );
}
