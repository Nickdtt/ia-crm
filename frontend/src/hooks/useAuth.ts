/**
 * Hook de Autenticação (TanStack Query + Zustand)
 * Combina queries/mutations com estado global
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import api from '../services/api';

interface UserData {
  id: string;
  email: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface RefreshResponse {
  access_token: string;
  token_type: string;
}

// Decodifica JWT e extrai payload
const decodeToken = (token: string): any | null => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
};

// Verifica se token está expirado
const isTokenExpired = (token: string): boolean => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;
  const currentTime = Date.now() / 1000;
  return decoded.exp < currentTime;
};

// Extrai dados do usuário do token
const getUserFromToken = (token: string): UserData | null => {
  const decoded = decodeToken(token);
  if (!decoded) return null;
  
  return {
    id: decoded.sub || decoded.user_id,
    email: decoded.email,
  };
};

export const useAuth = () => {
  const { setUser, logout: zustandLogout } = useAuthStore();
  const queryClient = useQueryClient();

  // Query: valida token e busca dados do usuário
  const {
    isLoading,
    refetch: refetchUser,
  } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      console.log('🔍 useAuth: Verificando token...');
      const token = localStorage.getItem('accessToken');
      const refreshToken = localStorage.getItem('refreshToken');
      
      console.log('📦 Token presente:', !!token);
      console.log('📦 Refresh Token presente:', !!refreshToken);
      
      if (!token) {
        console.log('❌ Sem token - usuário não autenticado');
        setUser(null);
        return null;
      }
      
      if (isTokenExpired(token)) {
        console.log('⚠️ Token expirado - usuário será deslogado');
        setUser(null);
        return null;
      }
      
      const userData = getUserFromToken(token);
      console.log('✅ Token válido:', userData);
      
      if (userData) {
        setUser(userData);
      } else {
        console.log('❌ Erro ao extrair dados do token');
        setUser(null);
      }
      
      return userData;
    },
    enabled: true, // MUDANÇA: Habilita execução automática ao montar
    retry: false,
    staleTime: Infinity,
    refetchOnMount: true, // Reexecuta ao montar componente
  });

  // Mutation: Login
  const loginMutation = useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const response = await api.post<LoginResponse>('/api/v1/auth/login', credentials);
      return response.data;
    },

    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      
      const userData = getUserFromToken(data.access_token);
      if (userData) setUser(userData);
      
      refetchUser();
    },
  });

  // Mutation: Refresh Token
  const refreshTokenMutation = useMutation({
    mutationFn: async () => {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) throw new Error('Sem refresh token');
      
      const response = await api.post<RefreshResponse>('/api/v1/auth/refresh', {
        refresh_token: refreshToken,
      });
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem('accessToken', data.access_token);
      const userData = getUserFromToken(data.access_token);
      if (userData) setUser(userData);
    },
    onError: () => logout(),
  });

  // Função de login
  const login = async (email: string, password: string) => {
    try {
      await loginMutation.mutateAsync({ email, password });
      return { success: true };
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail ||
        'Erro ao fazer login. Verifique suas credenciais.';
      return { success: false, error: errorMessage };
    }
  };

  // Função de logout
  const logout = () => {
    zustandLogout();
    queryClient.clear();
  };

  // Função de refresh manual
  const refreshToken = async () => {
    try {
      await refreshTokenMutation.mutateAsync();
      return { success: true };
    } catch (error) {
      return { success: false };
    }
  };

  return {
    user: useAuthStore((state) => state.user),
    isAuthenticated: useAuthStore((state) => state.isAuthenticated),
    isLoading,
    login,
    logout,
    refreshToken,
    refetchUser,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,
  };
};
