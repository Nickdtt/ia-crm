// src/hooks/useClients.ts

/**
 * Hook personalizado para buscar clientes do backend.
 * Utiliza o TanStack Query para gerenciar o estado das queries.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";

// Definição do tipo de dados retornados pela API de clientes
export interface Client {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  company_name?: string;
  segment?: string;
  monthly_budget?: number;
  main_marketing_problem?: string;
  created_at?: string;
}

export interface ClientCreateData {
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  company_name?: string;
  segment: string;
  monthly_budget: number;
  main_marketing_problem: string;
  notes?: string;
}

/**
 * Hook para buscar clientes.
 * @returns {object} - Dados dos clientes, estado de carregamento e erros.
 */
export const useClients = () => {
  return useQuery<Client[], Error>({
    queryKey: ["clients"],
    queryFn: async () => {
      const response = await api.get<Client[]>("/api/v1/clients/");
      return response.data;
    },
  });
};

/**
 * Hook para criar um novo cliente.
 */
export const useCreateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ClientCreateData) => {
      const response = await api.post("/api/v1/clients/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
};

/**
 * Hook para atualizar um cliente existente.
 */
export const useUpdateClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<ClientCreateData> }) => {
      const response = await api.put(`/api/v1/clients/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
};

/**
 * Hook para deletar um cliente.
 */
export const useDeleteClient = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/clients/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
    },
  });
};
