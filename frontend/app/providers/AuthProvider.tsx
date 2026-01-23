'use client';

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import type { LoginRequest, LoginResponse, RegisterRequest, RegisterResponse, UserInfo } from '@/lib/types';

type Role = 'claimant' | 'insurer';

type AuthState = {
  token: string | null;
  user: UserInfo | null;
  loading: boolean;
};

type AuthContextValue = AuthState & {
  role: Role | null;
  walletAddress: string | null;
  login: (data: LoginRequest) => Promise<LoginResponse>;
  register: (data: RegisterRequest) => Promise<RegisterResponse>;
  logout: () => void;
  refresh: () => Promise<UserInfo | null>;
  redirectToHome: (roleOverride?: Role | null) => void;
};

const AUTH_TOKEN_KEY = 'auth_token';

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readTokenFromStorage(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function writeTokenToStorage(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
  else localStorage.removeItem(AUTH_TOKEN_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>(() => ({
    token: readTokenFromStorage(),
    user: null,
    loading: true,
  }));

  const logout = useCallback(() => {
    writeTokenToStorage(null);
    api.auth.logout();
    setState({ token: null, user: null, loading: false });
    router.push('/login');
  }, [router]);

  const refresh = useCallback(async (): Promise<UserInfo | null> => {
    const token = readTokenFromStorage();
    if (!token) {
      setState({ token: null, user: null, loading: false });
      return null;
    }

    try {
      const me = await api.auth.me();
      setState({ token, user: me, loading: false });
      return me;
    } catch (err: any) {
      // Handle "User not found" or any 401 error - use existing logout function
      // logout() already clears token, state, and redirects to /login
      writeTokenToStorage(null);
      logout(); // Use existing logout function for proper cleanup
      return null;
    }
  }, [logout]);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = useCallback(async (data: LoginRequest): Promise<LoginResponse> => {
    setState(s => ({ ...s, loading: true }));
    const res = await api.auth.login(data);
    writeTokenToStorage(res.access_token);
    // hydrate canonical user data
    try {
      const me = await api.auth.me();
      setState({ token: res.access_token, user: me, loading: false });
    } catch {
      setState({
        token: res.access_token,
        user: {
          user_id: res.user_id,
          email: res.email,
          role: res.role,
          wallet_address: res.wallet_address,
        },
        loading: false,
      });
    }
    return res;
  }, []);

  const register = useCallback(async (data: RegisterRequest): Promise<RegisterResponse> => {
    setState(s => ({ ...s, loading: true }));
    const res = await api.auth.register(data);
    writeTokenToStorage(res.access_token);
    // hydrate canonical user data
    try {
      const me = await api.auth.me();
      setState({ token: res.access_token, user: me, loading: false });
    } catch {
      setState({
        token: res.access_token,
        user: {
          user_id: res.user_id,
          email: res.email,
          role: res.role,
          wallet_address: res.wallet_address,
        },
        loading: false,
      });
    }
    return res;
  }, []);

  const redirectToHome = useCallback(
    (roleOverride?: Role | null) => {
      const role = (roleOverride ?? (state.user?.role as Role | undefined)) || null;
      if (role === 'insurer') router.push('/insurer');
      else if (role === 'claimant') router.push('/claimant');
      else router.push('/login');
    },
    [router, state.user?.role]
  );

  const value = useMemo<AuthContextValue>(() => {
    const role = (state.user?.role as Role | undefined) || null;
    const walletAddress = state.user?.wallet_address ?? null;
    return {
      ...state,
      role,
      walletAddress,
      login,
      register,
      logout,
      refresh,
      redirectToHome,
    };
  }, [login, refresh, register, logout, redirectToHome, state]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

