import { IEventPort, IApiPort, SystemEvent } from "../../domain/ports";

export class PollingEventAdapter implements IEventPort {
  private readonly subscribers = new Map<string, Set<(event: SystemEvent) => void>>();
  private readonly intervals = new Map<string, NodeJS.Timeout>();
  private readonly pollIntervalMs: number;

  constructor(private readonly apiPort: IApiPort, pollIntervalMs = 2000) {
    this.pollIntervalMs = pollIntervalMs;
  }

  public subscribe(channel: string, callback: (event: SystemEvent) => void): () => void {
    if (!this.subscribers.has(channel)) {
      this.subscribers.set(channel, new Set());
    }
    this.subscribers.get(channel)!.add(callback);

    this.startPolling(channel);

    return () => {
      this.unsubscribe(channel, callback);
    };
  }

  public unsubscribe(channel: string, callback?: (event: SystemEvent) => void): void {
    const channelSubs = this.subscribers.get(channel);
    if (!channelSubs) return;

    if (callback) {
      channelSubs.delete(callback);
    } else {
      channelSubs.clear();
    }

    if (channelSubs.size === 0) {
      this.subscribers.delete(channel);
      this.stopPolling(channel);
    }
  }

  private startPolling(channel: string) {
    if (this.intervals.has(channel)) return;

    const queryEndpoint = async () => {
      try {
        // Dynamic matching of target channels for background scanning
        if (channel.startsWith("analysis:")) {
          const id = channel.replace("analysis:", "");
          const status = await this.apiPort.getAnalysisStatus(id);

          const event: SystemEvent = {
            type: "ANALYSIS_PROGRESS",
            payload: {
              analysis_id: status.analysisId,
              status: status.status,
              progress_percentage: status.progressPercentage,
              current_file: status.currentFile,
              total_files: status.totalFiles,
              errors: status.errors,
            },
            timestamp: new Date().toISOString(),
          };

          const subs = this.subscribers.get(channel);
          if (subs) {
            subs.forEach((cb) => cb(event));
          }
        }
      } catch (err) {
        console.error(`Polling adapter error encountered on channel ${channel}:`, err);
      }
    };

    // Execute immediately on start
    queryEndpoint();

    const timer = setInterval(queryEndpoint, this.pollIntervalMs);
    this.intervals.set(channel, timer);
  }

  private stopPolling(channel: string) {
    const timer = this.intervals.get(channel);
    if (timer) {
      clearInterval(timer);
      this.intervals.delete(channel);
    }
  }
}
export default PollingEventAdapter;
