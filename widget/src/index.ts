/**
 * CRM Chat Widget - Embeddable chat widget
 * 
 * Usage:
 * <script src="https://cdn.example.com/chat.js"></script>
 * <script>
 *   CRMChat.init({
 *     apiKey: 'your-tenant-api-key',
 *     domain: 'https://api.example.com',
 *     color: '#2563eb',
 *     position: 'bottom-right',
 *     darkMode: 'auto',
 *     language: 'es',
 *     title: 'Chat with us',
 *     subtitle: 'We usually reply within minutes',
 *     logo: 'https://example.com/logo.png',
 *   });
 * </script>
 */

import { ChatWidget } from './core/widget';
import { WidgetConfig, DEFAULT_CONFIG } from './core/config';

declare global {
  interface Window {
    CRMChat: {
      init: (config: Partial<WidgetConfig>) => void;
      open: () => void;
      close: () => void;
      toggle: () => void;
      destroy: () => void;
      on: (event: string, callback: (...args: unknown[]) => void) => void;
      sendMessage: (text: string) => void;
    };
  }
}

let widgetInstance: ChatWidget | null = null;

window.CRMChat = {
  init(userConfig: Partial<WidgetConfig>) {
    if (widgetInstance) {
      console.warn('[CRMChat] Widget already initialized');
      return;
    }

    const config: WidgetConfig = { ...DEFAULT_CONFIG, ...userConfig };

    if (!config.apiKey) {
      console.error('[CRMChat] apiKey is required');
      return;
    }

    widgetInstance = new ChatWidget(config);
    widgetInstance.mount();
  },

  open() {
    widgetInstance?.open();
  },

  close() {
    widgetInstance?.close();
  },

  toggle() {
    widgetInstance?.toggle();
  },

  destroy() {
    widgetInstance?.destroy();
    widgetInstance = null;
  },

  on(event: string, callback: (...args: unknown[]) => void) {
    widgetInstance?.on(event, callback);
  },

  sendMessage(text: string) {
    widgetInstance?.sendMessage(text);
  },
};

// Auto-init if data attributes present on script tag
(function autoInit() {
  const script = document.currentScript as HTMLScriptElement | null;
  if (script?.dataset.apiKey) {
    window.CRMChat.init({
      apiKey: script.dataset.apiKey,
      domain: script.dataset.domain,
      color: script.dataset.color,
      position: (script.dataset.position as WidgetConfig['position']) || 'bottom-right',
      darkMode: (script.dataset.darkMode as WidgetConfig['darkMode']) || 'auto',
      language: script.dataset.language || 'es',
    });
  }
})();
