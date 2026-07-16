import { IEventPort, SystemEvent } from "../../domain/ports";

export class SseEventAdapter implements IEventPort {
  private eventSource: EventSource | null = null;
  private readonly subscribers = new Map<string, Set<(event: SystemEvent) => void>>();
  private readonly url: string;

  constructor(customUrl?: string) {
    this.url = customUrl || "http://localhost:3000/api/events/sse";
  }

  public subscribe(channel: string, callback: (event: SystemEvent) => void): () => void {
    if (!this.subscribers.has(channel)) {
      this.subscribers.set(channel, new Set());
    }
    this.subscribers.get(channel)!.add(callback);

    this.ensureConnection();

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
    }

    if (this.subscribers.size === 0 && this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  private ensureConnection() {
    if (typeof window === "undefined" || this.eventSource) return;

    try {
      this.eventSource = new EventSource(this.url);

      this.eventSource.onmessage = (event) => {
        try {
          const rawEvent = JSON.parse(event.data);
          const sysEvent: SystemEvent = {
            type: rawEvent.type,
            payload: rawEvent.payload,
            timestamp: rawEvent.timestamp || new Date().toISOString(),
          };

          const channel = rawEvent.channel;
          const channelSubs = this.subscribers.get(channel);
          if (channelSubs) {
            channelSubs.forEach((cb) => cb(sysEvent));
          }
        } catch (err) {
          console.error("Failed to parse incoming SSE stream event:", err);
        }
      };

      this.eventSource.onerror = (err) => {
        console.error("SSE connection error, closing adapter socket:", err);
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
      };
    } catch (err) {
      console.error("Failed to initialize SSE EventSource client link:", err);
    }
  }
}
export default SseEventAdapter;
