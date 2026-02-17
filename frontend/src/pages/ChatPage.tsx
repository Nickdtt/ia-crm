import React, { useState, useRef, useEffect } from "react";
import { useChat, type ChatMessage } from "../hooks/useChat";
import { useNavigate } from "react-router-dom";

const ChatPage: React.FC = () => {
  const { messages, isLoading, error, sendMessage, resetChat } = useChat();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  // Auto-scroll para última mensagem
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus no input ao montar
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput("");
  };

  const handleReset = () => {
    resetChat();
    inputRef.current?.focus();
  };

  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#4a6a72] via-[#3a5a60] to-[#2c3e42] flex flex-col">
      {/* Header */}
      <header className="bg-[#2c3e42]/80 backdrop-blur-sm border-b border-white/10 px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-yellow-400 rounded-full w-10 h-10 flex items-center justify-center shadow-md">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-[#3a5a60]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <div>
              <h1 className="text-white font-bold text-lg">AtenteAI</h1>
              <p className="text-white/60 text-xs">Assistente Virtual</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleReset}
              className="text-white/60 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
              title="Nova conversa"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4 inline mr-1"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
              Nova conversa
            </button>
            <button
              onClick={() => navigate("/")}
              className="text-white/60 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition-colors"
            >
              ← Voltar
            </button>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Mensagem de boas-vindas se vazio */}
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-16">
              <div className="bg-yellow-400 rounded-full w-16 h-16 flex items-center justify-center shadow-lg mx-auto mb-4">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-8 w-8 text-[#3a5a60]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
              </div>
              <h2 className="text-white text-xl font-semibold mb-2">
                Converse com a AtenteAI
              </h2>
              <p className="text-white/60 text-sm max-w-md mx-auto">
                Nosso assistente virtual pode tirar suas dúvidas sobre marketing
                digital e agendar uma consultoria gratuita. Envie uma mensagem
                para começar!
              </p>
            </div>
          )}

          {/* Mensagens */}
          {messages.map((msg: ChatMessage) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-md ${
                  msg.role === "user"
                    ? "bg-yellow-400 text-[#2c3e42] rounded-br-sm"
                    : "bg-white/90 text-[#2c3e42] rounded-bl-sm"
                }`}
              >
                {msg.role === "assistant" && (
                  <p className="text-xs font-semibold text-[#3a5a60] mb-1">
                    AtenteAI
                  </p>
                )}
                <p className="text-sm whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </p>
                <p
                  className={`text-xs mt-1 ${
                    msg.role === "user" ? "text-[#2c3e42]/50" : "text-[#3a5a60]/50"
                  }`}
                >
                  {formatTime(msg.timestamp)}
                </p>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white/90 rounded-2xl rounded-bl-sm px-4 py-3 shadow-md">
                <p className="text-xs font-semibold text-[#3a5a60] mb-1">
                  AtenteAI
                </p>
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 bg-[#3a5a60] rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-[#3a5a60] rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-[#3a5a60] rounded-full animate-bounce"></div>
                </div>
              </div>
            </div>
          )}

          {/* Erro */}
          {error && (
            <div className="flex justify-center">
              <div className="bg-red-500/20 text-red-200 rounded-lg px-4 py-2 text-sm">
                {error}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-[#2c3e42]/80 backdrop-blur-sm border-t border-white/10 px-4 py-3">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto flex items-center gap-2"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite sua mensagem..."
            disabled={isLoading}
            className="flex-1 bg-white/10 text-white placeholder-white/40 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400/50 border border-white/10 disabled:opacity-50"
            maxLength={2000}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-yellow-400 hover:bg-yellow-300 disabled:bg-yellow-400/50 text-[#2c3e42] font-semibold rounded-xl px-5 py-3 text-sm transition-colors disabled:cursor-not-allowed"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </form>
      </footer>
    </div>
  );
};

export default ChatPage;
