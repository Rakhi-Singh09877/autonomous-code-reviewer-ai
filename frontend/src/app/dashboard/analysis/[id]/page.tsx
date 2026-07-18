"use client";

import { use } from "react";
import { useRouter } from "next/navigation";
import {
  useAnalysisProgress,
  AnalysisProgressPayload,
} from "@/features/analysis/hooks/useAnalysisProgress";

// ─── Status badge ────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<AnalysisProgressPayload["status"], string> = {
  PENDING: "bg-zinc-700 text-zinc-300",
  PROCESSING: "bg-cyan-900/60 text-cyan-300",
  COMPLETED: "bg-emerald-900/60 text-emerald-300",
  FAILED: "bg-red-900/60 text-red-300",
};

function StatusBadge({ status }: { status: AnalysisProgressPayload["status"] }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLES[status]}`}
    >
      {status === "PROCESSING" && (
        <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse" />
      )}
      {status}
    </span>
  );
}

// ─── Progress bar ─────────────────────────────────────────────────────────────

function ProgressBar({ value }: { value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  return (
    <div className="relative h-2 w-full overflow-hidden rounded-full bg-zinc-800">
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        style={{ width: `${pct}%` }}
        className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-cyan-400 transition-all duration-700 ease-out"
      />
    </div>
  );
}

// ─── Stat row ─────────────────────────────────────────────────────────────────

function StatRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 border-b border-zinc-800 last:border-0">
      <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        {label}
      </span>
      <span className="text-sm text-zinc-200 font-mono">{value}</span>
    </div>
  );
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingState({ analysisId }: { analysisId: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[300px] gap-5" data-testid="loading-state">
      <div className="relative h-12 w-12">
        <svg className="animate-spin h-12 w-12 text-cyan-500" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-20"
            cx="12" cy="12" r="10"
            stroke="currentColor" strokeWidth="3"
          />
          <path
            className="opacity-80"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-zinc-300">Connecting to analysis stream…</p>
        <p className="mt-1 text-xs text-zinc-500 font-mono">{analysisId}</p>
      </div>
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function ErrorState({ message }: { message: string }) {
  return (
    <div
      role="alert"
      data-testid="error-state"
      className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-950/30 p-5"
    >
      <svg
        className="mt-0.5 h-5 w-5 shrink-0 text-red-400"
        fill="none" viewBox="0 0 24 24" stroke="currentColor"
      >
        <path
          strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
        />
      </svg>
      <div>
        <p className="text-sm font-semibold text-red-400">Connection Error</p>
        <p className="mt-0.5 text-xs text-red-300/80">{message}</p>
      </div>
    </div>
  );
}

// ─── Progress panel ───────────────────────────────────────────────────────────

function ProgressPanel({
  analysisId,
  progress,
  onViewReport,
}: {
  analysisId: string;
  progress: AnalysisProgressPayload;
  onViewReport: () => void;
}) {
  const isCompleted = progress.status === "COMPLETED";

  return (
    <div data-testid="progress-panel" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-white">Analysis in Progress</h2>
          <p className="mt-0.5 text-xs text-zinc-500 font-mono truncate max-w-xs" title={analysisId}>
            {analysisId}
          </p>
        </div>
        <StatusBadge status={progress.status} />
      </div>

      {/* Progress bar */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs text-zinc-400">
          <span>Progress</span>
          <span data-testid="progress-percentage">{progress.progress_percentage.toFixed(1)}%</span>
        </div>
        <ProgressBar value={progress.progress_percentage} />
      </div>

      {/* Stats */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900/50 px-4 py-1">
        <StatRow label="Analysis ID" value={progress.analysis_id} />
        <StatRow
          label="Status"
          value={<StatusBadge status={progress.status} />}
        />
        <StatRow
          label="Current file"
          value={
            <span className="text-zinc-300 truncate max-w-[240px] block text-right">
              {progress.current_file ?? "—"}
            </span>
          }
        />
        <StatRow label="Total files" value={String(progress.total_files)} />
        <StatRow
          label="Errors"
          value={
            <span className={progress.errors.length > 0 ? "text-red-400" : "text-zinc-200"}>
              {progress.errors.length}
            </span>
          }
        />
      </div>

      {/* Completed CTA */}
      {isCompleted && (
        <button
          data-testid="view-report-btn"
          onClick={onViewReport}
          className="w-full rounded-lg bg-emerald-500 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-emerald-400 shadow-md shadow-emerald-500/10 hover:shadow-emerald-500/20 transition duration-200"
        >
          View Report
        </button>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AnalysisProgressPage({ params }: PageProps) {
  const { id: analysisId } = use(params);
  const router = useRouter();
  const { progress, connected, error } = useAnalysisProgress(analysisId);

  const handleViewReport = () => {
    router.push(`/dashboard/reports/${analysisId}`);
  };

  return (
    <main className="min-h-screen bg-zinc-950 px-4 py-10">
      <div className="mx-auto max-w-xl">
        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Analysis Progress
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Real-time status from the code review pipeline.
          </p>
        </div>

        {/* Content card */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-xl">
          {error ? (
            <ErrorState message={error} />
          ) : !connected || !progress ? (
            <LoadingState analysisId={analysisId} />
          ) : (
            <ProgressPanel
              analysisId={analysisId}
              progress={progress}
              onViewReport={handleViewReport}
            />
          )}
        </div>
      </div>
    </main>
  );
}
