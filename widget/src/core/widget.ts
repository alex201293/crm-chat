/**
 * Main ChatWidget class.
 * Manages the widget lifecycle, UI rendering, and communication.
 */

import { WidgetConfig, Message } from './config';
import { WidgetAPI } from './api';
import { WidgetSocket } from './socket';
import { createWidgetStyles } from '../styles/widget-styles';
import { renderWidget } from '../components/chat-window';

export class ChatWidget {
  private config: WidgetConfig;
  private api: WidgetAPI;
  private socket: WidgetSocket | null = null;
  private container: HTMLDivElement | null = null;
  private shadowRoot: ShadowRoot | null = null;
  private isOpen = false;
  private conversationId: string | null = null;
  private visitorId: string;
  private messages: Message[] = [];
  private isTyping = false;
  private eventListeners: Map<string, ((...args: unknown[]) => void)[]> = new Map();

  constructor(config: WidgetConfig) {
    this.config = config;
    this.api = new WidgetAPI(config);
    this.visitorId = this.getOrCreateVisitorId();
  }

  mount(): void {
    // Create container with Shadow DOM for style isolation
    this.container = document.createElement('div');
    this.container.id = 'crm-chat-widget';
    this.container.setAttribute('aria-label', 'Chat widget');
    document.body.appendChild(this.container);

    this.shadowRoot = this.container.attachShadow({ mode: 'open' });

    // Inject styles
    const styleEl = document.createElement('style');
    styleEl.textContent = createWidgetStyles(this.config);
    this.shadowRoot.appendChild(styleEl);

    // Render UI
    this.render();

    // Load conversation history
    this.loadHistory();

    // Connect WebSocket
    this.connectSocket();
  }

  destroy(): void {
    this.socket?.disconnect();
    this.container?.remove();
    this.container = null;
    this.shadowRoot = null;
  }

  open(): void {
    this.isOpen = true;
    this.render();
    this.emit('open');
  }

  close(): void {
    this.isOpen = false;
    this.render();
    this.emit('close');
  }

  toggle(): void {
    this.isOpen ? this.close() : this.open();
  }

  on(event: string, callback: (...args: unknown[]) => void): void {
    const listeners = this.eventListeners.get(event) || [];
    listeners.push(callback);
    this.eventListeners.set(event, listeners);
  }

  async sendMessage(text: string): Promise<void> {
    if (!text.trim()) return;

    // Optimistic UI update
    const tempMsg: Message = {
      id: `temp_${Date.now()}`,
      content: text,
      sender_type: 'user',
      sender_name: this.config.visitorName || 'You',
      created_at: new Date().toISOString(),
      status: 'sending',
    };
    this.messages.push(tempMsg);
    this.render();

    try {
      // Ensure conversation exists
      if (!this.conversationId) {
        const conv = await this.api.createConversation(this.visitorId);
        this.conversationId = conv.conversation_id;
      }

      // Send message
      const response = await this.api.sendMessage(
        this.conversationId,
        text,
        this.visitorId,
        this.config.visitorName || 'Visitor'
      );

      // Replace temp message with real one
      const idx = this.messages.findIndex(m => m.id === tempMsg.id);
      if (idx >= 0) {
        this.messages[idx] = {
          id: response.message.id,
          content: response.message.content,
          sender_type: 'user',
          sender_name: response.message.sender_name,
          created_at: response.message.created_at,
          status: 'sent',
        };
      }

      // Add AI response if present
      if (response.ai_response) {
        this.messages.push({
          id: response.ai_response.id,
          content: response.ai_response.content,
          sender_type: response.ai_response.sender_type as Message['sender_type'],
          sender_name: response.ai_response.sender_name,
          created_at: response.ai_response.created_at,
        });
      }

      this.render();
      this.emit('messageSent', response.message);
    } catch (error) {
      // Mark as failed
      tempMsg.status = undefined;
      this.render();
      console.error('[CRMChat] Send failed:', error);
    }
  }

  // --- Private Methods ---

  private render(): void {
    if (!this.shadowRoot) return;

    // Remove existing content (except style)
    const style = this.shadowRoot.querySelector('style');
    this.shadowRoot.innerHTML = '';
    if (style) this.shadowRoot.appendChild(style);

    const html = renderWidget({
      config: this.config,
      isOpen: this.isOpen,
      messages: this.messages,
      isTyping: this.isTyping,
      onToggle: () => this.toggle(),
      onSend: (text: string) => this.sendMessage(text),
    });

    const wrapper = document.createElement('div');
    wrapper.innerHTML = html;
    this.shadowRoot.appendChild(wrapper);

    // Attach event listeners
    this.attachEvents();

    // Scroll to bottom
    const msgContainer = this.shadowRoot.querySelector('.crm-messages');
    if (msgContainer) {
      msgContainer.scrollTop = msgContainer.scrollHeight;
    }
  }

  private attachEvents(): void {
    if (!this.shadowRoot) return;

    // Toggle button
    const toggleBtn = this.shadowRoot.querySelector('.crm-toggle-btn');
    toggleBtn?.addEventListener('click', () => this.toggle());

    // Close button
    const closeBtn = this.shadowRoot.querySelector('.crm-close-btn');
    closeBtn?.addEventListener('click', () => this.close());

    // Send form
    const form = this.shadowRoot.querySelector('.crm-input-form');
    form?.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = this.shadowRoot?.querySelector('.crm-input') as HTMLInputElement;
      if (input?.value.trim()) {
        this.sendMessage(input.value.trim());
        input.value = '';
      }
    });

    // File upload
    const fileBtn = this.shadowRoot.querySelector('.crm-file-btn');
    fileBtn?.addEventListener('click', () => {
      const fileInput = document.createElement('input');
      fileInput.type = 'file';
      fileInput.accept = 'image/*,.pdf,.doc,.docx';
      fileInput.onchange = () => {
        if (fileInput.files?.[0]) {
          this.emit('fileSelected', fileInput.files[0]);
          // TODO: Upload file via API
        }
      };
      fileInput.click();
    });
  }

  private async loadHistory(): Promise<void> {
    const stored = localStorage.getItem(`crm_chat_conv_${this.config.apiKey}`);
    if (stored) {
      this.conversationId = stored;
      try {
        const history = await this.api.getMessages(this.conversationId);
        this.messages = history.data.map((m: any) => ({
          id: m.id,
          content: m.content,
          sender_type: m.sender_type,
          sender_name: m.sender_name,
          created_at: m.created_at,
        }));
        this.render();
      } catch {
        // Conversation may have expired, start fresh
        this.conversationId = null;
        localStorage.removeItem(`crm_chat_conv_${this.config.apiKey}`);
      }
    }
  }

  private connectSocket(): void {
    this.socket = new WidgetSocket(this.config);
    this.socket.connect();

    this.socket.on('message:new', (data: any) => {
      // Only add if not from us and not already in list
      if (data.sender_type !== 'user' && !this.messages.find(m => m.id === data.id)) {
        this.messages.push({
          id: data.id,
          content: data.content,
          sender_type: data.sender_type,
          sender_name: data.sender_name,
          created_at: data.created_at,
        });
        this.render();
        this.emit('messageReceived', data);
      }
    });

    this.socket.on('agent:typing', (data: any) => {
      this.isTyping = data.is_typing;
      this.render();
    });
  }

  private getOrCreateVisitorId(): string {
    const key = `crm_chat_visitor_${this.config.apiKey}`;
    let id = localStorage.getItem(key);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(key, id);
    }
    return id;
  }

  private emit(event: string, ...args: unknown[]): void {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(cb => cb(...args));
  }
}
