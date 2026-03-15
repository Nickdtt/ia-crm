import React, { useState, useEffect } from "react";
import type { ClientCreateData, Client } from "../hooks/useClients";

interface ClientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: ClientCreateData) => Promise<void>;
  client?: Client | null;
}

const ClientModal: React.FC<ClientModalProps> = ({ isOpen, onClose, onSave, client }) => {
  const [loading, setLoading] = useState(false);
  
  const [formData, setFormData] = useState<ClientCreateData>({
    first_name: "",
    last_name: "",
    phone: "",
    email: "",
    company_name: "",
    segment: "clinica_medica",
    monthly_budget: 0,
    main_marketing_problem: "",
    notes: ""
  });

  // Preenche o formulário quando client for passado (modo edição)
  useEffect(() => {
    if (client) {
      setFormData({
        first_name: client.first_name,
        last_name: client.last_name,
        phone: client.phone || "",
        email: client.email || "",
        company_name: client.company_name || "",
        segment: client.segment || "clinica_medica",
        monthly_budget: client.monthly_budget || 0,
        main_marketing_problem: client.main_marketing_problem || "",
        notes: ""
      });
    } else {
      // Reset form quando não há client (modo criação)
      setFormData({
        first_name: "",
        last_name: "",
        phone: "",
        email: "",
        company_name: "",
        segment: "clinica_medica",
        monthly_budget: 0,
        main_marketing_problem: "",
        notes: ""
      });
    }
  }, [client, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Sanitiza os dados antes de enviar
    const dataToSend = {
      ...formData,
      email: formData.email?.trim() === "" ? undefined : formData.email,
      company_name: formData.company_name?.trim() === "" ? undefined : formData.company_name,
      notes: formData.notes?.trim() === "" ? undefined : formData.notes,
    };

    try {
      await onSave(dataToSend);
      onClose();
      // Reset form
      setFormData({
        first_name: "",
        last_name: "",
        phone: "",
        email: "",
        company_name: "",
        segment: "clinica_medica",
        monthly_budget: 0,
        main_marketing_problem: "",
        notes: ""
      });
    } catch (error: any) {
      console.error("Erro ao salvar:", error);
      
      // Tenta extrair mensagem de erro detalhada da API (FastAPI retorna detail em 422)
      let errorMessage = "Erro ao salvar cliente. Verifique os dados.";
      if (error.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          // Formata erros de validação do Pydantic
          errorMessage = error.response.data.detail
            .map((err: any) => `${err.loc[1]}: ${err.msg}`)
            .join("\n");
        } else {
          errorMessage = error.response.data.detail;
        }
      }
      
      alert(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl my-8 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center sticky top-0">
          <h3 className="text-lg font-bold text-slate-800">{client ? "Editar Cliente" : "Novo Cliente"}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Nome*</label>
              <input 
                type="text"
                required
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.first_name}
                onChange={e => setFormData({...formData, first_name: e.target.value})}
                placeholder="Ex: João"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Sobrenome*</label>
              <input 
                type="text"
                required
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.last_name}
                onChange={e => setFormData({...formData, last_name: e.target.value})}
                placeholder="Ex: Silva"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Telefone (WhatsApp)*</label>
              <input 
                type="tel"
                required
                minLength={11}
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.phone}
                onChange={e => setFormData({...formData, phone: e.target.value})}
                placeholder="Ex: 5511999887766"
              />
              <p className="text-[10px] text-slate-400 mt-1">Mínimo 11 dígitos (DDD + Número).</p>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Email</label>
              <input 
                type="email"
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.email}
                onChange={e => setFormData({...formData, email: e.target.value})}
                placeholder="Ex: joao@email.com"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Empresa</label>
              <input 
                type="text"
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.company_name}
                onChange={e => setFormData({...formData, company_name: e.target.value})}
                placeholder="Ex: Clínica Silva"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Segmento*</label>
              <select 
                required
                className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.segment}
                onChange={e => setFormData({...formData, segment: e.target.value})}
              >
                <optgroup label="Clínicas">
                  <option value="clinica_medica">Clínica Médica</option>
                  <option value="clinica_odontologica">Clínica Odontológica</option>
                  <option value="clinica_estetica">Clínica Estética</option>
                  <option value="laboratorio">Laboratório</option>
                  <option value="hospital">Hospital</option>
                </optgroup>
                <optgroup label="Autônomos">
                  <option value="medico_autonomo">Médico Autônomo</option>
                  <option value="dentista_autonomo">Dentista Autônomo</option>
                  <option value="psicologo">Psicólogo</option>
                  <option value="fisioterapeuta">Fisioterapeuta</option>
                  <option value="nutricionista">Nutricionista</option>
                </optgroup>
                <optgroup label="Outros">
                  <option value="farmacia">Farmácia</option>
                  <option value="ecommerce_saude">E-commerce Saúde</option>
                  <option value="equipamentos_medicos">Equipamentos Médicos</option>
                  <option value="plano_saude">Plano de Saúde</option>
                  <option value="outro">Outro</option>
                </optgroup>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Orçamento Mensal (R$)*</label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-slate-500 text-sm">R$</span>
              <input 
                type="number"
                required
                min="1000"
                step="100.00"
                className="w-full rounded-lg border-slate-200 text-sm pl-9 focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                value={formData.monthly_budget || ""}
                onChange={e => setFormData({...formData, monthly_budget: Number(e.target.value)})}
                placeholder="0,00"
              />
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Mínimo R$ 1.000,00 para qualificação.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Principal Problema de Marketing*</label>
            <textarea 
              required
              minLength={10}
              rows={2}
              className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              value={formData.main_marketing_problem}
              onChange={e => setFormData({...formData, main_marketing_problem: e.target.value})}
              placeholder="Descreva o principal desafio atual..."
            />
            <p className="text-[10px] text-slate-400 mt-1">Mínimo 10 caracteres.</p>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Observações</label>
            <textarea 
              rows={2}
              className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              value={formData.notes}
              onChange={e => setFormData({...formData, notes: e.target.value})}
              placeholder="Detalhes adicionais..."
            />
          </div>

          <div className="pt-4 flex gap-3 border-t border-slate-100 mt-2">
            <button 
              type="button" 
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl font-medium hover:bg-slate-50 transition-colors"
            >
              Cancelar
            </button>
            <button 
              type="submit" 
              disabled={loading}
              className="flex-1 px-4 py-2 bg-emerald-500 text-white rounded-xl font-bold hover:bg-emerald-600 transition-colors shadow-lg shadow-emerald-200 disabled:opacity-70 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Salvando...
                </>
              ) : (
                client ? "Salvar Alterações" : "Cadastrar Cliente"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClientModal;
