/** Session de l'utilisateur : jeton JWT + profil, partagés dans toute l'application. */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, getToken, setToken } from "../api/client";
import type { User } from "../api/types";

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  organization_name: string | null;
}

interface AuthValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  /** Inscription d'un compte CLIENT (un compte freelance demande un profil créé par la plateforme). */
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(getToken() !== null);

  // Au chargement : si un jeton existe, on vérifie qu'il est toujours valide.
  useEffect(() => {
    if (!getToken()) return;
    api
      .me()
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const out = await api.login(email, password);
    setToken(out.access_token);
    setUser(out.user);
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    const out = await api.register(data);
    setToken(out.access_token);
    setUser(out.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans <AuthProvider>.");
  return ctx;
}
