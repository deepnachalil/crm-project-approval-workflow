import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authApi } from "../api";
import { setUnauthorizedHandler, tokenStore } from "../api/http";
import { config } from "../config";
import type { CurrentUser, Role } from "../types/api";
import { cognitoLogin } from "./cognito";

interface AuthState {
  user: CurrentUser | null;
  initializing: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: Role) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [initializing, setInitializing] = useState(true);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!tokenStore.get()) {
      setInitializing(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(logout)
      .finally(() => setInitializing(false));
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    if (config.authMode === "cognito") {
      tokenStore.set(await cognitoLogin(email, password));
      setUser(await authApi.me());
    } else {
      const res = await authApi.login(email, password);
      tokenStore.set(res.access_token);
      setUser(res.user);
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, initializing, login, logout, hasRole: (role) => user?.role === role }),
    [user, initializing, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
