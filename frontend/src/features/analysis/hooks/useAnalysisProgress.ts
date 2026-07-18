import { useEffect, useRef, useState } from "react";
import { SseEventAdapter } from "@/services/events/SseEventAdapter";
import { IEventPort, SystemEvent } from "@/domain/ports";
import { env } from "@/config";

export interface AnalysisProgressPayload {
  analysis_id: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  progress_percentage: number;
  current_file: string | null;
  total_files: number;
  errors: string[];
}

export interface UseAnalysisProgressResult {
  progress: AnalysisProgressPayload | null;
  connected: boolean;
  error: string | null;
}

export function useAnalysisProgress(
  analysisId: string,
  adapterOverride?: IEventPort,
): UseAnalysisProgressResult {
  const [progress, setProgress] = useState<AnalysisProgressPayload | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stable ref so the effect closure always reads the current adapter
  // without re-running the effect when an override is provided in tests.
  const adapterRef = useRef<IEventPort | null>(null);

  useEffect(() => {
    // Allow tests to inject a fresh adapter per render cycle or instantiate it
    if (adapterOverride) {
      adapterRef.current = adapterOverride;
    } else {
      adapterRef.current = new SseEventAdapter(
        `${env.BFF_URL}/events/sse?analysis_id=${analysisId}`
      );
    }

    const adapter = adapterRef.current;
    if (!adapter) return;

    const channel = `analysis:${analysisId}`;

    const handleEvent = (event: SystemEvent) => {
      if (event.type !== "ANALYSIS_PROGRESS") return;

      try {
        const payload = event.payload as AnalysisProgressPayload;
        setProgress(payload);
        setConnected(true);
        setError(null);
      } catch {
        setError("Received malformed progress event.");
      }
    };

    // subscribe returns the unsubscribe cleanup function
    let unsubscribe: (() => void) | undefined;
    try {
      unsubscribe = adapter.subscribe(channel, handleEvent);
      setConnected(true);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to connect to event stream.";
      setError(message);
      setConnected(false);
    }

    return () => {
      unsubscribe?.();
      setConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisId]);

  return { progress, connected, error };
}
