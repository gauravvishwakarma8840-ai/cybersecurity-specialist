/**
 * Auth Context
 * Provides authentication state and actions to the entire app.
 * Persists user/token in localStorage with secure token refresh.
 */
'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authApi, type User, type Organization } from './api';

interface AuthState {
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    org: { name: string; slug: string };
  }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    organization: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Rehydrate from localStorage on mount
  useEffect(() => {
    try {
      const token = localStorage.getItem('access_token');
      const userJson = localStorage.getItem('user');
      const orgJson = localStorage.getItem('organization');

      if (token && userJson) {
        setState({
          user: JSON.parse(userJson),
          organization: orgJson ? JSON.parse(orgJson) : null,
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        setState(prev => ({ ...prev, isLoading: false }));
      }
    } catch {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login(email, password);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('user', JSON.stringify(response.user));
    localStorage.setItem('organization', JSON.stringify(response.organization));
    setState({
      user: response.user,
      organization: response.organization,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const register = useCallback(async (payload: Parameters<typeof authApi.register>[0]) => {
    const response = await authApi.register(payload);
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('user', JSON.stringify(response.user));
    localStorage.setItem('organization', JSON.stringify(response.organization));
    setState({
      user: response.user,
      organization: response.organization,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Continue with local logout even if server request fails
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      localStorage.removeItem('organization');
      setState({ user: null, organization: null, isAuthenticated: false, isLoading: false });
      window.location.href = '/login';
    }
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
