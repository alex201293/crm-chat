/**
 * Chat window HTML rendering.
 * Returns HTML strings for the widget UI components.
 */

import { WidgetConfig, Message } from '../core/config';

interface RenderProps {
  config: WidgetConfig;
  isOpen: boolean;
  messages: Message[];
  isTyping: boolean;
  onToggle: () => void;
  onSend: (text: string) => void;
}

export function renderWidget(props: RenderProps): string {
  const { config, isOpen, messages, isTyping } = props;
  const posClass = config.position === 'bottom-left' ? 'crm-left' : 'crm-right';

  return `
    <div class="crm-widget ${posClass}">
      ${isOpen ? renderChatWindow(config, messages, isTyping) : ''}
      ${renderToggleButton(config, isOpen)}
    </div>
  `;
}

function renderToggleButton(config: WidgetConfig, isOpen: boolean): string {
  return `
    <button class="crm-toggle-btn" aria-label="${isOpen ? 'Close chat' : 'Open chat'}">
      ${isOpen ? closeSVG() : chatSVG()}
    </button>
  `;
}

function renderChatWindow(config: WidgetConfig, messages: Message[], isTyping: boolean): string {
  return `
    <div class="crm-window" role="dialog" aria-label="Chat window">
      ${renderHeader(config)}
      <div class="crm-messages" role="log" aria-live="polite">
        ${messages.length === 0 ? renderWelcome(config) : ''}
        ${messages.map(renderMessage).join('')}
        ${isTyping ? renderTypingIndicator() : ''}
      </div>
      ${renderInputArea(config)}
    </div>
  `;
}

function renderHeader(config: WidgetConfig): string {
  return `
    <div class="crm-header">
      <div class="crm-header-info">
        ${config.logo ? `<img src="${config.logo}" alt="Logo" class="crm-logo" />` : ''}
        <div>
          <div class="crm-title">${escapeHtml(config.title)}</div>
          <div class="crm-subtitle">${escapeHtml(config.subtitle)}</div>
        </div>
      </div>
      <button class="crm-close-btn" aria-label="Close chat">
        ${closeSVG()}
      </button>
    </div>
  `;
}

function renderWelcome(config: WidgetConfig): string {
  if (!config.welcomeMessage) return '';
  return `
    <div class="crm-message crm-message-agent">
      <div class="crm-bubble crm-bubble-agent">
        ${escapeHtml(config.welcomeMessage)}
      </div>
    </div>
  `;
}

function renderMessage(msg: Message): string {
  const isUser = msg.sender_type === 'user';
  const isSystem = msg.sender_type === 'system';
  const isAgent = msg.sender_type === 'agent';
  const isAI = msg.sender_type === 'ai';

  if (isSystem) {
    return `
      <div class="crm-message crm-message-system">
        <div class="crm-bubble crm-bubble-system">
          🔔 ${escapeHtml(msg.content)}
        </div>
      </div>`;
  }

  const bubbleClass = isUser
    ? 'crm-bubble-user'
    : isAgent
    ? 'crm-bubble-agent crm-bubble-human'
    : 'crm-bubble-agent';

  const alignClass = isUser ? 'crm-message-user' : 'crm-message-agent';
  const time = formatTime(msg.created_at);
  const senderLabel = isAgent
    ? `👨‍💼 ${escapeHtml(msg.sender_name)}`
    : isAI
    ? `🤖 Asistente`
    : escapeHtml(msg.sender_name);
  const statusIcon = msg.status === 'sending' ? ' ⏳' : '';

  return `
    <div class="crm-message ${alignClass}">
      <div class="crm-bubble ${bubbleClass}">
        <div class="crm-bubble-content">${escapeHtml(msg.content)}</div>
        <div class="crm-bubble-meta">
          <span class="crm-bubble-time">${senderLabel} · ${time}${statusIcon}</span>
        </div>
      </div>
    </div>
  `;
}

function renderTypingIndicator(): string {
  return `
    <div class="crm-message crm-message-agent">
      <div class="crm-bubble crm-bubble-agent crm-typing">
        <span class="crm-dot"></span>
        <span class="crm-dot"></span>
        <span class="crm-dot"></span>
      </div>
    </div>
  `;
}

function renderInputArea(config: WidgetConfig): string {
  return `
    <form class="crm-input-form">
      <button type="button" class="crm-file-btn" aria-label="Attach file">
        ${attachSVG()}
      </button>
      <input
        type="text"
        class="crm-input"
        placeholder="${escapeHtml(config.placeholder)}"
        aria-label="Message input"
        autocomplete="off"
      />
      <button type="submit" class="crm-send-btn" aria-label="Send message">
        ${sendSVG()}
      </button>
    </form>
  `;
}

// --- Utilities ---
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

// --- SVG Icons ---
function chatSVG(): string {
  return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
}

function closeSVG(): string {
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
}

function sendSVG(): string {
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`;
}

function attachSVG(): string {
  return `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;
}
