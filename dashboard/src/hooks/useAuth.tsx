import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { authApi, getStoredToken, setStoredToken } from "@/lib/api";
import type { SignupResponse, User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (
    email: string,
    password: string,
    clientName: string,
  ) => Promise<SignupResponse>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(
  undefined,
);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = React.useState<string | null>(() =>
    getStoredToken(),
  );

  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: ["auth", "me", token],
    queryFn: async () => {
      if (!token) return null;
      try {
        return await authApi.me();
      } catch {
        return null;
      }
    },
    staleTime: 60_000,
  });

  const login = React.useCallback(
    async (email: string, password: string) => {
      const response = await authApi.login({ email, password });
      setStoredToken(response.access_token);
      setToken(response.access_token);
      queryClient.setQueryData(
        ["auth", "me", response.access_token],
        response.user,
      );
      return response.user;
    },
    [queryClient],
  );

  const signup = React.useCallback(
    async (email: string, password: string, clientName: string) => {
      const response = await authApi.signup({
        email,
        password,
        client_name: clientName,
      });
      setStoredToken(response.access_token);
      setToken(response.access_token);
      queryClient.setQueryData(
        ["auth", "me", response.access_token],
        response.user,
      );
      return response;
    },
    [queryClient],
  );

  const logout = React.useCallback(() => {
    setStoredToken(null);
    setToken(null);
    queryClient.clear();
  }, [queryClient]);

  const value: AuthContextValue = {
    user: user ?? null,
    token,
    isLoading,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
