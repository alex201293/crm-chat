import { io, type Socket } from "socket.io-client";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export type WebSocketEvent =
  | "message:new"
  | "message:updated"
  | "conversation:new"
  | "conversation:updated"
  | "conversation:assigned"
  | "agent:typing"
  | "presence:update";

interface WebSocketConfig {
  token: string;
  tenantId: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

/**
 * WebSocket client with automatic reconnection, authentication,
 * and typed event handling.
 */
class WebSocketClient {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<(...args: unknown[]) => void>> = new Map();

  connect(config: WebSocketConfig): void {
    if (this.socket?.connected) return;

    this.socket = io(WS_URL, {
      auth: {
        token: config.token,
        tenant_id: config.tenantId,
      },
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30000,
      timeout: 20000,
    });

    this.socket.on("connect", () => {
      config.onConnect?.();
    });

    this.socket.on("disconnect", () => {
      config.onDisconnect?.();
    });

    this.socket.on("connect_error", (error) => {
      config.onError?.(error);
    });

    // Re-register any existing listeners
    this.listeners.forEach((handlers, event) => {
      handlers.forEach((handler) => {
        this.socket?.on(event, handler);
      });
    });
  }

  disconnect(): void {
    this.socket?.disconnect();
    this.socket = null;
  }

  on(event: WebSocketEvent | string, handler: (...args: unknown[]) => void): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
    this.socket?.on(event, handler);
  }

  off(event: WebSocketEvent | string, handler: (...args: unknown[]) => void): void {
    this.listeners.get(event)?.delete(handler);
    this.socket?.off(event, handler);
  }

  emit(event: string, data: unknown): void {
    this.socket?.emit(event, data);
  }

  joinRoom(room: string): void {
    this.socket?.emit("join", { room });
  }

  leaveRoom(room: string): void {
    this.socket?.emit("leave", { room });
  }

  get isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

// Singleton instance
export const wsClient = new WebSocketClient();
