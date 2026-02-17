import React, { useState, useMemo, useEffect } from "react";
import { useAppointments, useCreateAppointment, useCancelAppointment } from "../hooks/useAppointments";
import type { Appointment, AppointmentCreateData } from "../hooks/useAppointments";
import AppointmentModal from "../components/AppointmentModal";

const hours = Array.from({ length: 14 }, (_, i) => `${String(i + 8).padStart(2, "0")}:00`);

// Função para atribuir cor baseada no status
const getColorByStatus = (status: string): string => {
  const colors: Record<string, string> = {
    confirmed: "bg-emerald-500 shadow-emerald-200",
    pending: "bg-amber-500 shadow-amber-200",
    completed: "bg-blue-500 shadow-blue-200",
    cancelled: "bg-rose-500 shadow-rose-200",
  };
  return colors[status.toLowerCase()] || "bg-slate-500 shadow-slate-200";
};

const getMonday = (d: Date) => {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1); // Ajusta para segunda-feira
  return new Date(date.setDate(diff));
};

const AppointmentsPage: React.FC = () => {
  const { data: appointments, isLoading, error, refetch } = useAppointments();
  const createAppointment = useCreateAppointment();
  const cancelAppointment = useCancelAppointment();

  const [startDate, setStartDate] = useState(getMonday(new Date()));
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedSlotDate, setSelectedSlotDate] = useState<Date | null>(null);
  const [cancellingAppointment, setCancellingAppointment] = useState<Appointment | null>(null);
  const [cancellationReason, setCancellationReason] = useState("");

  // Tablet/iPad Portrait também entra como mobile para o calendário
  const [isMobile, setIsMobile] = useState(window.innerWidth < 1024);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 1024);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 🔄 FORÇA refetch ao montar o componente
  useEffect(() => {
    console.log("🔄 AppointmentsPage montada - forçando refetch...");
    refetch();
  }, [refetch]);

  useEffect(() => {
    if (appointments) {
      console.log("📊 AppointmentsPage - Total de agendamentos:", appointments.length, appointments);
    }
  }, [appointments]);

  const weekDays = useMemo(() => {
    const days = [];
    const labels = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    const daysToShow = isMobile ? 1 : 7;

    for (let i = 0; i < daysToShow; i++) {
      const date = new Date(startDate);
      date.setDate(startDate.getDate() + i);

      const dayLabel = labels[date.getDay()];
      const dayDate = `${String(date.getDate()).padStart(2, "0")}/${String(date.getMonth() + 1).padStart(2, "0")}`;
      const dayIso = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;

      days.push({ label: dayLabel, date: dayDate, iso: dayIso });
    }
    return days;
  }, [startDate, isMobile]);

  const handlePrev = () => {
    const newDate = new Date(startDate);
    newDate.setDate(startDate.getDate() - (isMobile ? 1 : 7));
    setStartDate(newDate);
  };

  const handleNext = () => {
    const newDate = new Date(startDate);
    newDate.setDate(startDate.getDate() + (isMobile ? 1 : 7));
    setStartDate(newDate);
  };

  const handleToday = () => {
    // Se mobile, hoje é hoje. Se desktop, é a segunda-feira da semana atual.
    const today = new Date();
    setStartDate(isMobile ? today : getMonday(today));
  };

  const handleOpenModal = (isoDate: string, hour: string) => {
    // Constrói objeto Date a partir do ISO (YYYY-MM-DD) e Hora (HH:MM)
    const [year, month, day] = isoDate.split('-').map(Number);
    const [h, m] = hour.split(':').map(Number);

    const date = new Date(year, month - 1, day, h, m);
    setSelectedSlotDate(date);
    setIsModalOpen(true);
  };

  const handleCreateAppointment = async (data: AppointmentCreateData) => {
    await createAppointment.mutateAsync(data);
  };

  const handleCancelClick = (appt: Appointment, e: React.MouseEvent) => {
    e.stopPropagation();
    if (appt.status.toLowerCase() === 'cancelled') {
      alert('Este agendamento já foi cancelado.');
      return;
    }
    setCancellingAppointment(appt);
    setCancellationReason("");
  };

  const handleConfirmCancel = async () => {
    if (!cancellingAppointment) return;

    try {
      await cancelAppointment.mutateAsync({
        id: cancellingAppointment.id,
        cancellation_reason: cancellationReason || "Cancelado pelo usuário"
      });
      setCancellingAppointment(null);
      setCancellationReason("");
    } catch (error) {
      console.error("Erro ao cancelar:", error);
      alert("Erro ao cancelar agendamento. Tente novamente.");
    }
  };

  if (isLoading) {
    return (
      <div className="w-full max-w-6xl mx-auto bg-white/80 rounded-2xl shadow-2xl p-8 flex items-center justify-center">
        <p className="text-xl text-[#3a5a60]">Carregando agendamentos...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full max-w-6xl mx-auto bg-white/80 rounded-2xl shadow-2xl p-8 flex items-center justify-center">
        <p className="text-xl text-red-600">Erro ao carregar agendamentos: {error.message}</p>
      </div>
    );
  }

  function getAppointmentForCell(dayIso: string, hour: string): Appointment | undefined {
    return appointments?.find((appt) => {
      // Ignora agendamentos cancelados - horário fica disponível
      if (appt.status.toLowerCase() === 'cancelled') {
        return false;
      }

      const apptDate = new Date(appt.scheduled_at);
      const apptDayIso = `${apptDate.getFullYear()}-${String(apptDate.getMonth() + 1).padStart(2, '0')}-${String(apptDate.getDate()).padStart(2, '0')}`;
      return (
        apptDayIso === dayIso &&
        apptDate.getHours() === parseInt(hour.slice(0, 2))
      );
    });
  }

  return (
    <>
      <div className="w-full max-w-7xl mx-auto bg-white rounded-3xl shadow-xl border border-slate-100 p-4 lg:p-6 flex flex-col h-[calc(100vh-80px)] lg:h-[calc(100vh-60px)] overflow-hidden font-sans">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center mb-4 lg:mb-6 gap-4">
          <div>
            <h1 className="text-2xl lg:text-3xl font-extrabold text-slate-800 tracking-tight">Agendamentos</h1>
            <p className="text-slate-500 mt-0.5 lg:mt-1 font-medium text-sm lg:text-base">Gestão da agenda</p>
          </div>

          <div className="flex items-center justify-between w-full lg:w-auto gap-4 bg-slate-50 p-2 rounded-2xl border border-slate-100 self-end lg:self-auto">
            <button
              onClick={handleToday}
              className="px-4 py-2 text-sm font-bold text-slate-600 hover:bg-white hover:shadow-sm rounded-xl transition-all flex-1 lg:flex-none"
            >
              Hoje
            </button>
            <div className="flex items-center gap-1">
              <button
                onClick={handlePrev}
                className="p-3 lg:p-2 bg-white lg:bg-transparent shadow-sm lg:shadow-none hover:bg-white hover:shadow-md rounded-xl transition-all text-slate-600 border border-slate-100 lg:border-transparent"
                title="Anterior"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6" /></svg>
              </button>
              <button
                onClick={handleNext}
                className="p-3 lg:p-2 bg-white lg:bg-transparent shadow-sm lg:shadow-none hover:bg-white hover:shadow-md rounded-xl transition-all text-slate-600 border border-slate-100 lg:border-transparent"
                title="Próximo"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6" /></svg>
              </button>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-auto rounded-xl border border-slate-200 shadow-inner bg-slate-50/50">
          <table className="min-w-full border-separate border-spacing-0 bg-white">
            <thead className="bg-white">
              <tr>
                <th className="bg-white p-2 lg:p-4 border-b border-r border-slate-200 sticky top-0 left-0 z-30 w-12 lg:w-16 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)]" />
                {weekDays.map((day) => (
                  <th
                    key={day.iso}
                    className="sticky top-0 z-20 border-b border-slate-200 bg-white px-1 lg:px-2 py-3 lg:py-4 min-w-[100px] lg:min-w-[140px] text-center shadow-[0_2px_5px_-2px_rgba(0,0,0,0.05)]"
                  >
                    <div className="text-xs lg:text-sm font-bold text-slate-700 uppercase tracking-wider">{day.label}</div>
                    <div className="text-[10px] lg:text-xs font-medium text-slate-400 mt-0.5">{day.date}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {hours.map((hour) => (
                <tr key={hour} className="group">
                  <td className="bg-white border-r border-b border-slate-100 text-right px-3 py-3 text-xs font-semibold text-slate-400 sticky left-0 z-20 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.05)] select-none">
                    {hour}
                  </td>
                  {weekDays.map((day) => {
                    const appt = getAppointmentForCell(day.iso, hour);
                    return (
                      <td
                        key={day.iso + hour}
                        className="border-b border-r border-slate-100 h-28 relative p-1.5 transition-colors hover:bg-slate-50/80 align-top group-hover:bg-slate-50/30"
                      >
                        {appt ? (
                          <div
                            className={`w-full h-full rounded-lg shadow-sm hover:shadow-md transition-all duration-200 p-2.5 flex flex-col justify-between text-white border-l-4 border-black/10 cursor-pointer hover:scale-[1.01] hover:-translate-y-0.5 ${getColorByStatus(
                              appt.status
                            )}`}
                            title={appt.meeting_type || "Reunião"}
                          >
                            <div>
                              <div className="flex justify-between items-start mb-1">
                                <div className="font-bold text-xs leading-tight line-clamp-2 flex-1">
                                  {appt.meeting_type || "Reunião"}
                                </div>
                                {appt.status.toLowerCase() !== 'cancelled' && (
                                  <button
                                    onClick={(e) => handleCancelClick(appt, e)}
                                    className="ml-1 text-white/80 hover:text-white hover:bg-black/20 rounded px-1.5 py-0.5 text-[9px] font-bold transition-colors"
                                    title="Cancelar agendamento"
                                  >
                                    ✕
                                  </button>
                                )}
                              </div>

                            </div>
                            <div className="flex items-center gap-1 mt-1">
                              <div className={`w-1.5 h-1.5 rounded-full bg-white animate-pulse`} />
                              <span className="text-[9px] font-bold uppercase tracking-wider opacity-95">
                                {appt.status}
                              </span>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => handleOpenModal(day.iso, hour)}
                            className="w-full h-full rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center text-slate-300 opacity-0 hover:opacity-100 hover:border-blue-300 hover:bg-blue-50 hover:text-blue-400 transition-all duration-200 scale-95 hover:scale-100"
                            title="Agendar neste horário"
                          >
                            <span className="text-2xl font-light">+</span>
                          </button>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <AppointmentModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        initialDate={selectedSlotDate}
        onSave={handleCreateAppointment}
      />

      {/* Modal de Confirmação de Cancelamento */}
      {cancellingAppointment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="bg-rose-50 px-6 py-4 border-b border-rose-100">
              <h3 className="text-lg font-bold text-rose-800">Cancelar Agendamento</h3>
            </div>

            <div className="p-6 space-y-4">
              <p className="text-slate-700">
                Tem certeza que deseja cancelar este agendamento?
              </p>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                <p className="text-xs text-slate-500 uppercase font-bold mb-1">Detalhes</p>
                <p className="text-sm font-semibold text-slate-800">{cancellingAppointment.meeting_type || "Reunião"}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {new Date(cancellingAppointment.scheduled_at).toLocaleString('pt-BR', {
                    dateStyle: 'short',
                    timeStyle: 'short'
                  })}
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Motivo do Cancelamento (Opcional)</label>
                <textarea
                  rows={3}
                  className="w-full rounded-lg border-slate-200 text-sm focus:ring-2 focus:ring-rose-500 focus:border-transparent"
                  value={cancellationReason}
                  onChange={(e) => setCancellationReason(e.target.value)}
                  placeholder="Descreva o motivo..."
                />
              </div>
            </div>

            <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex gap-3">
              <button
                onClick={() => {
                  setCancellingAppointment(null);
                  setCancellationReason("");
                }}
                className="flex-1 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl font-medium hover:bg-slate-50 transition-colors"
              >
                Voltar
              </button>
              <button
                onClick={handleConfirmCancel}
                className="flex-1 px-4 py-2 bg-rose-500 text-white rounded-xl font-bold hover:bg-rose-600 transition-colors shadow-lg shadow-rose-200"
              >
                Confirmar Cancelamento
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AppointmentsPage;
