import { IEventPort, SystemEvent } from "../../domain/ports";

export class WebSocketEventAdapter implements IEventPort {
  private socket: WebSocket | null = null;
  private readonly subscribers = new Map<string, Set<(event: SystemEvent) => void>>();
  private readonly url: string;

  constructor(customUrl?: string) {
    this.url = customUrl || "ws://localhost:3000/api/events";
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

    // Clean connection if no remaining active listeners exist
    if (this.subscribers.size === 0 && this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  private ensureConnection() {
    if (typeof window === "undefined" || this.socket) return;

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onmessage = (event) => {
        try {
          const rawEvent = JSON.parse(event.data);
          const sysEvent: SystemEvent = {
            type: rawEvent.type,
            payload: rawEvent.payload,
            timestamp: rawEvent.timestamp || new Date().toISOString(),
          };

          // Broadcast to matching channel subscribers
          const channel = rawEvent.channel;
          const channelSubs = this.subscribers.get(channel);
          if (channelSubs) {
            channelSubs.forEach((cb) => cb(sysEvent));
          }
        } catch (err) {
          console.error("Failed to parse incoming WebSocket stream event:", err);
        }
      };

      this.socket.onerror = (err) => {
        console.error("WebSocket adapter error encountered:", err);
      };

      this.socket.onclose = () => {
        this.socket = null;
      };
    } catch (err) {
      console.error("Failed to initialize WebSocket client stream link:", err);
    }
  }
}
export default WebSocketEventAdapter;
