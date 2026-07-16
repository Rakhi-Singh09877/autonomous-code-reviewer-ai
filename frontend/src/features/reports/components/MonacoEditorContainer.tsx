"use client";

/**
 * MonacoEditorContainer
 *
 * Read-only Monaco Editor instance that renders the selected file's source
 * code with inline issue decorations (coloured line highlights + gutter
 * glyphs). Scrolls to the focusedLine in the workspace store whenever the
 * selected issue changes.
 *
 * Architecture notes:
 * - Monaco is loaded with next/dynamic (dynamic import) so the heavy bundle
 *   is code-split and only fetched when the report page mounts.
 * - The component is a Client Component ("use client") because Monaco
 *   requires a browser DOM environment.
 * - Zero direct axios/fetch calls; all data arrives via props from the
 *   parent page that already consumed TanStack Query.
 */

import React, { useRef, useEffect, useCallback } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import type * as Monaco from "monaco-editor";
import { FileCode, Loader2 } from "lucide-react";
import { ReviewIssue } from "@/domain/entities";
import { useWorkspaceStore } from "@/stores";

// ---------------------------------------------------------------------------
// Severity → Monaco decoration colour mapping
// ---------------------------------------------------------------------------

const SEVERITY_DECORATION: Record<
  ReviewIssue["severity"],
  { className: string; glyphClass: string }
> = {
  CRITICAL: {
    className: "monaco-line-critical",
    glyphClass: "monaco-glyph-critical",
  },
  HIGH: {
    className: "monaco-line-high",
    glyphClass: "monaco-glyph-high",
  },
  MEDIUM: {
    className: "monaco-line-medium",
    glyphClass: "monaco-glyph-medium",
  },
  LOW: {
    className: "monaco-line-low",
    glyphClass: "monaco-glyph-low",
  },
  INFO: {
    className: "monaco-line-info",
    glyphClass: "monaco-glyph-info",
  },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface MonacoEditorContainerProps {
  /** Source code to display */
  content: string;
  /** Monaco language identifier (e.g. "typescript", "python") */
  language: string;
  /** All issues relevant to this file (used to build decorations) */
  issues: ReviewIssue[];
  /** Height of the editor in pixels */
  height?: number;
}

export function MonacoEditorContainer({
  content,
  language,
  issues,
  height = 480,
}: MonacoEditorContainerProps) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<Monaco.editor.IEditorDecorationsCollection | null>(null);
  const { focusedLine } = useWorkspaceStore();

  // ------------------------------------------------------------------
  // Build decoration ranges from issue list
  // ------------------------------------------------------------------
  const buildDecorations = useCallback(
    (editor: Monaco.editor.IStandaloneCodeEditor, monaco: typeof Monaco) => {
      if (decorationsRef.current) {
        decorationsRef.current.clear();
      }
      const decorations: Monaco.editor.IModelDeltaDecoration[] = issues.map(
        (issue) => {
          const { className, glyphClass } = SEVERITY_DECORATION[issue.severity];
          return {
            range: new monaco.Range(
              issue.lineStart,
              1,
              issue.lineEnd,
              Number.MAX_SAFE_INTEGER
            ),
            options: {
              isWholeLine: true,
              className,
              glyphMarginClassName: glyphClass,
              hoverMessage: {
                value: `**${issue.severity}** — ${issue.description}`,
              },
            },
          };
        }
      );
      decorationsRef.current = editor.createDecorationsCollection(decorations);
    },
    [issues]
  );

  // ------------------------------------------------------------------
  // Editor mount handler
  // ------------------------------------------------------------------
  const handleEditorMount: OnMount = useCallback(
    (editor, monaco) => {
      editorRef.current = editor;

      // Inject CSS for decoration classes once
      const style = document.getElementById("monaco-decoration-styles");
      if (!style) {
        const el = document.createElement("style");
        el.id = "monaco-decoration-styles";
        el.textContent = `
          .monaco-line-critical { background: rgba(239,68,68,0.12) !important; }
          .monaco-line-high     { background: rgba(249,115,22,0.10) !important; }
          .monaco-line-medium   { background: rgba(234,179,8,0.10)  !important; }
          .monaco-line-low      { background: rgba(59,130,246,0.08) !important; }
          .monaco-line-info     { background: rgba(161,161,170,0.06) !important; }
          .monaco-glyph-critical::before { content: "●"; color: #ef4444; }
          .monaco-glyph-high::before    { content: "●"; color: #f97316; }
          .monaco-glyph-medium::before  { content: "●"; color: #eab308; }
          .monaco-glyph-low::before     { content: "●"; color: #3b82f6; }
          .monaco-glyph-info::before    { content: "●"; color: #a1a1aa; }
        `;
        document.head.appendChild(el);
      }

      buildDecorations(editor, monaco);
    },
    [buildDecorations]
  );

  // ------------------------------------------------------------------
  // Rebuild decorations when issues change
  // ------------------------------------------------------------------
  useEffect(() => {
    if (editorRef.current) {
      // Import monaco lazily so this effect doesn't block SSR
      import("monaco-editor").then((monaco) => {
        if (editorRef.current) buildDecorations(editorRef.current, monaco);
      });
    }
  }, [issues, buildDecorations]);

  // ------------------------------------------------------------------
  // Scroll to focused line when selectedIssueId changes
  // ------------------------------------------------------------------
  useEffect(() => {
    if (editorRef.current && focusedLine) {
      editorRef.current.revealLineInCenter(focusedLine.lineStart);
    }
  }, [focusedLine]);

  return (
    <div
      className="w-full rounded-md overflow-hidden border border-border bg-[#1e1e1e]"
      id="monaco-editor-container"
      role="region"
      aria-label="Code editor"
    >
      {/* File bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#252526] border-b border-[#3c3c3c]">
        <FileCode className="w-3.5 h-3.5 text-blue-400 shrink-0" />
        <span className="text-xs text-zinc-300 font-mono">{language}</span>
      </div>

      <Editor
        height={height}
        language={language}
        value={content}
        theme="vs-dark"
        loading={
          <div className="flex items-center gap-2 justify-center h-full text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading editor…
          </div>
        }
        options={{
          readOnly: true,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: "on",
          glyphMargin: true,
          scrollBeyondLastLine: false,
          wordWrap: "on",
          renderLineHighlight: "gutter",
          contextmenu: false,
          automaticLayout: true,
          scrollbar: {
            verticalScrollbarSize: 6,
            horizontalScrollbarSize: 6,
          },
        }}
        onMount={handleEditorMount}
      />
    </div>
  );
}
