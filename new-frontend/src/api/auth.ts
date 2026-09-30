import { apiClient, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, USER_KEY, clearAuthStorage } from './client';
import { AuthResponse, LoginCredentials, RegisterPayload, User } from '../types';

export const authApi = {
  /**
   * Authenticate user credentials
   * POST /api/v1/auth/login
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    console.log('[Auth] Submitting login request to /api/v1/auth/login for:', credentials.email);
    const data = await apiClient.post<AuthResponse>('/api/v1/auth/login', credentials, {
      skipAuth: true,
    });
    console.log('[Auth] Login response payload received:', data);
    console.log('[Auth] access_token present:', Boolean(data?.access_token));

    if (!data || !data.access_token) {
      console.error('[Auth] Server returned response without access_token:', data);
      throw new Error('Authentication succeeded but server returned no access token.');
    }

    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    console.log(`[Auth] Stored ${ACCESS_TOKEN_KEY}:`, localStorage.getItem(ACCESS_TOKEN_KEY) ? 'SUCCESS' : 'FAILED');

    if (data.refresh_token) {
      localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      console.log(`[Auth] Stored ${REFRESH_TOKEN_KEY}: SUCCESS`);
    }

    // Call GET /api/v1/auth/me to fetch authenticated profile details with explicit token
    console.log('[Auth] Fetching user profile via getMe()...');
    const user = await authApi.getMe(data.access_token);
    console.log('[Auth] getMe() returned user:', user);

    if (user && user.email) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      data.user = user;
      console.log(`[Auth] Stored ${USER_KEY} in localStorage:`, user.email);
    } else {
      console.error('[Auth] User profile retrieved is invalid or missing email:', user);
      throw new Error('Failed to retrieve valid user profile from server.');
    }

    return data;
  },

  /**
   * Retrieve current authenticated user profile
   * GET /api/v1/auth/me
   */
  async getMe(overrideToken?: string): Promise<User> {
    console.log('[Auth] getMe() called. Override token provided:', Boolean(overrideToken));
    const token = overrideToken || localStorage.getItem(ACCESS_TOKEN_KEY);
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const user = await apiClient.get<User>('/api/v1/auth/me', { headers });
    console.log('[Auth] /api/v1/auth/me response:', user);
    if (user && user.email) {
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

