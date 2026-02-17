import React, { useState, useEffect } from "react";
import { useClients } from "../hooks/useClients";

interface AppointmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialDate: Date | null;
  onSave: (data: any) => Promise<void>;
}

const AppointmentModal: React.FC<AppointmentModalProps> = ({ isOpen, onClose, initialDate, onSave }) => {
  const [loading, setLoading] = useState(false);
  const { data: clients = [], refetch: refetchClients } = useClients();

  const [formData, setFormData] = useState({
    client_id: "",
    date: "",
    time: "",
    duration_minutes: 60,
    meeting_type: "Reunião Comercial",
    notes: ""
  });

  // Recarregar clientes ao abrir modal
  useEffect(() => {
    if (isOpen) {
      refetchClients();
    }
  }, [isOpen, refetchClients]);

  // Atualizar form quando initialDate muda
  useEffect(() => {
    if (initialDate) {
      setFormData(prev => ({
        ...prev,
        date: initialDate.toISOString().split('T')[0],
        time: initialDate.toTimeString().slice(0, 5)
      }));
    }
  }, [initialDate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Combina data e hora para criar o ISO string
      const scheduledAt = new Date(`${formData.date}T${formData.time}:00`);

      await onSave({
        client_id: formData.client_id,
        scheduled_at: scheduledAt.toISOString(),
        duration_minutes: Number(formData.duration_minutes),
        meeting_type: formData.meeting_type,
        notes: formData.notes
      });
      onClose();
    } catch (error) {
      console.error(error);
      alert("Erro ao salvar agendamento");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <h3 className="text-lg font-bold text-slate-800">Novo Agendamento</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Cliente</label>
            <select
              required
              className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              value={formData.client_id}
              onChange={e => setFormData({ ...formData, client_id: e.target.value })}
            >
              <option value="">Selecione um cliente...</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.first_name} {client.last_name} {client.company_name ? `(${client.company_name})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Data</label>
              <input
                type="date"
                required
                className="w-full rounded-lg border-slate-200 text-sm"
                value={formData.date}
                onChange={e => setFormData({ ...formData, date: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Hora</label>
              <input
                type="time"
                required
                className="w-full rounded-lg border-slate-200 text-sm"
                value={formData.time}
                onChange={e => setFormData({ ...formData, time: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Duração (min)</label>
              <select
                className="w-full rounded-lg border-slate-200 text-sm"
                value={formData.duration_minutes}
                onChange={e => setFormData({ ...formData, duration_minutes: Number(e.target.value) })}
              >
                <option value={30}>30 min</option>
                <option value={45}>45 min</option>
                <option value={60}>1 hora</option>
                <option value={90}>1h 30min</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Tipo</label>
              <input
                type="text"
                className="w-full rounded-lg border-slate-200 text-sm"
                value={formData.meeting_type}
                onChange={e => setFormData({ ...formData, meeting_type: e.target.value })}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Observações</label>
            <textarea
              rows={3}
              className="w-full rounded-lg border-slate-200 text-sm"
              value={formData.notes}
              onChange={e => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Detalhes sobre a reunião..."
            />
          </div>

          <div className="pt-4 flex gap-3">
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
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-colors shadow-lg shadow-blue-200 disabled:opacity-70 flex items-center justify-center gap-2"
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
                "Agendar"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AppointmentModal;
