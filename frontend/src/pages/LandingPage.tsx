import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  const handleDemoLogin = async () => {
    const demoEmail = import.meta.env.VITE_DEMO_EMAIL;
    const demoPassword = import.meta.env.VITE_DEMO_PASSWORD;

    if (!demoEmail || !demoPassword) {
      navigate("/login");
      return;
    }

    setIsDemoLoading(true);
    const result = await login(demoEmail, demoPassword);
    if (result.success) {
      navigate("/dashboard");
    } else {
      navigate("/login");
    }
    setIsDemoLoading(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#4a6a72] via-[#3a5a60] to-[#2c3e42] flex flex-col">
      {/* Header */}
      <header className="px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-yellow-400 rounded-full w-8 h-8 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-4 w-4 text-[#3a5a60]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 2v14m0 0c-3.866 0-7-3.134-7-7m7 7c3.866 0 7-3.134 7-7M5 21h14"
                />
              </svg>
            </div>
            <span className="text-white font-bold text-lg">AtenteAI</span>
          </div>
          <button
            onClick={() => navigate("/login")}
            className="text-white/60 hover:text-white text-sm px-4 py-2 rounded-lg hover:bg-white/10 transition-colors"
          >
            Login Admin →
          </button>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex items-center justify-center px-6">
        <div className="max-w-3xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-1.5 mb-6 border border-white/10">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-white/80 text-sm">Projeto de Portfólio — Demo Interativa</span>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-6xl font-extrabold text-white mb-4 tracking-tight">
            Atente<span className="text-yellow-400">AI</span>
          </h1>
          <p className="text-xl md:text-2xl text-white/80 font-light mb-3">
            CRM com IA Conversacional
          </p>
          <p className="text-white/50 text-base md:text-lg max-w-xl mx-auto mb-10 leading-relaxed">
            Sistema de qualificação de leads e agendamento automatizado via chat
            com inteligência artificial. Converse com o agente e veja os dados
            refletidos no dashboard em tempo real.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-12">
            <button
              onClick={() => navigate("/chat")}
              className="w-full sm:w-auto flex items-center justify-center gap-3 bg-yellow-400 hover:bg-yellow-300 text-[#2c3e42] font-bold rounded-xl px-8 py-4 text-lg transition-all shadow-lg hover:shadow-xl hover:-translate-y-0.5"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
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
              Testar o Chat
            </button>

            <button
              onClick={handleDemoLogin}
              disabled={isDemoLoading}
              className="w-full sm:w-auto flex items-center justify-center gap-3 bg-white/10 hover:bg-white/20 text-white font-bold rounded-xl px-8 py-4 text-lg border border-white/20 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-wait"
            >
              {isDemoLoading ? (
                <>
                  <svg
                    className="animate-spin h-5 w-5"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    ></path>
                  </svg>
                  Entrando...
                </>
              ) : (
                <>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  Acessar Dashboard
                </>
              )}
            </button>
          </div>

          {/* Tech Stack */}
          <div className="flex flex-wrap items-center justify-center gap-3 mb-8">
            {[
              "LangGraph",
              "RAG",
              "FastAPI",
              "React",
              "PostgreSQL",
              "LangChain",
              "Tailwind CSS",
              "TypeScript",
            ].map((tech) => (
              <span
                key={tech}
                className="bg-white/5 text-white/60 text-xs px-3 py-1.5 rounded-full border border-white/10"
              >
                {tech}
              </span>
            ))}
          </div>

          {/* How it works */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-2xl mx-auto">
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="text-yellow-400 text-2xl mb-2">💬</div>
              <h3 className="text-white font-semibold text-sm mb-1">1. Converse</h3>
              <p className="text-white/50 text-xs">
                O agente qualifica leads e agenda reuniões automaticamente
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="text-yellow-400 text-2xl mb-2">🤖</div>
              <h3 className="text-white font-semibold text-sm mb-1">2. IA Processa</h3>
              <p className="text-white/50 text-xs">
                LangGraph orquestra múltiplos agentes com RAG para respostas precisas
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4 border border-white/10">
              <div className="text-yellow-400 text-2xl mb-2">📊</div>
              <h3 className="text-white font-semibold text-sm mb-1">3. Dashboard</h3>
              <p className="text-white/50 text-xs">
                Dados refletidos em tempo real no painel administrativo
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-center gap-4 text-white/30 text-xs">
          <span>Desenvolvido por Nícolas Figueiredo</span>
          <span>·</span>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white/60 transition-colors"
          >
            GitHub ↗
          </a>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
