/**
 * Widget configuration types and defaults.
 */

export interface WidgetConfig {
  apiKey: string;
  domain: string;
  wsUrl: string;
  color: string;
  position: 'bottom-right' | 'bottom-left';
  darkMode: 'light' | 'dark' | 'auto';
  language: string;
  title: string;
  subtitle: string;
  logo: string;
  placeholder: string;
  welcomeMessage: string;
  offlineMessage: string;
  visitorName: string;
  visitorEmail: string;
  zIndex: number;
}

export const DEFAULT_CONFIG: WidgetConfig = {
  apiKey: '',
  domain: 'https://api.example.com',
  wsUrl: 'wss://api.example.com/ws',
  color: '#2563eb',
  position: 'bottom-right',
  darkMode: 'auto',
  language: 'es',
  title: 'Chat with us',
  subtitle: 'We usually reply within minutes',
  logo: '',
  placeholder: 'Type a message...',
  welcomeMessage: 'Hi! How can we help you today?',
  offlineMessage: 'We are currently offline. Leave a message!',
  visitorName: '',
  visitorEmail: '',
  zIndex: 99999,
};

export interface Message {
  id: string;
  content: string;
  sender_type: 'user' | 'agent' | 'ai' | 'system';
  sender_name: string;
  created_at: string;
  status?: 'sending' | 'sent' | 'delivered' | 'read';
}
