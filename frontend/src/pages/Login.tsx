import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { login, isLoggingIn } = useAuth();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const result = await login(email, password);

    if (result.success) {
      navigate("/dashboard");
    } else {
      setError(result.error || "Credenciais inválidas. Tente novamente.");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[#4a6a72] via-[#3a5a60] to-[#2c3e42]">
      <div className="w-full max-w-md p-8 rounded-2xl shadow-2xl bg-white/80 relative flex flex-col items-center">
        <div className="absolute -top-8 flex justify-center w-full">
          <div className="bg-yellow-400 rounded-full w-16 h-16 flex items-center justify-center shadow-lg border-4 border-white">
            {/* Ícone de âncora estilizado */}
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
                d="M12 2v14m0 0c-3.866 0-7-3.134-7-7m7 7c3.866 0 7-3.134 7-7M5 21h14"
              />
            </svg>
          </div>
        </div>
        <h1 className="mt-10 text-3xl font-extrabold text-[#2c3e42] tracking-widest text-center">
          BEM-VINDO
        </h1>
        <p className="text-center text-[#3a5a60] mb-4">
          Acesse sua conta para continuar
        </p>
        {error && <p className="text-red-500 text-center">{error}</p>}
        <form onSubmit={handleLogin} className="space-y-4 w-full mt-2">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-[#3a5a60]"
            >
              Email
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 mt-1 rounded-lg bg-white/70 border border-[#bfcfd4] focus:ring-2 focus:ring-yellow-400 focus:outline-none placeholder:text-[#7a9297]"
              placeholder="Digite seu email"
              required
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-[#3a5a60]"
            >
              Senha
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 mt-1 rounded-lg bg-white/70 border border-[#bfcfd4] focus:ring-2 focus:ring-yellow-400 focus:outline-none placeholder:text-[#7a9297]"
              placeholder="Digite sua senha"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoggingIn}
            className="w-full py-2 mt-2 rounded-lg bg-yellow-400 text-[#2c3e42] font-bold uppercase tracking-wider shadow-md hover:bg-yellow-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoggingIn ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <button
          onClick={() => navigate("/")}
          className="mt-4 text-[#3a5a60]/60 hover:text-[#3a5a60] text-sm transition-colors"
        >
          ← Voltar à página inicial
        </button>
      </div>
    </div>
  );
};

export default LoginPage;