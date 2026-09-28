import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { ACCESS_TOKEN_KEY, USER_KEY, clearAuthStorage } from '../api/client';
import { LoginCredentials, RegisterPayload, User } from '../types';
import { normalizeRole } from '../utils/formatters';

interface AuthContextValue {
  user: User | null;
  role: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const stored = localStorage.getItem(USER_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initialize auth state and verify with backend
  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!token) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      try {
        const verifiedUser = await authApi.getMe();
        setUser(verifiedUser);
        localStorage.setItem(USER_KEY, JSON.stringify(verifiedUser));
      } catch (err) {
        console.warn('Initial session verification failed:', err);
        // If 401 or token was invalid, clear state
        clearAuthStorage();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials): Promise<User> => {
    const response = await authApi.login(credentials);
    let resolvedUser = response.user;

    if (!resolvedUser) {
      resolvedUser = await authApi.getMe();
    }

    setUser(resolvedUser);
    localStorage.setItem(USER_KEY, JSON.stringify(resolvedUser));
    return resolvedUser;
  }, []);

  const register = useCallback(async (payload: RegisterPayload): Promise<void> => {
    await authApi.register(payload);
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await authApi.logout();
    } finally {
      clearAuthStorage();
      setUser(null);
    }
  }, []);

  const refreshProfile = useCallback(async (): Promise<User | null> => {
    try {
      const updatedUser = await authApi.getMe();
      setUser(updatedUser);
      localStorage.setItem(USER_KEY, JSON.stringify(updatedUser));
      return updatedUser;
    } catch {
      return null;
    }
  }, []);

  const role = normalizeRole(user?.role);
  const isAuthenticated = Boolean(user && localStorage.getItem(ACCESS_TOKEN_KEY));

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
