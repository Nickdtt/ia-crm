import React, { useEffect, useState } from "react";
import { useClients, useCreateClient, useUpdateClient, useDeleteClient, type Client } from "../hooks/useClients";
import ClientModal from "../components/ClientModal";

/**
 * Página de Clientes
 * Layout visual inspirado no dashboard, integrado com API.
 */
const ClientsPage: React.FC = () => {
  const { data: clients = [], isLoading, error, refetch } = useClients();
  const createClient = useCreateClient();
  const updateClient = useUpdateClient();
  const deleteClient = useDeleteClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | null>(null);

  // 🔄 FORÇA refetch ao montar o componente
  useEffect(() => {
    console.log("🔄 ClientsPage montada - forçando refetch...");
    refetch();
  }, [refetch]);

  const handleSaveClient = async (data: any) => {
    if (editingClient) {
      // Modo edição
      await updateClient.mutateAsync({ id: editingClient.id, data });
    } else {
      // Modo criação
      await createClient.mutateAsync(data);
    }
    setEditingClient(null);
  };

  const handleEditClick = (client: Client) => {
    setEditingClient(client);
    setIsModalOpen(true);
  };

  const handleDeleteClick = async (client: Client) => {
    if (window.confirm(`Tem certeza que deseja excluir ${client.first_name} ${client.last_name}?`)) {
      try {
        await deleteClient.mutateAsync(client.id);
      } catch (error) {
        console.error("Erro ao deletar cliente:", error);
        alert("Erro ao excluir cliente. Tente novamente.");
      }
    }
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingClient(null);
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-7xl mx-auto bg-white rounded-3xl shadow-xl border border-slate-100 p-6 flex items-center justify-center h-[calc(100vh-60px)]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p className="text-slate-600 font-medium">Carregando clientes...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-7xl mx-auto bg-white rounded-3xl shadow-xl border border-slate-100 p-6 flex items-center justify-center h-[calc(100vh-60px)]">
        <div className="text-center">
          <p className="text-rose-600 font-semibold mb-2">❌ Erro ao carregar clientes</p>
          <p className="text-slate-500 text-sm">{error.message}</p>
          <button
            onClick={() => refetch()}
            className="mt-4 bg-emerald-500 text-white font-bold px-4 py-2 rounded-lg hover:bg-emerald-600 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  console.log("📊 ClientsPage - Total de clientes:", clients.length, clients);

  return (
    <div className="w-full max-w-7xl mx-auto bg-white rounded-3xl shadow-xl border border-slate-100 p-6 flex flex-col h-[calc(100vh-60px)] overflow-hidden font-sans">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-800 tracking-tight">Clientes</h1>
          <p className="text-slate-500 mt-1 font-medium">Gerencie sua base de clientes e leads.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-emerald-500 text-white font-bold px-6 py-2.5 rounded-xl shadow-lg shadow-emerald-200 hover:bg-emerald-600 hover:scale-105 transition-all duration-200 flex items-center gap-2"
        >
          <span>+</span> Novo Cliente
        </button>
      </div>

      <div className="flex-1 overflow-auto rounded-xl border border-slate-200 shadow-inner bg-slate-50/50">
        {/* Mobile View: Cards */}
        <div className="md:hidden space-y-4 p-4">
          {clients.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-slate-400 font-medium">Nenhum cliente cadastrado ainda</p>
            </div>
          ) : (
            clients.map((client) => (
              <div key={client.id} className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex flex-col gap-3">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">{client.first_name} {client.last_name}</h3>
                    <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-100">
                      {client.segment || "Geral"}
                    </span>
                  </div>
                  {client.monthly_budget && (
                    <span className="font-semibold text-slate-700 text-sm">R$ {client.monthly_budget}</span>
                  )}
                </div>

                <div className="space-y-1 text-sm text-slate-600">
                  <div className="flex items-center gap-2">
                    <span>📞</span> {client.phone || "—"}
                  </div>
                  <div className="flex items-center gap-2">
                    <span>📧</span> <span className="truncate">{client.email || "—"}</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span>📅</span> {client.created_at ? new Date(client.created_at).toLocaleDateString("pt-BR") : "—"}
                  </div>
                </div>

                <div className="flex gap-2 mt-2 pt-3 border-t border-slate-50">
                  <button
                    onClick={() => handleEditClick(client)}
                    className="flex-1 py-2 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg font-semibold text-sm transition-colors"
                  >
                    Editar
                  </button>
                  <button
                    onClick={() => handleDeleteClick(client)}
                    className="flex-1 py-2 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-lg font-semibold text-sm transition-colors"
                  >
                    Excluir
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Desktop View: Table */}
        <table className="hidden md:table min-w-full border-separate border-spacing-0 bg-white">
          <thead className="bg-slate-50 sticky top-0 z-10">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Nome</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Telefone</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Email</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Segmento</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Orçamento</th>
              <th className="px-6 py-4 text-left text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Cadastro</th>
              <th className="px-6 py-4 text-right text-xs font-bold text-slate-500 uppercase tracking-wider border-b border-slate-200">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {clients.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center">
                  <p className="text-slate-400 font-medium">Nenhum cliente cadastrado ainda</p>
                </td>
              </tr>
            ) : (
              clients.map((client) => (
                <tr key={client.id} className="hover:bg-slate-50/80 transition-colors duration-150 group">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-slate-700">
                    {client.first_name} {client.last_name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 font-mono">
                    {client.phone || "—"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                    {client.email || "—"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-50 text-blue-700 border border-blue-100">
                      {client.segment || "Geral"}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700 font-medium">
                    {client.monthly_budget ? `R$ ${client.monthly_budget}` : "—"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                    {client.created_at ? new Date(client.created_at).toLocaleDateString("pt-BR") : "—"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <button
                      onClick={() => handleEditClick(client)}
                      className="text-blue-600 hover:text-blue-800 font-semibold mr-3 transition-colors"
                      title="Editar cliente"
                    >
                      ✏️ Editar
                    </button>
                    <button
                      onClick={() => handleDeleteClick(client)}
                      className="text-rose-600 hover:text-rose-800 font-semibold transition-colors"
                      title="Excluir cliente"
                    >
                      🗑️ Excluir
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ClientModal
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onSave={handleSaveClient}
        client={editingClient}
      />
    </div>
  );
};

export default ClientsPage;
