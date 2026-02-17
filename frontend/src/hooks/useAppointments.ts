// src/hooks/useAppointments.ts

/**
 * Hook personalizado para buscar agendamentos do backend.
 * Utiliza o TanStack Query para gerenciar o estado das queries.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";

// Definição do tipo de dados retornados pela API de agendamentos
export interface Appointment {
  id: string;
  client_id: string;
  meeting_type: string | null;
  status: string;
  scheduled_at: string;
  duration_minutes: number;
  notes: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
}

export interface AppointmentCreateData {
  client_id: string;
  scheduled_at: string;
  duration_minutes: number;
  meeting_type?: string;
  notes?: string;
}

/**
 * Hook para buscar agendamentos.
 * @returns {object} - Dados dos agendamentos, estado de carregamento e erros.
 */
export const useAppointments = () => {
  return useQuery<Appointment[], Error>({
    queryKey: ["appointments"],
    queryFn: async () => {
      const response = await api.get<Appointment[]>("/api/v1/appointments/");
      return response.data;
    },
  });
};

/**
 * Hook para criar um novo agendamento.
 */
export const useCreateAppointment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: AppointmentCreateData) => {
      const response = await api.post("/api/v1/appointments/", data);
      return response.data;
    },
    onSuccess: () => {
      // Invalida a cache para recarregar a lista automaticamente
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
};

/**
 * Hook para cancelar um agendamento.
 */
export const useCancelAppointment = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, cancellation_reason }: { id: string; cancellation_reason?: string }) => {
      const response = await api.patch(`/api/v1/appointments/${id}/cancel`, {
        cancellation_reason: cancellation_reason || "Cancelado pelo usuário"
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["appointments"] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
};