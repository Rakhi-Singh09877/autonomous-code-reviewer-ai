import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import {
  useAnalysisProgress,
  AnalysisProgressPayload,
} from "@/features/analysis/hooks/useAnalysisProgress";
import { IEventPort, SystemEvent } from "@/domain/ports";

const MOCK_ID = "8547f6b0-ed28-4d60-ade9-da892e2bd9d4";
const MOCK_CHANNEL = `analysis:${MOCK_ID}`;

// ---------------------------------------------------------------------------
// Minimal fake adapter that captures the callback for manual dispatch
// ---------------------------------------------------------------------------
function makeFakeAdapter(): {
  adapter: IEventPort;
  dispatch: (event: SystemEvent) => void;
  subscribeMock: ReturnType<typeof vi.fn>;
  unsubscribeMock: ReturnType<typeof vi.fn>;
} {
  let capturedCallback: ((event: SystemEvent) => void) | undefined;
  const subscribeMock = vi.fn((channel: string, cb: (e: SystemEvent) => void) => {
    if (channel === MOCK_CHANNEL) capturedCallback = cb;
    return () => unsubscribeMock(channel);
  });
  const unsubscribeMock = vi.fn();

  const adapter: IEventPort = {
    subscribe: subscribeMock,
    unsubscribe: unsubscribeMock,
  };

  const dispatch = (event: SystemEvent) => {
    capturedCallback?.(event);
  };

  return { adapter, dispatch, subscribeMock, unsubscribeMock };
}

function makeProgressEvent(
  overrides: Partial<AnalysisProgressPayload> = {},
): SystemEvent {
  return {
    type: "ANALYSIS_PROGRESS",
    timestamp: new Date().toISOString(),
    payload: {
      analysis_id: MOCK_ID,
      status: "PROCESSING",
      progress_percentage: 45,
      current_file: "src/main.py",
      total_files: 20,
      errors: [],
      ...overrides,
    },
  };
}

// ---------------------------------------------------------------------------

describe("useAnalysisProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("subscribes to the correct channel on mount", () => {
    const { adapter, subscribeMock } = makeFakeAdapter();

    renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    expect(subscribeMock).toHaveBeenCalledOnce();
    expect(subscribeMock).toHaveBeenCalledWith(
      MOCK_CHANNEL,
      expect.any(Function),
    );
  });

  it("starts with connected=true and progress=null", () => {
    const { adapter } = makeFakeAdapter();

    const { result } = renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    expect(result.current.connected).toBe(true);
    expect(result.current.progress).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("updates progress state when an ANALYSIS_PROGRESS event is dispatched", () => {
    const { adapter, dispatch } = makeFakeAdapter();

    const { result } = renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    const event = makeProgressEvent({ progress_percentage: 72, current_file: "utils.py" });

    act(() => {
      dispatch(event);
    });

    expect(result.current.progress).not.toBeNull();
    expect(result.current.progress?.progress_percentage).toBe(72);
    expect(result.current.progress?.current_file).toBe("utils.py");
    expect(result.current.connected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("ignores events with a non-ANALYSIS_PROGRESS type", () => {
    const { adapter, dispatch } = makeFakeAdapter();

    const { result } = renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    act(() => {
      dispatch({
        type: "WORKER_STATUS_CHANGED",
        timestamp: new Date().toISOString(),
        payload: { worker: "idle" },
      });
    });

    // progress must remain null — irrelevant event type was silently ignored
    expect(result.current.progress).toBeNull();
  });

  it("calls the unsubscribe function returned by subscribe on unmount", () => {
    const { adapter, unsubscribeMock } = makeFakeAdapter();

    const { unmount } = renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    expect(unsubscribeMock).not.toHaveBeenCalled();

    unmount();

    expect(unsubscribeMock).toHaveBeenCalledOnce();
    expect(unsubscribeMock).toHaveBeenCalledWith(MOCK_CHANNEL);
  });

  it("cleanup is called exactly once on unmount, not on earlier renders", () => {
    const { adapter, unsubscribeMock } = makeFakeAdapter();

    const { unmount, rerender } = renderHook(
      ({ id }: { id: string }) => useAnalysisProgress(id, adapter),
      { initialProps: { id: MOCK_ID } },
    );

    // Re-render with same id does NOT call unsubscribe
    rerender({ id: MOCK_ID });
    expect(unsubscribeMock).not.toHaveBeenCalled();

    // Unmount triggers the cleanup — exactly once
    unmount();
    expect(unsubscribeMock).toHaveBeenCalledOnce();
  });

  it("surfaces an error and sets connected=false when adapter.subscribe throws", () => {
    const throwingAdapter: IEventPort = {
      subscribe: vi.fn(() => {
        throw new Error("EventSource failed to connect");
      }),
      unsubscribe: vi.fn(),
    };

    const { result } = renderHook(() =>
      useAnalysisProgress(MOCK_ID, throwingAdapter),
    );

    expect(result.current.connected).toBe(false);
    expect(result.current.error).toBe("EventSource failed to connect");
    expect(result.current.progress).toBeNull();
  });

  it("re-subscribes to the new channel when analysisId changes", () => {
    const { adapter, subscribeMock } = makeFakeAdapter();
    const SECOND_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

    const { rerender } = renderHook(
      ({ id }: { id: string }) => useAnalysisProgress(id, adapter),
      { initialProps: { id: MOCK_ID } },
    );

    expect(subscribeMock).toHaveBeenCalledTimes(1);
    expect(subscribeMock).toHaveBeenLastCalledWith(MOCK_CHANNEL, expect.any(Function));

    rerender({ id: SECOND_ID });

    expect(subscribeMock).toHaveBeenCalledTimes(2);
    expect(subscribeMock).toHaveBeenLastCalledWith(
      `analysis:${SECOND_ID}`,
      expect.any(Function),
    );
  });

  it("reflects COMPLETED status from the final progress event", () => {
    const { adapter, dispatch } = makeFakeAdapter();

    const { result } = renderHook(() => useAnalysisProgress(MOCK_ID, adapter));

    act(() => {
      dispatch(
        makeProgressEvent({
          status: "COMPLETED",
          progress_percentage: 100,
          current_file: null,
        }),
      );
    });

    expect(result.current.progress?.status).toBe("COMPLETED");
    expect(result.current.progress?.progress_percentage).toBe(100);
  });
});
