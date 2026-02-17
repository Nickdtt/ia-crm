import React, { useEffect } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const AdminLayout: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/login");
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
    <div className="flex h-screen bg-gradient-to-b from-[#4a6a72] via-[#3a5a60] to-[#2c3e42] overflow-hidden">
      {/* Mobile/Tablet Header */}
      <div className="lg:hidden fixed top-0 w-full bg-white/90 backdrop-blur-sm z-50 px-4 py-3 shadow-md flex justify-between items-center">
        <div className="text-xl font-extrabold text-[#2c3e42] tracking-widest">IA CRM</div>
        <button
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          className="text-[#3a5a60] p-2 hover:bg-slate-100 rounded-lg focus:outline-none"
        >
          {isMobileMenuOpen ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Overlay para fechar menu mobile ao clicar fora */}
      {isMobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar - Fixa em Desktop (LG+), Drawer em Mobile/Tablet */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white/95 shadow-2xl flex flex-col items-center pt-20 lg:pt-8 pb-8 transition-transform duration-300 ease-in-out
          ${isMobileMenuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="flex justify-center w-full mb-8">
          <div className="bg-yellow-400 rounded-full w-20 h-20 flex items-center justify-center shadow-lg border-4 border-white">
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

        <div className="mb-8 text-2xl font-extrabold text-[#2c3e42] tracking-widest hidden lg:block">
          IA CRM
        </div>

        <nav className="w-full flex-1">
          <ul className="space-y-2 px-4">
            <li>
              <Link
                to="/dashboard"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block py-3 px-4 rounded-xl text-[#3a5a60] font-bold hover:bg-yellow-100/50 hover:text-[#2c3e42] transition-colors"
              >
                Dashboard
              </Link>
            </li>
            <li>
              <Link
                to="/dashboard/clients"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block py-3 px-4 rounded-xl text-[#3a5a60] font-bold hover:bg-yellow-100/50 hover:text-[#2c3e42] transition-colors"
              >
                Clientes
              </Link>
            </li>
            <li>
              <Link
                to="/dashboard/appointments"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block py-3 px-4 rounded-xl text-[#3a5a60] font-bold hover:bg-yellow-100/50 hover:text-[#2c3e42] transition-colors"
              >
                Agendamentos
              </Link>
            </li>
          </ul>
        </nav>

        {/* User info / Logout placeholder */}
        <div className="mt-auto px-6 w-full opacity-60 text-xs text-center text-[#3a5a60]">
          <p>Logado como Admin</p>
        </div>
      </aside>

      {/* Conteúdo principal */}
      <main className="flex-1 flex flex-col items-center justify-start lg:justify-center p-4 lg:p-8 pt-20 lg:pt-8 overflow-y-auto w-full">
        <Outlet />
      </main>
    </div>
  );
};

export default AdminLayout;