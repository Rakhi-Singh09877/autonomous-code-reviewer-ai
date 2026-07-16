/**
 * useWorkspaceEditor
 *
 * Application-layer hook that bridges the domain report entity with the
 * global workspace store. Exposes helper actions that components call without
 * needing to know about store internals or DTO shapes.
 *
 * Architecture note: Zero axios/fetch calls live here. Server data arrives
 * via the `report` prop from TanStack Query; this hook only coordinates
 * presentation state.
 */

"use client";

import { useCallback } from "react";
import { useWorkspaceStore, EditorTab } from "@/stores/useWorkspaceStore";
import { RepositoryReviewReport, ReviewIssue } from "@/domain/entities";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map file extension to a Monaco language identifier. */
function resolveLanguage(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    rs: "rust",
    go: "go",
    java: "java",
    cs: "csharp",
    cpp: "cpp",
    c: "c",
    rb: "ruby",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    md: "markdown",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    toml: "toml",
    sh: "shell",
    dockerfile: "dockerfile",
    html: "html",
    css: "css",
  };
  return map[ext] ?? "plaintext";
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export interface UseWorkspaceEditorReturn {
  /** Currently active tab path */
  activeFilePath: string | null;
  /** Open editor tabs list */
  tabs: EditorTab[];
  /** ID of the selected issue in the issue pane */
  selectedIssueId: string | null;
  /** Open a file from a FileReviewResult snippet */
  openFileFromReport: (report: RepositoryReviewReport, filePath: string) => void;
  /** Select an issue and jump Monaco to its line range */
  jumpToIssue: (issue: ReviewIssue) => void;
  /** Close a tab by file path */
  closeTab: (filePath: string) => void;
  /** Switch to an already-open tab */
  setActiveTab: (filePath: string) => void;
  /** Clear all workspace state */
  clearWorkspace: () => void;
}

export function useWorkspaceEditor(): UseWorkspaceEditorReturn {
  const {
    tabs,
    activeFilePath,
    selectedIssueId,
    openTab,
    closeTab,
    setActiveTab,
    selectIssue,
    setFocusedLine,
    clearWorkspace,
  } = useWorkspaceStore();

  /**
   * Open the source snippet for a specific file path from the report.
   * Uses the `snippet` field of the first issue found in that file as
   * a proxy for the file's code content (real integration would fetch
   * the raw file from a dedicated endpoint).
   */
  const openFileFromReport = useCallback(
    (report: RepositoryReviewReport, filePath: string) => {
      const fileResult = report.fileResults.find(
        (fr) => fr.filePath === filePath
      );
      const content =
        fileResult?.issues[0]?.snippet ??
        `// Source for ${filePath}\n// Full content available after backend file API integration.`;

      const tab: EditorTab = {
        filePath,
        label: filePath.split("/").pop() ?? filePath,
        content,
        language: resolveLanguage(filePath),
      };
      openTab(tab);
    },
    [openTab]
  );

  /**
   * Select an issue in the pane and scroll Monaco to the issue's line range.
   */
  const jumpToIssue = useCallback(
    (issue: ReviewIssue) => {
      selectIssue(issue.id);
      setFocusedLine({ lineStart: issue.lineStart, lineEnd: issue.lineEnd });
    },
    [selectIssue, setFocusedLine]
  );

  return {
    activeFilePath,
    tabs,
    selectedIssueId,
    openFileFromReport,
    jumpToIssue,
    closeTab,
    setActiveTab,
    clearWorkspace,
  };
}
