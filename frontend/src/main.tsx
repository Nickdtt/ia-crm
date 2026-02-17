import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./providers/AuthProvider";
import AdminLayout from "./layouts/AdminLayout";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/Login";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/Dashboard";
import ClientsPage from "./pages/Clients";
import AppointmentsPage from "./pages/Appointments";
import "./index.css";

// Criação do QueryClient com configurações otimizadas
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 0, // Dados sempre considerados "stale" - força refetch
      gcTime: 1000 * 60 * 30, // 30 minutos - tempo que dados ficam em cache
      refetchOnWindowFocus: true, // Recarrega ao voltar para a aba
      refetchOnMount: true, // Sempre recarrega ao montar componente
      refetchOnReconnect: true, // Recarrega ao reconectar internet
      retry: 1, // Tenta novamente 1 vez se falhar
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {/* Provedor do TanStack Query para gerenciar o estado global das queries */}
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/dashboard" element={<AdminLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="clients" element={<ClientsPage />} />
              <Route path="appointments" element={<AppointmentsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);