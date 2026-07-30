/**
 * Widget HTTP API client.
 * Communicates with the backend widget endpoints.
 */

import { WidgetConfig } from './config';

export class WidgetAPI {
  private baseUrl: string;
  private apiKey: string;

  constructor(config: WidgetConfig) {
    this.baseUrl = `${config.domain}/api/v1/widget`;
    this.apiKey = config.apiKey;
  }

  private headers(visitorId?: string, visitorName?: string): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey,
    };
    if (visitorId) h['X-Visitor-ID'] = visitorId;
    if (visitorName) h['X-Visitor-Name'] = visitorName;
    return h;
  }

  async createConversation(visitorId: string): Promise<{ conversation_id: string }> {
    const res = await fetch(`${this.baseUrl}/conversations`, {
      method: 'POST',
      headers: this.headers(visitorId),
      body: JSON.stringify({ channel: 'web' }),
    });
    if (!res.ok) throw new Error(`Create conversation failed: ${res.status}`);
    const data = await res.json();

    // Store conversation ID for history persistence
    localStorage.setItem(`crm_chat_conv_${this.apiKey}`, data.conversation_id);
    return data;
  }

  async sendMessage(
    conversationId: string,
    content: string,
    visitorId: string,
    visitorName: string
  ): Promise<any> {
    const res = await fetch(
      `${this.baseUrl}/conversations/${conversationId}/messages`,
      {
        method: 'POST',
        headers: this.headers(visitorId, visitorName),
        body: JSON.stringify({ content, content_type: 'text' }),
      }
    );
    if (!res.ok) throw new Error(`Send message failed: ${res.status}`);
    return res.json();
  }

  async getMessages(conversationId: string): Promise<any> {
    const res = await fetch(
      `${this.baseUrl}/conversations/${conversationId}/messages`,
      {
        method: 'GET',
        headers: this.headers(),
      }
    );
    if (!res.ok) throw new Error(`Get messages failed: ${res.status}`);
    return res.json();
  }

  async submitCSAT(conversationId: string, score: number, comment?: string): Promise<void> {
    await fetch(
      `${this.baseUrl}/../agents/conversations/${conversationId}/csat`,
      {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify({ score, comment }),
      }
    );
  }
}
