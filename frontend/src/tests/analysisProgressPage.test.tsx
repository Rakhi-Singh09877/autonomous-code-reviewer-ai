import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Mock next/navigation ─────────────────────────────────────────────────────
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

// ─── Mock react `use` so we can resolve params synchronously ──────────────────
const MOCK_ID = "8547f6b0-ed28-4d60-ade9-da892e2bd9d4";

vi.mock("react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react")>();
  return {
    ...actual,
    use: vi.fn(() => ({ id: MOCK_ID })),
  };
});

// ─── Mock useAnalysisProgress ─────────────────────────────────────────────────
import type { UseAnalysisProgressResult } from "@/features/analysis/hooks/useAnalysisProgress";

const mockHookResult: UseAnalysisProgressResult = {
  progress: null,
  connected: false,
  error: null,
};

vi.mock("@/features/analysis/hooks/useAnalysisProgress", () => ({
  useAnalysisProgress: vi.fn(() => ({ ...mockHookResult })),
}));

// ─── Imports after mocks ──────────────────────────────────────────────────────
import AnalysisProgressPage from "@/app/dashboard/analysis/[id]/page";
import { useAnalysisProgress } from "@/features/analysis/hooks/useAnalysisProgress";

const MOCK_PARAMS = Promise.resolve({ id: MOCK_ID });

function makeProgress(
  overrides: Partial<{
    status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
    progress_percentage: number;
    current_file: string | null;
    total_files: number;
    errors: string[];
  }> = {},
) {
  return {
    analysis_id: MOCK_ID,
    status: "PROCESSING" as const,
    progress_percentage: 45,
    current_file: "src/main.py",
    total_files: 20,
    errors: [],
    ...overrides,
  };
}

function setHookResult(result: Partial<UseAnalysisProgressResult>) {
  const next = { progress: null, connected: false, error: null, ...result } as UseAnalysisProgressResult;
  vi.mocked(useAnalysisProgress).mockReturnValue(next);
}

function renderPage() {
  return render(<AnalysisProgressPage params={MOCK_PARAMS} />);
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("AnalysisProgressPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPush.mockReset();
    vi.mocked(useAnalysisProgress).mockReturnValue({ progress: null, connected: false, error: null });
  });

  // ── Loading state ───────────────────────────────────────────────────────────

  it("renders loading state when not yet connected and no progress", () => {
    setHookResult({ connected: false, progress: null, error: null });
    renderPage();

    expect(screen.getByTestId("loading-state")).toBeTruthy();
    expect(screen.queryByTestId("progress-panel")).toBeNull();
    expect(screen.queryByTestId("error-state")).toBeNull();
  });

  it("renders loading state when connected but no first event yet", () => {
    setHookResult({ connected: true, progress: null, error: null });
    renderPage();

    expect(screen.getByTestId("loading-state")).toBeTruthy();
  });

  it("shows the analysis ID in the loading state", () => {
    setHookResult({ connected: false, progress: null, error: null });
    renderPage();

    expect(screen.getByText(MOCK_ID)).toBeTruthy();
  });

  // ── Progress / connected state ──────────────────────────────────────────────

  it("renders progress panel when connected with a progress payload", () => {
    setHookResult({ connected: true, progress: makeProgress(), error: null });
    renderPage();

    expect(screen.getByTestId("progress-panel")).toBeTruthy();
    expect(screen.queryByTestId("loading-state")).toBeNull();
    expect(screen.queryByTestId("error-state")).toBeNull();
  });

  it("displays progress percentage in the panel", () => {
    setHookResult({ connected: true, progress: makeProgress({ progress_percentage: 72 }), error: null });
    renderPage();

    expect(screen.getByTestId("progress-percentage").textContent).toContain("72.0");
  });

  it("displays the current file", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ current_file: "utils/helpers.py" }),
      error: null,
    });
    renderPage();

    expect(screen.getByText("utils/helpers.py")).toBeTruthy();
  });

  it("displays total files count", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ total_files: 35 }),
      error: null,
    });
    renderPage();

    expect(screen.getByText("35")).toBeTruthy();
  });

  it("displays error count from the progress payload", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ errors: ["err1", "err2"] }),
      error: null,
    });
    renderPage();

    expect(screen.getByText("2")).toBeTruthy();
  });

  it("does NOT show the View Report button when status is PROCESSING", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ status: "PROCESSING" }),
      error: null,
    });
    renderPage();

    expect(screen.queryByTestId("view-report-btn")).toBeNull();
  });

  // ── Completed state ─────────────────────────────────────────────────────────

  it("shows View Report button when status is COMPLETED", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ status: "COMPLETED", progress_percentage: 100 }),
      error: null,
    });
    renderPage();

    const btn = screen.getByTestId("view-report-btn");
    expect(btn).toBeTruthy();
    expect(btn.textContent).toContain("View Report");
  });

  it("navigates to the report page when View Report is clicked", () => {
    setHookResult({
      connected: true,
      progress: makeProgress({ status: "COMPLETED", progress_percentage: 100 }),
      error: null,
    });
    renderPage();

    fireEvent.click(screen.getByTestId("view-report-btn"));

    expect(mockPush).toHaveBeenCalledOnce();
    expect(mockPush).toHaveBeenCalledWith(`/dashboard/reports/${MOCK_ID}`);
  });

  // ── Error state ─────────────────────────────────────────────────────────────

  it("renders error state when hook returns an error", () => {
    setHookResult({
      connected: false,
      progress: null,
      error: "EventSource failed to connect",
    });
    renderPage();

    expect(screen.getByTestId("error-state")).toBeTruthy();
    expect(screen.getByText("EventSource failed to connect")).toBeTruthy();
    expect(screen.queryByTestId("loading-state")).toBeNull();
    expect(screen.queryByTestId("progress-panel")).toBeNull();
  });

  it("error state takes precedence over progress", () => {
    setHookResult({
      connected: false,
      progress: makeProgress(),
      error: "Connection lost",
    });
    renderPage();

    expect(screen.getByTestId("error-state")).toBeTruthy();
    expect(screen.queryByTestId("progress-panel")).toBeNull();
  });

  // ── Hook wiring ─────────────────────────────────────────────────────────────

  it("calls useAnalysisProgress with the analysisId from params", () => {
    renderPage();
    expect(useAnalysisProgress).toHaveBeenCalledWith(MOCK_ID);
  });
});
