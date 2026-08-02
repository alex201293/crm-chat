/**
 * Widget CSS styles generated dynamically from config.
 * Injected into Shadow DOM for complete isolation.
 */

import { WidgetConfig } from '../core/config';

export function createWidgetStyles(config: WidgetConfig): string {
  const isDark = config.darkMode === 'dark' ||
    (config.darkMode === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  const bg = isDark ? '#1f2937' : '#ffffff';
  const bgSecondary = isDark ? '#374151' : '#f3f4f6';
  const text = isDark ? '#f9fafb' : '#111827';
  const textMuted = isDark ? '#9ca3af' : '#6b7280';
  const border = isDark ? '#4b5563' : '#e5e7eb';
  const color = config.color;

  return `
    .crm-widget {
      position: fixed;
      z-index: ${config.zIndex};
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      line-height: 1.5;
      bottom: 20px;
    }
    .crm-right { right: 20px; }
    .crm-left { left: 20px; }

    .crm-toggle-btn {
      width: 56px; height: 56px;
      border-radius: 50%;
      background: ${color};
      border: none; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      color: white;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .crm-toggle-btn:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }

    .crm-window {
      position: absolute;
      bottom: 70px;
      width: 380px; height: 520px;
      background: ${bg};
      border-radius: 16px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.12);
      border: 1px solid ${border};
      display: flex; flex-direction: column;
      overflow: hidden;
      animation: crm-slide-up 0.2s ease-out;
    }
    .crm-right .crm-window { right: 0; }
    .crm-left .crm-window { left: 0; }

    @keyframes crm-slide-up {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .crm-header {
      padding: 16px;
      background: ${color};
      color: white;
      display: flex; align-items: center; justify-content: space-between;
    }
    .crm-header-info { display: flex; align-items: center; gap: 10px; }
    .crm-logo { width: 32px; height: 32px; border-radius: 50%; }
    .crm-title { font-weight: 600; font-size: 15px; }
    .crm-subtitle { font-size: 12px; opacity: 0.85; }
    .crm-close-btn {
      background: none; border: none; color: white;
      cursor: pointer; padding: 4px; border-radius: 4px;
    }
    .crm-close-btn:hover { background: rgba(255,255,255,0.15); }

    .crm-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 8px;
    }
    .crm-messages::-webkit-scrollbar { width: 4px; }
    .crm-messages::-webkit-scrollbar-thumb { background: ${border}; border-radius: 2px; }

    .crm-message { display: flex; }
    .crm-message-user { justify-content: flex-end; }
    .crm-message-agent { justify-content: flex-start; }
    .crm-message-system { justify-content: center; }

    .crm-bubble {
      max-width: 80%; padding: 10px 14px;
      border-radius: 12px; word-wrap: break-word;
    }
    .crm-bubble-user {
      background: ${color}; color: white;
      border-bottom-right-radius: 4px;
    }
    .crm-bubble-agent {
      background: ${bgSecondary}; color: ${text};
      border-bottom-left-radius: 4px;
    }
    .crm-bubble-human {
      background: #dcfce7; color: #166534;
      border-bottom-left-radius: 4px;
    }
    .crm-bubble-system {
      background: transparent; color: ${textMuted};
      font-size: 12px; font-style: italic; text-align: center;
    }
    .crm-bubble-content { white-space: pre-wrap; }
    .crm-bubble-meta {
      display: flex; gap: 4px; margin-top: 4px;
      font-size: 11px; opacity: 0.7;
    }

    .crm-typing {
      display: flex; gap: 4px; padding: 12px 16px;
    }
    .crm-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: ${textMuted};
      animation: crm-bounce 1.4s infinite;
    }
    .crm-dot:nth-child(2) { animation-delay: 0.2s; }
    .crm-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes crm-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-4px); }
    }

    .crm-input-form {
      display: flex; align-items: center; gap: 8px;
      padding: 12px 16px;
      border-top: 1px solid ${border};
      background: ${bg};
    }
    .crm-input {
      flex: 1; padding: 8px 12px;
      border: 1px solid ${border};
      border-radius: 20px;
      background: ${bgSecondary};
      color: ${text};
      outline: none; font-size: 14px;
    }
    .crm-input:focus { border-color: ${color}; }
    .crm-input::placeholder { color: ${textMuted}; }

    .crm-send-btn, .crm-file-btn {
      background: none; border: none; cursor: pointer;
      color: ${color}; padding: 4px;
      display: flex; align-items: center;
    }
    .crm-send-btn:hover, .crm-file-btn:hover { opacity: 0.7; }
    .crm-file-btn { color: ${textMuted}; }

    @media (max-width: 480px) {
      .crm-window {
        width: calc(100vw - 24px);
        height: calc(100vh - 100px);
        bottom: 70px;
        right: 12px; left: 12px;
        border-radius: 12px;
      }
    }
  `;
}
