import { apiClient, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_KEY, clearAuthStorage } from './client';
import { AuthResponse, LoginCredentials, RegisterPayload, User } from '../types';

export const authApi = {
  /**
   * Authenticate user credentials
   * POST /api/v1/auth/login
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const data = await apiClient.post<AuthResponse>('/api/v1/auth/login', credentials, {
      skipAuth: true,
    });

    if (data.access_token) {
      localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
      if (data.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      }
    }

    // Call GET /api/v1/auth/me to fetch authenticated profile details
    try {
      const user = await authApi.getMe();
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      data.user = user;
    } catch (meError) {
      // If /me has issues or data.user was already included, ensure fallback
      if (data.user) {
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      }
    }

    return data;
  },

  /**
   * Retrieve current authenticated user profile
   * GET /api/v1/auth/me
   */
  async getMe(): Promise<User> {
    const user = await apiClient.get<User>('/api/v1/auth/me');
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    return user;
  },

  /**
   * Register a new user
   * POST /api/v1/auth/register
   */
  async register(payload: RegisterPayload): Promise<AuthResponse | User> {
    return apiClient.post<AuthResponse | User>('/api/v1/auth/register', payload, {
      skipAuth: true,
    });
  },

  /**
   * Refresh the access token explicitly
   * POST /api/v1/auth/refresh
   */
  async refresh(): Promise<AuthResponse> {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    return apiClient.post<AuthResponse>('/api/v1/auth/refresh', { refresh_token: refreshToken });
  },

  /**
   * Logout user and revoke session
   * POST /api/v1/auth/logout
   */
  async logout(): Promise<void> {
    try {
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        await apiClient.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      }
    } catch {
      // Continue clearing storage even if backend call fails
    } finally {
      clearAuthStorage();
    }
  },
};

