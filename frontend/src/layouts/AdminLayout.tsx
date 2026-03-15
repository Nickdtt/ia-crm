import React, { useEffect } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const AdminLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/");
    }
  }, [isLoading, isAuthenticated, navigate]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-100">
        <p className="text-slate-500">Carregando...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen bg-gradient-to-b from-[#4a6a72] via-[#3a5a60] to-[#2c3e42]">
      {/* Sidebar estilizada */}
      <aside className="w-64 bg-white/80 shadow-2xl flex flex-col items-center pt-8 pb-8 relative">
        <div className="flex justify-center w-full">
          <div className="bg-yellow-400 rounded-full w-20 h-20 flex items-center justify-center shadow-lg border-4 border-white">
            {/* Ícone de âncora */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-10 w-10 text-[#3a5a60]"
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
        <div className="mt-8 mb-8 text-2xl font-extrabold text-[#2c3e42] tracking-widest">
          IA CRM
        </div>
        <nav className="w-full flex-1">
          <ul className="space-y-2 px-4">
            <li>
              <Link
                to="/dashboard"
                className="block py-2 px-4 rounded-lg text-[#3a5a60] font-semibold hover:bg-yellow-100 transition"
              >
                Dashboard
              </Link>
            </li>
            <li>
              <Link
                to="/dashboard/clients"
                className="block py-2 px-4 rounded-lg text-[#3a5a60] font-semibold hover:bg-yellow-100 transition"
              >
                Clientes
              </Link>
            </li>
            <li>
              <Link
                to="/dashboard/appointments"
                className="block py-2 px-4 rounded-lg text-[#3a5a60] font-semibold hover:bg-yellow-100 transition"
              >
                Agendamentos
              </Link>
            </li>
          </ul>
        </nav>
      </aside>
      {/* Conteúdo principal */}
      <main className="flex-1 flex flex-col items-center justify-center p-8">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;