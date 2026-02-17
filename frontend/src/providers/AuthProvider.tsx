import { useEffect } from 'react';
import type { ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const { refetchUser } = useAuth();

  useEffect(() => {
    // Ao montar, verifica se existe token válido e restaura sessão
    refetchUser();
  }, [refetchUser]);

  return <>{children}</>;
};
