/**
 * useWorkspaceStore
 *
 * Global Zustand store for the Monaco report review workspace.
 * Tracks open editor tabs, the active file, folder expand/collapse state,
 * selected issue id, and the focused line range for decorations.
 *
 * Architecture note: This store holds ONLY presentation-layer UI state.
 * Server data (report DTOs) is managed by TanStack Query in feature hooks.
 */

import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EditorTab {
  /** Relative file path used as a stable key */
  filePath: string;
  /** Display label shown in the tab strip */
  label: string;
  /** Raw source content buffered from the report DTO */
  content: string;
  /** Language identifier passed to Monaco (e.g. "python", "typescript") */
  language: string;
}

export interface FocusedLine {
  /** 1-indexed start line to scroll to and highlight */
  lineStart: number;
  /** 1-indexed end line (inclusive) */
  lineEnd: number;
}

export interface WorkspaceState {
  /** Ordered list of currently open editor tabs */
  tabs: EditorTab[];
  /** File path of the currently visible tab (null = nothing open) */
  activeFilePath: string | null;
  /** Map of folder path → expanded flag */
  expandedFolders: Record<string, boolean>;
  /** ID of the review issue currently selected in the issue pane */
  selectedIssueId: string | null;
  /** Line range that Monaco should scroll to and decorate */
  focusedLine: FocusedLine | null;

  // Actions
  openTab: (tab: EditorTab) => void;
  closeTab: (filePath: string) => void;
  setActiveTab: (filePath: string) => void;
  toggleFolder: (folderPath: string) => void;
  selectIssue: (issueId: string | null) => void;
  setFocusedLine: (range: FocusedLine | null) => void;
  clearWorkspace: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  tabs: [],
  activeFilePath: null,
  expandedFolders: {},
  selectedIssueId: null,
  focusedLine: null,

  openTab: (tab) => {
    const { tabs } = get();
    const alreadyOpen = tabs.some((t) => t.filePath === tab.filePath);
    if (alreadyOpen) {
      // Just switch to the existing tab without duplicating it
      set({ activeFilePath: tab.filePath });
    } else {
      set({ tabs: [...tabs, tab], activeFilePath: tab.filePath });
    }
  },

  closeTab: (filePath) => {
    const { tabs, activeFilePath } = get();
    const remaining = tabs.filter((t) => t.filePath !== filePath);
    // Promote the last remaining tab when the active one is closed
    const newActive =
      activeFilePath === filePath
        ? (remaining[remaining.length - 1]?.filePath ?? null)
        : activeFilePath;
    set({ tabs: remaining, activeFilePath: newActive });
  },

  setActiveTab: (filePath) => set({ activeFilePath: filePath }),

  toggleFolder: (folderPath) => {
    const { expandedFolders } = get();
    set({
      expandedFolders: {
        ...expandedFolders,
        [folderPath]: !expandedFolders[folderPath],
      },
    });
  },

  selectIssue: (issueId) => set({ selectedIssueId: issueId }),

  setFocusedLine: (range) => set({ focusedLine: range }),

  clearWorkspace: () =>
    set({
      tabs: [],
      activeFilePath: null,
      expandedFolders: {},
      selectedIssueId: null,
      focusedLine: null,
    }),
}));
