import React from "react";
import { useClients } from "../hooks/useClients";
import { useAppointments } from "../hooks/useAppointments";

const DashboardPage: React.FC = () => {
  const { data: clients = [], isLoading: loadingClients } = useClients();
  const { data: appointments = [], isLoading: loadingAppts } = useAppointments();

  const isLoading = loadingClients || loadingAppts;

  const totalClients = clients.length;
  const totalAppointments = appointments.length;
  const pending = appointments.filter((a) => a.status === "pending").length;
  const confirmed = appointments.filter((a) => a.status === "confirmed").length;
  const completed = appointments.filter((a) => a.status === "completed").length;
  const cancelled = appointments.filter((a) => a.status === "cancelled").length;

  // Segmentos mais frequentes
  const segmentCounts: Record<string, number> = {};
  clients.forEach((c) => {
    const seg = c.segment || "outro";
    segmentCounts[seg] = (segmentCounts[seg] || 0) + 1;
  });
  const topSegments = Object.entries(segmentCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  const segmentLabels: Record<string, string> = {
    clinica_odontologica: "Odontologia",
    clinica_medica: "Clínica Médica",
    clinica_estetica: "Estética",
    medico_autonomo: "Médico Autônomo",
    psicologo: "Psicologia",
    farmacia: "Farmácia",
    laboratorio: "Laboratório",
    nutricionista: "Nutrição",
    fisioterapeuta: "Fisioterapia",
    ecommerce_saude: "E-commerce Saúde",
    outro: "Outro",
  };

  // Próximos agendamentos
  const now = new Date();
  const upcoming = appointments
    .filter((a) => new Date(a.scheduled_at) > now && a.status !== "cancelled")
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime())
    .slice(0, 5);

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  };
  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  };

  const getClientName = (clientId: string) => {
    const client = clients.find((c) => c.id === clientId);
    return client ? `${client.first_name} ${client.last_name}` : "—";
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-4xl flex items-center justify-center py-20">
        <div className="animate-pulse text-[#3a5a60] text-lg">Carregando dashboard...</div>
      </div>
    );
  }

  return (
    <div className="w-full h-full max-w-4xl space-y-6 overflow-auto">
      {/* Header */}
      <div className="bg-white/80 rounded-2xl shadow-2xl p-8">
        <h1 className="text-3xl font-extrabold text-[#2c3e42] tracking-widest mb-1">Dashboard</h1>
        <p className="text-[#3a5a60]">Visão geral do CRM — dados em tempo real</p>
      </div>

      {/* Cards principais */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/80 rounded-xl p-5 shadow text-center">
          <span className="text-4xl font-bold text-[#3a5a60]">{totalClients}</span>
          <p className="text-[#2c3e42] mt-1 font-semibold text-sm">Clientes</p>
        </div>
        <div className="bg-white/80 rounded-xl p-5 shadow text-center">
          <span className="text-4xl font-bold text-[#3a5a60]">{totalAppointments}</span>
          <p className="text-[#2c3e42] mt-1 font-semibold text-sm">Agendamentos</p>
        </div>
        <div className="bg-amber-50 rounded-xl p-5 shadow text-center">
          <span className="text-4xl font-bold text-amber-600">{pending}</span>
          <p className="text-amber-800 mt-1 font-semibold text-sm">Pendentes</p>
        </div>
        <div className="bg-emerald-50 rounded-xl p-5 shadow text-center">
          <span className="text-4xl font-bold text-emerald-600">{confirmed}</span>
          <p className="text-emerald-800 mt-1 font-semibold text-sm">Confirmados</p>
        </div>
      </div>

      {/* Linha 2: Status + Segmentos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Status breakdown */}
        <div className="bg-white/80 rounded-xl p-6 shadow">
          <h2 className="text-lg font-bold text-[#2c3e42] mb-4">Status dos Agendamentos</h2>
          <div className="space-y-3">
            {[
              { label: "Pendentes", value: pending, color: "bg-amber-400", total: totalAppointments },
              { label: "Confirmados", value: confirmed, color: "bg-emerald-400", total: totalAppointments },
              { label: "Concluídos", value: completed, color: "bg-blue-400", total: totalAppointments },
              { label: "Cancelados", value: cancelled, color: "bg-rose-400", total: totalAppointments },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-[#3a5a60] font-medium">{item.label}</span>
                  <span className="text-[#2c3e42] font-bold">{item.value}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`${item.color} h-2 rounded-full transition-all duration-500`}
                    style={{ width: item.total ? `${(item.value / item.total) * 100}%` : "0%" }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Segmentos */}
        <div className="bg-white/80 rounded-xl p-6 shadow">
          <h2 className="text-lg font-bold text-[#2c3e42] mb-4">Segmentos de Clientes</h2>
          <div className="space-y-3">
            {topSegments.map(([seg, count]) => (
              <div key={seg} className="flex items-center justify-between">
                <span className="text-sm text-[#3a5a60]">{segmentLabels[seg] || seg}</span>
                <span className="bg-yellow-100 text-[#2c3e42] text-xs font-bold px-3 py-1 rounded-full">
                  {count}
                </span>
              </div>
            ))}
            {topSegments.length === 0 && (
              <p className="text-sm text-gray-400 italic">Nenhum cliente cadastrado</p>
            )}
          </div>
        </div>
      </div>

      {/* Próximos agendamentos */}
      <div className="bg-white/80 rounded-xl p-6 shadow">
        <h2 className="text-lg font-bold text-[#2c3e42] mb-4">Próximos Agendamentos</h2>
        {upcoming.length > 0 ? (
          <div className="space-y-2">
            {upcoming.map((apt) => (
              <div
                key={apt.id}
                className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      apt.status === "confirmed" ? "bg-emerald-400" : "bg-amber-400"
                    }`}
                  />
                  <div>
                    <p className="text-sm font-semibold text-[#2c3e42]">{getClientName(apt.client_id)}</p>
                    <p className="text-xs text-[#3a5a60]">{apt.meeting_type || "Reunião"}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-[#2c3e42]">{formatDate(apt.scheduled_at)}</p>
                  <p className="text-xs text-[#3a5a60]">{formatTime(apt.scheduled_at)}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">Nenhum agendamento futuro</p>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;