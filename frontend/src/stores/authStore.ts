/**
 * Zustand Store de Autenticação
 * Gerencia estado global de autenticação (usuário, isAuthenticated)
 */

import { create } from 'zustand';

interface UserData {
  id: string;
  email: string;
}

interface AuthStore {
  isAuthenticated: boolean;
  user: UserData | null;
  setUser: (user: UserData | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  isAuthenticated: false,
  user: null,
  
  setUser: (user) => set({ 
    user, 
    isAuthenticated: !!user 
  }),
  
  logout: () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    set({ user: null, isAuthenticated: false });
  },
}));
