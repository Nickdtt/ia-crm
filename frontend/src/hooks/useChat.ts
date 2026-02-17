/**
 * useChat - Hook para comunicação com o agente de IA via REST.
 * 
 * Gerencia sessão, histórico de mensagens e estado de loading.
 * Cada visitante recebe um session_id único (UUID) persistido em sessionStorage.
 */

import { useState, useCallback, useRef } from "react";
import api from "../services/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  conversationMode: string | null;
}

function getOrCreateSessionId(): string {
  const key = "chat_session_id";
  let sessionId = sessionStorage.getItem(key);
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(key, sessionId);
  }
  return sessionId;
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
    conversationMode: null,
  });

  const sessionIdRef = useRef(getOrCreateSessionId());

  const sendMessage = useCallback(async (message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;

    // Adicionar mensagem do usuário imediatamente
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      timestamp: new Date(),
    };

    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      const response = await api.post("/api/v1/chat/message", {
        session_id: sessionIdRef.current,
        message: trimmed,
      });

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.data.response,
        timestamp: new Date(),
      };

      setState((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        isLoading: false,
        conversationMode: response.data.conversation_mode,
      }));
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        "Erro ao se comunicar com o agente. Tente novamente.";

      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMsg,
      }));
    }
  }, []);

  const resetChat = useCallback(async () => {
    try {
      await api.post("/api/v1/chat/reset", {
        session_id: sessionIdRef.current,
      });
    } catch {
      // Ignora erro no reset — vamos limpar local de qualquer forma
    }

    // Gerar novo session_id
    const newSessionId = crypto.randomUUID();
    sessionStorage.setItem("chat_session_id", newSessionId);
    sessionIdRef.current = newSessionId;

    setState({
      messages: [],
      isLoading: false,
      error: null,
      conversationMode: null,
    });
  }, []);

  return {
    messages: state.messages,
    isLoading: state.isLoading,
    error: state.error,
    conversationMode: state.conversationMode,
    sendMessage,
    resetChat,
  };
}
