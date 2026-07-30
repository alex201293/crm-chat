"use client";

import { useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { wsClient } from "@/lib/websocket/client";
import { useChatStore, type Message, type Conversation } from "@/stores/chat.store";
import { useAuthStore } from "@/stores/auth.store";

interface SendMessagePayload {
  conversation_id: string;
  content: string;
  content_type?: "text" | "image" | "file" | "audio";
  metadata?: Record<string, unknown>;
}

export function useChat() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const {
    conversations,
    activeConversationId,
    messages,
    isTyping,
    connectionStatus,
    setConversations,
    setActiveConversation,
    addMessage,
    setMessages,
    setTyping,
    setConnectionStatus,
    updateConversation,
  } = useChatStore();

  // Connect WebSocket on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const tenantId = localStorage.getItem("tenant_id");

    if (!token || !tenantId) return;

    wsClient.connect({
      token,
      tenantId,
      onConnect: () => setConnectionStatus("connected"),
      onDisconnect: () => setConnectionStatus("disconnected"),
      onError: () => setConnectionStatus("reconnecting"),
    });

    // Listen for new messages
    wsClient.on("message:new", (data: unknown) => {
      const message = data as Message;
      addMessage(message.conversation_id, message);
      updateConversation(message.conversation_id, {
        last_message: message.content,
        last_message_at: message.created_at,
      });
    });

    // Listen for typing indicators
    wsClient.on("agent:typing", (data: unknown) => {
      const { conversation_id, is_typing } = data as {
        conversation_id: string;
        is_typing: boolean;
      };
      setTyping(conversation_id, is_typing);
    });

    return () => {
      wsClient.disconnect();
    };
  }, [user?.id]);

  // Fetch conversations
  const conversationsQuery = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const response = await apiClient.get<{ data: Conversation[] }>(
        "/api/v1/chat/conversations"
      );
      setConversations(response.data.data);
      return response.data.data;
    },
  });

  // Fetch messages for active conversation
  const messagesQuery = useQuery({
    queryKey: ["messages", activeConversationId],
    queryFn: async () => {
      if (!activeConversationId) return [];
      const response = await apiClient.get<{ data: Message[] }>(
        `/api/v1/chat/conversations/${activeConversationId}/messages`
      );
      setMessages(activeConversationId, response.data.data);
      return response.data.data;
    },
    enabled: !!activeConversationId,
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (payload: SendMessagePayload) => {
      const response = await apiClient.post<Message>(
        `/api/v1/chat/conversations/${payload.conversation_id}/messages`,
        payload
      );
      return response.data;
    },
    onSuccess: (message) => {
      addMessage(message.conversation_id, message);
    },
  });

  // Emit typing indicator
  const emitTyping = useCallback(
    (conversationId: string, typing: boolean) => {
      wsClient.emit("typing", { conversation_id: conversationId, is_typing: typing });
    },
    []
  );

  return {
    conversations,
    activeConversationId,
    messages: activeConversationId
      ? messages.get(activeConversationId) || []
      : [],
    isTyping: activeConversationId
      ? isTyping.get(activeConversationId) || false
      : false,
    connectionStatus,
    setActiveConversation,
    sendMessage: sendMessageMutation.mutate,
    isSending: sendMessageMutation.isPending,
    emitTyping,
    conversationsQuery,
    messagesQuery,
  };
}
