import { create } from "zustand";

export interface Message {
  id: string;
  conversation_id: string;
  content: string;
  sender_type: "user" | "agent" | "ai" | "system";
  sender_id: string;
  sender_name: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  contact_name: string;
  contact_avatar: string | null;
  channel: "web" | "whatsapp" | "email" | "telegram" | "facebook" | "instagram";
  status: "active" | "pending" | "resolved" | "closed";
  assigned_to: string | null;
  assigned_to_name: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  is_ai_handling: boolean;
}

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Map<string, Message[]>;
  isTyping: Map<string, boolean>;
  connectionStatus: "connected" | "disconnected" | "reconnecting";

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  addMessage: (conversationId: string, message: Message) => void;
  setMessages: (conversationId: string, messages: Message[]) => void;
  setTyping: (conversationId: string, isTyping: boolean) => void;
  setConnectionStatus: (status: ChatState["connectionStatus"]) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: new Map(),
  isTyping: new Map(),
  connectionStatus: "disconnected",

  setConversations: (conversations) => set({ conversations }),

  setActiveConversation: (id) => set({ activeConversationId: id }),

  addMessage: (conversationId, message) =>
    set((state) => {
      const newMessages = new Map(state.messages);
      const existing = newMessages.get(conversationId) || [];
      newMessages.set(conversationId, [...existing, message]);
      return { messages: newMessages };
    }),

  setMessages: (conversationId, messages) =>
    set((state) => {
      const newMessages = new Map(state.messages);
      newMessages.set(conversationId, messages);
      return { messages: newMessages };
    }),

  setTyping: (conversationId, isTyping) =>
    set((state) => {
      const newTyping = new Map(state.isTyping);
      newTyping.set(conversationId, isTyping);
      return { isTyping: newTyping };
    }),

  setConnectionStatus: (status) => set({ connectionStatus: status }),

  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((conv) =>
        conv.id === id ? { ...conv, ...updates } : conv
      ),
    })),
}));
