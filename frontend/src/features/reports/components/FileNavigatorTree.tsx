"use client";

/**
 * FileNavigatorTree
 *
 * Scrollable sidebar that renders the file paths found in a
 * RepositoryReviewReport as a hierarchical folder / file tree.
 *
 * - Folder expand/collapse state is stored in the global workspace store
 *   so it persists when the user switches editor tabs.
 * - File nodes are clickable; clicking calls onSelectFile which the parent
 *   page routes to useWorkspaceEditor.openFileFromReport.
 *
 * Note: react-window ships a CJS-only bundle incompatible with Turbopack's
 * strict ESM static analysis. A native overflow-y scroll container is used
 * for Phase 4; a true ESM-native virtual list (@tanstack/react-virtual)
 * can be added in Phase 5 if performance demands it.
 */

import React, { useMemo } from "react";
import { ChevronRight, ChevronDown, FileCode, Folder, FolderOpen } from "lucide-react";
import { FileReviewResult } from "@/domain/entities";
import { useWorkspaceStore } from "@/stores";

// ---------------------------------------------------------------------------
// Tree builder helpers
// ---------------------------------------------------------------------------

interface TreeNode {
  id: string;
  label: string;
  /** Folder path key used for toggle (full path segments joined) */
  folderKey: string;
  depth: number;
  isFolder: boolean;
  filePath?: string;
  issueCount: number;
}

function buildTreeNodes(
  fileResults: FileReviewResult[],
  expandedFolders: Record<string, boolean>
): TreeNode[] {
  const folderSet = new Set<string>();
  const fileMap = new Map<string, number>();

  for (const fr of fileResults) {
    fileMap.set(fr.filePath, fr.issues.length);
    const segments = fr.filePath.split("/");
    for (let i = 1; i < segments.length; i++) {
      folderSet.add(segments.slice(0, i).join("/"));
    }
  }

  const sortedFolders = Array.from(folderSet).sort();
  const nodes: TreeNode[] = [];

  for (const folder of sortedFolders) {
    const depth = folder.split("/").length - 1;
    nodes.push({
      id: `folder:${folder}`,
      folderKey: folder,
      label: folder.split("/").pop() ?? folder,
      depth,
      isFolder: true,
      issueCount: 0,
    });

    if (expandedFolders[folder]) {
      for (const [filePath, issueCount] of fileMap.entries()) {
        const parentFolder = filePath.substring(0, filePath.lastIndexOf("/"));
        if (parentFolder === folder) {
          nodes.push({
            id: `file:${filePath}`,
            folderKey: "",
            label: filePath.split("/").pop() ?? filePath,
            depth: depth + 1,
            isFolder: false,
            filePath,
            issueCount,
          });
        }
      }
    }
  }

  // Root-level files (no parent folder)
  for (const [filePath, issueCount] of fileMap.entries()) {
    if (!filePath.includes("/")) {
      nodes.push({
        id: `file:${filePath}`,
        folderKey: "",
        label: filePath,
        depth: 0,
        isFolder: false,
        filePath,
        issueCount,
      });
    }
  }

  return nodes;
}

// ---------------------------------------------------------------------------
// Row components
// ---------------------------------------------------------------------------

interface FolderRowProps {
  node: TreeNode;
  isExpanded: boolean;
  onToggle: (folderKey: string) => void;
}

function FolderRow({ node, isExpanded, onToggle }: FolderRowProps) {
  return (
    <div
      style={{ paddingLeft: node.depth * 16 + 8 }}
      className="flex items-center gap-1.5 h-7 cursor-pointer select-none text-sm text-muted-foreground hover:text-foreground hover:bg-muted/40 px-2 rounded transition-colors"
      onClick={() => onToggle(node.folderKey)}
      role="treeitem"
      aria-expanded={isExpanded}
      aria-selected={false}
      id={`tree-folder-${node.id.replace(/[:/]/g, "-")}`}
    >
      {isExpanded ? (
        <ChevronDown className="w-3.5 h-3.5 shrink-0" />
      ) : (
        <ChevronRight className="w-3.5 h-3.5 shrink-0" />
      )}
      {isExpanded ? (
        <FolderOpen className="w-3.5 h-3.5 shrink-0 text-yellow-500" />
      ) : (
        <Folder className="w-3.5 h-3.5 shrink-0 text-yellow-500" />
      )}
      <span className="truncate">{node.label}</span>
    </div>
  );
}

interface FileRowProps {
  node: TreeNode;
  isActive: boolean;
  onSelect: (filePath: string) => void;
}

function FileRow({ node, isActive, onSelect }: FileRowProps) {
  return (
    <div
      style={{ paddingLeft: node.depth * 16 + 8 }}
      className={`flex items-center gap-1.5 h-7 cursor-pointer select-none text-sm px-2 rounded transition-colors ${
        isActive
          ? "bg-primary/10 text-primary font-medium"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
      }`}
      onClick={() => node.filePath && onSelect(node.filePath)}
      role="treeitem"
      aria-selected={isActive}
      id={`tree-file-${node.id.replace(/[:/]/g, "-")}`}
    >
      <FileCode className="w-3.5 h-3.5 shrink-0 text-blue-400" />
      <span className="truncate flex-1">{node.label}</span>
      {node.issueCount > 0 && (
        <span className="ml-auto text-[10px] font-medium bg-destructive/20 text-destructive px-1.5 py-0.5 rounded-full">
          {node.issueCount}
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface FileNavigatorTreeProps {
  fileResults: FileReviewResult[];
  onSelectFile: (filePath: string) => void;
  height?: number;
}

export function FileNavigatorTree({
  fileResults,
  onSelectFile,
  height = 600,
}: FileNavigatorTreeProps) {
  const { expandedFolders, activeFilePath, toggleFolder } = useWorkspaceStore();

  const nodes = useMemo(
    () => buildTreeNodes(fileResults, expandedFolders),
    [fileResults, expandedFolders]
  );

  if (fileResults.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
        No files reviewed.
      </div>
    );
  }

  return (
    <div
      className="w-full overflow-y-auto"
      style={{ height }}
      aria-label="File navigator tree"
      role="tree"
    >
      {nodes.map((node) =>
        node.isFolder ? (
          <FolderRow
            key={node.id}
            node={node}
            isExpanded={!!expandedFolders[node.folderKey]}
            onToggle={toggleFolder}
          />
        ) : (
          <FileRow
            key={node.id}
            node={node}
            isActive={node.filePath === activeFilePath}
            onSelect={onSelectFile}
          />
        )
      )}
    </div>
  );
}
