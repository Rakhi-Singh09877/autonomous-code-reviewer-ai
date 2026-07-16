/**
 * src/tests/reports.test.tsx
 *
 * Phase 4 unit tests for:
 * - useWorkspaceStore (tab operations, folder toggle, issue selection)
 * - IssueNavigatorPane (severity sorting, category filtering)
 * - RefactorDiffViewer (renders original vs suggested fix)
 *
 * Note: @testing-library/jest-dom is not installed.
 * DOM presence is asserted with .not.toBeNull() / .toBeTruthy() and
 * text content is checked with element.textContent.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { useWorkspaceStore } from "../stores/useWorkspaceStore";
import { IssueNavigatorPane } from "../features/reports/components/IssueNavigatorPane";
import { RefactorDiffViewer } from "../features/reports/components/RefactorDiffViewer";
import { ReviewIssue } from "../domain/entities";

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const CRITICAL_ISSUE = new ReviewIssue(
  "critical-1",
  "src/auth.py",
  5,
  7,
  "SECURITY",
  "CRITICAL",
  0.99,
  "Remote code execution via eval().",
  "Never use eval() with user input.",
  "result = ast.literal_eval(data)",
  "result = eval(data)"
);

const LOW_ISSUE = new ReviewIssue(
  "low-1",
  "src/utils.py",
  20,
  21,
  "CODE_QUALITY",
  "LOW",
  0.6,
  "Unused variable 'x'.",
  "Remove unused variable.",
  "# Remove 'x = 5'",
  "x = 5"
);

const MEDIUM_ISSUE = new ReviewIssue(
  "medium-1",
  "src/views.py",
  33,
  36,
  "PERFORMANCE",
  "MEDIUM",
  0.8,
  "Nested loop with O(n²) complexity.",
  "Flatten the loop.",
  "result = list(chain(items))",
  "result = [x for x in [y for y in items]]"
);

const TEST_ISSUE = new ReviewIssue(
  "issue-test-1",
  "src/main.py",
  10,
  12,
  "SECURITY",
  "HIGH",
  0.9,
  "SQL injection risk.",
  "Use parameterised queries.",
  "cursor.execute(query, (val,))",
  "cursor.execute(f'SELECT * FROM t WHERE x={val}')"
);

// ---------------------------------------------------------------------------
// useWorkspaceStore tests
// ---------------------------------------------------------------------------

describe("useWorkspaceStore", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      tabs: [],
      activeFilePath: null,
      expandedFolders: {},
      selectedIssueId: null,
      focusedLine: null,
    });
  });

  it("should open a new tab and set it as active", () => {
    const { result } = renderHook(() => useWorkspaceStore());

    act(() => {
      result.current.openTab({
        filePath: "src/main.py",
        label: "main.py",
        content: "print('hello')",
        language: "python",
      });
    });

    expect(result.current.tabs).toHaveLength(1);
    expect(result.current.activeFilePath).toBe("src/main.py");
  });

  it("should not duplicate a tab if the same file is opened twice", () => {
    const { result } = renderHook(() => useWorkspaceStore());
    const tab = { filePath: "src/app.ts", label: "app.ts", content: "", language: "typescript" };

    act(() => {
      result.current.openTab(tab);
      result.current.openTab(tab);
    });

    expect(result.current.tabs).toHaveLength(1);
  });

  it("should close a tab and promote the previous tab as active", () => {
    const { result } = renderHook(() => useWorkspaceStore());

    act(() => {
      result.current.openTab({ filePath: "a.py", label: "a.py", content: "", language: "python" });
      result.current.openTab({ filePath: "b.py", label: "b.py", content: "", language: "python" });
    });

    expect(result.current.activeFilePath).toBe("b.py");

    act(() => {
      result.current.closeTab("b.py");
    });

    expect(result.current.tabs).toHaveLength(1);
    expect(result.current.activeFilePath).toBe("a.py");
  });

  it("should toggle folder expansion state", () => {
    const { result } = renderHook(() => useWorkspaceStore());

    act(() => result.current.toggleFolder("src/auth"));
    expect(result.current.expandedFolders["src/auth"]).toBe(true);

    act(() => result.current.toggleFolder("src/auth"));
    expect(result.current.expandedFolders["src/auth"]).toBe(false);
  });

  it("should select an issue and update focused line", () => {
    const { result } = renderHook(() => useWorkspaceStore());

    act(() => {
      result.current.selectIssue("issue-99");
      result.current.setFocusedLine({ lineStart: 10, lineEnd: 15 });
    });

    expect(result.current.selectedIssueId).toBe("issue-99");
    expect(result.current.focusedLine).toEqual({ lineStart: 10, lineEnd: 15 });
  });

  it("should clear the entire workspace state", () => {
    const { result } = renderHook(() => useWorkspaceStore());

    act(() => {
      result.current.openTab({ filePath: "x.py", label: "x.py", content: "", language: "python" });
      result.current.selectIssue("issue-1");
      result.current.clearWorkspace();
    });

    expect(result.current.tabs).toHaveLength(0);
    expect(result.current.activeFilePath).toBeNull();
    expect(result.current.selectedIssueId).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// IssueNavigatorPane tests
// ---------------------------------------------------------------------------

describe("IssueNavigatorPane", () => {
  it("should render all issues when no filter is applied", () => {
    render(
      <IssueNavigatorPane
        issues={[CRITICAL_ISSUE, MEDIUM_ISSUE, LOW_ISSUE]}
        onSelectIssue={() => {}}
      />
    );

    // Use screen.queryByText and check truthiness — no jest-dom needed
    expect(screen.queryByText("Remote code execution via eval().")).not.toBeNull();
    expect(screen.queryByText("Nested loop with O(n²) complexity.")).not.toBeNull();
    expect(screen.queryByText("Unused variable 'x'.")).not.toBeNull();
  });

  it("should sort CRITICAL issues above LOW issues", () => {
    render(
      <IssueNavigatorPane
        issues={[LOW_ISSUE, CRITICAL_ISSUE]}
        onSelectIssue={() => {}}
      />
    );

    const cards = document.querySelectorAll("[id^='issue-card-']");
    expect(cards[0].id).toBe(`issue-card-${CRITICAL_ISSUE.id}`);
    expect(cards[1].id).toBe(`issue-card-${LOW_ISSUE.id}`);
  });

  it("should filter issues to the PERFORMANCE category only", () => {
    render(
      <IssueNavigatorPane
        issues={[CRITICAL_ISSUE, MEDIUM_ISSUE, LOW_ISSUE]}
        onSelectIssue={() => {}}
      />
    );

    // Click the filter button by its unique id
    const filterBtn = document.getElementById("issue-filter-performance");
    expect(filterBtn).not.toBeNull();
    fireEvent.click(filterBtn!);

    expect(screen.queryByText("Nested loop with O(n²) complexity.")).not.toBeNull();
    expect(screen.queryByText("Remote code execution via eval().")).toBeNull();
  });

  it("should show empty state when issues list is empty", () => {
    render(<IssueNavigatorPane issues={[]} onSelectIssue={() => {}} />);
    expect(screen.queryByText("No issues found")).not.toBeNull();
  });

  it("should call onSelectIssue with the clicked issue", () => {
    const spy = vi.fn();
    render(
      <IssueNavigatorPane
        issues={[CRITICAL_ISSUE]}
        onSelectIssue={spy}
      />
    );

    const card = document.getElementById(`issue-card-${CRITICAL_ISSUE.id}`);
    expect(card).not.toBeNull();
    fireEvent.click(card!);
    expect(spy).toHaveBeenCalledWith(CRITICAL_ISSUE);
  });
});

// ---------------------------------------------------------------------------
// RefactorDiffViewer tests
// ---------------------------------------------------------------------------

describe("RefactorDiffViewer", () => {
  it("should render the Original label panel", () => {
    render(<RefactorDiffViewer issue={TEST_ISSUE} onClose={() => {}} />);
    expect(screen.queryByLabelText("Original code snippet")).not.toBeNull();
    // Snippet is split across line-nodes; check substring presence via textContent
    const panel = screen.getByLabelText("Original code snippet");
    expect(panel.textContent).toContain("SELECT * FROM t");
  });

  it("should render the Suggested fix panel", () => {
    render(<RefactorDiffViewer issue={TEST_ISSUE} onClose={() => {}} />);
    expect(screen.queryByLabelText("Suggested code fix")).not.toBeNull();
    const panel = screen.getByLabelText("Suggested code fix");
    expect(panel.textContent).toContain("cursor.execute(query");
  });

  it("should display the file path in the header", () => {
    render(<RefactorDiffViewer issue={TEST_ISSUE} onClose={() => {}} />);
    const header = document.getElementById("refactor-diff-viewer");
    expect(header?.textContent).toContain("src/main.py");
  });

  it("should call onClose when the close button is clicked", () => {
    const closeSpy = vi.fn();
    render(<RefactorDiffViewer issue={TEST_ISSUE} onClose={closeSpy} />);
    fireEvent.click(screen.getByLabelText("Close diff viewer"));
    expect(closeSpy).toHaveBeenCalledOnce();
  });
});
