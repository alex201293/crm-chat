"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Conversation {
  id: string;
  channel: string;
  status: string;
  last_message_preview: string | null;
  last_message_at: string | null;
  unread_count: number;
  is_ai_handling: boolean;
  contact_id: string | null;
}

interface Message {
  id: string;
  content: string;
  sender_type: string;
  sender_name: string;
  created_at: string;
  ai_generated: boolean;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "ahora";
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

const channelIcon: Record<string, string> = {
  web: "🌐", whatsapp: "📱", email: "📧",
  telegram: "✈️", facebook: "👤", instagram: "📸",
};

export default function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState("");

  // Get token
  useEffect(() => {
    const t = localStorage.getItem("access_token") || "";
    setToken(t);
  }, []);

  // Load conversations
  useEffect(() => {
    if (!token) return;
    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API}/api/v1/chat/conversations`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setConversations(data.data || []);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 5000); // refresh every 5s
    return () => clearInterval(interval);
  }, [token]);

  // Load messages for active conversation
  useEffect(() => {
    if (!activeId || !token) return;
    const load = async () => {
      try {
        const res = await fetch(
          `${API}/api/v1/chat/conversations/${activeId}/messages`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const data = await res.json();
        setMessages(data.data || []);
      } catch {
        // ignore
      }
    };
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [activeId, token]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || !activeId || !token) return;
    setSending(true);
    try {
      await fetch(`${API}/api/v1/chat/conversations/${activeId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: text.trim(), content_type: "text" }),
      });
      setText("");
      // reload messages
      const res = await fetch(
        `${API}/api/v1/chat/conversations/${activeId}/messages`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const data = await res.json();
      setMessages(data.data || []);
    } finally {
      setSending(false);
    }
  };

  const active = conversations.find((c) => c.id === activeId);

  return (
    <div className="flex h-full">
      {/* Sidebar conversaciones */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <input
            type="search"
            placeholder="Buscar conversaciones..."
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <p className="p-4 text-sm text-gray-400 text-center">Cargando...</p>
          )}
          {!loading && conversations.length === 0 && (
            <div className="p-6 text-center">
              <p className="text-4xl mb-2">💬</p>
              <p className="text-sm text-gray-500">Sin conversaciones aún.</p>
              <p className="text-xs text-gray-400 mt-1">
                Los mensajes del widget y WhatsApp aparecerán aquí.
              </p>
            </div>
          )}
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => setActiveId(conv.id)}
              className={`w-full text-left p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                activeId === conv.id ? "bg-blue-50 border-l-4 border-l-blue-500" : ""
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span>{channelIcon[conv.channel] || "💬"}</span>
                  <span className="text-sm font-medium text-gray-900">
                    {conv.contact_id ? `Contacto` : "Visitante"}
                  </span>
                  {conv.is_ai_handling && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">IA</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {conv.unread_count > 0 && (
                    <span className="bg-blue-600 text-white text-xs rounded-full px-1.5 py-0.5">
                      {conv.unread_count}
                    </span>
                  )}
                  {conv.last_message_at && (
                    <span className="text-xs text-gray-400">{timeAgo(conv.last_message_at)}</span>
                  )}
                </div>
              </div>
              <p className="text-xs text-gray-500 truncate">
                {conv.last_message_preview || "Sin mensajes"}
              </p>
              <span className={`text-xs mt-1 inline-block px-1.5 py-0.5 rounded ${
                conv.status === "active" ? "bg-green-100 text-green-700" :
                conv.status === "pending" ? "bg-yellow-100 text-yellow-700" :
                "bg-gray-100 text-gray-600"
              }`}>
                {conv.status === "active" ? "Activo" :
                 conv.status === "pending" ? "Pendiente" :
                 conv.status === "resolved" ? "Resuelto" : conv.status}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Área de mensajes */}
      <div className="flex flex-1 flex-col bg-gray-50">
        {!activeId ? (
          <div className="flex flex-1 items-center justify-center">
            <div className="text-center">
              <p className="text-5xl mb-4">👈</p>
              <p className="text-gray-500 font-medium">Selecciona una conversación</p>
              <p className="text-sm text-gray-400 mt-1">para ver los mensajes</p>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
              <span>{channelIcon[active?.channel || "web"]}</span>
              <div>
                <p className="font-medium text-sm text-gray-900">
                  {active?.contact_id ? "Contacto" : "Visitante"}
                </p>
                <p className="text-xs text-gray-500">
                  {active?.is_ai_handling ? "🤖 IA respondiendo" : "👤 Agente respondiendo"} · {active?.channel}
                </p>
              </div>
            </div>

            {/* Mensajes */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 && (
                <p className="text-center text-sm text-gray-400 mt-8">Sin mensajes en esta conversación</p>
              )}
              {messages.map((msg) => {
                const isAgent = msg.sender_type === "agent" || msg.sender_type === "ai";
                return (
                  <div key={msg.id} className={`flex ${isAgent ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-xs lg:max-w-md xl:max-w-lg rounded-2xl px-4 py-2.5 ${
                      msg.sender_type === "user"
                        ? "bg-white border border-gray-200 text-gray-900"
                        : msg.sender_type === "ai"
                        ? "bg-purple-600 text-white"
                        : msg.sender_type === "system"
                        ? "bg-gray-100 text-gray-500 text-xs italic"
                        : "bg-blue-600 text-white"
                    }`}>
                      <p className="text-sm">{msg.content}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs ${isAgent ? "text-white/70" : "text-gray-400"}`}>
                          {msg.sender_name}
                        </span>
                        {msg.ai_generated && (
                          <span className="text-xs text-white/70">🤖</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Input */}
            <div className="bg-white border-t border-gray-200 p-4">
              <form onSubmit={sendMessage} className="flex gap-3">
                <input
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Escribe un mensaje como agente..."
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={sending}
                />
                <button
                  type="submit"
                  disabled={sending || !text.trim()}
                  className="bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {sending ? "..." : "Enviar"}
                </button>
              </form>
              <p className="text-xs text-gray-400 mt-2">
                💡 Los mensajes del widget aparecen automáticamente cada 3 segundos
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
