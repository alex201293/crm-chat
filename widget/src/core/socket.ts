/**
 * Widget WebSocket client.
 * Lightweight reconnecting WebSocket for real-time message delivery.
 */

import { WidgetConfig } from './config';

type EventCallback = (...args: any[]) => void;

export class WidgetSocket {
  private config: WidgetConfig;
  private ws: WebSocket | null = null;
  private listeners: Map<string, EventCallback[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnects = 5;
  private reconnectDelay = 2000;
  private conversationId: string | null = null;

  constructor(config: WidgetConfig) {
    this.config = config;
  }

  connect(): void {
    const url = `${this.config.wsUrl}?token=widget_${this.config.apiKey}&tenant_id=${this.config.apiKey}`;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;

        // Join conversation room if we have one
        const convId = localStorage.getItem(`crm_chat_conv_${this.config.apiKey}`);
        if (convId) {
          this.joinRoom(convId);
          this.conversationId = convId;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventName = data.event;
          const payload = data.data;

          if (eventName) {
            this.emit(eventName, payload);
          }
        } catch {
          // Ignore malformed messages
        }
      };

      this.ws.onclose = () => {
        this.attemptReconnect();
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.attemptReconnect();
    }
  }

  disconnect(): void {
    this.maxReconnects = 0; // Prevent reconnection
    this.ws?.close();
    this.ws = null;
  }

  joinRoom(conversationId: string): void {
    this.conversationId = conversationId;
    this.send({ event: 'join', data: { room: conversationId } });
  }

  sendTyping(isTyping: boolean): void {
    if (this.conversationId) {
      this.send({
        event: 'typing',
        data: { conversation_id: this.conversationId, is_typing: isTyping },
      });
    }
  }

  on(event: string, callback: EventCallback): void {
    const list = this.listeners.get(event) || [];
    list.push(callback);
    this.listeners.set(event, list);
  }

  private send(data: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private emit(event: string, payload: any): void {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach(cb => cb(payload));
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnects) return;
    this.reconnectAttempts++;

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay * this.reconnectAttempts);
  }
}
