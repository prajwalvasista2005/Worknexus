/**
 * SkillMesh Unified API Client
 * Enterprise labour-market intelligence and workforce curriculum-alignment platform.
 */

import { ApiErrorResponse } from '../types';

export const ACCESS_TOKEN_KEY = 'worknexus_access_token';
export const REFRESH_TOKEN_KEY = 'worknexus_refresh_token';
export const USER_KEY = 'worknexus_user';

// Configurable base URL
export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.replace(/\/+$/, '');
  }
  if (
    typeof window !== 'undefined' &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
  ) {
    return window.location.origin;
  }
  return 'http://localhost:8000';
};

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

// Single in-flight refresh promise to prevent simultaneous refreshes
let activeRefreshPromise: Promise<string | null> | null = null;

export const parseFastApiError = (data: unknown, fallbackMessage = 'An unexpected error occurred'): string => {
  if (!data) return fallbackMessage;

  if (typeof data === 'string') {
    return data;
  }

  const err = data as ApiErrorResponse;

  if (typeof err.detail === 'string') {
    return err.detail;
  }

  if (Array.isArray(err.detail) && err.detail.length > 0) {
    return err.detail
      .map((item) => {
        if (typeof item === 'string') return item;
        const field = item.loc && item.loc.length > 0 ? `${item.loc[item.loc.length - 1]}: ` : '';
        return `${field}${item.msg || 'Invalid value'}`;
      })
      .join('; ');
  }

  if (err.message) {
    return err.message;
  }

  return fallbackMessage;
};

export const clearAuthStorage = (): void => {
  try {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch (err) {
    console.error('Failed to clear auth storage:', err);
  }
};

const performTokenRefresh = async (): Promise<string | null> => {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    clearAuthStorage();
    return null;
  }

  const baseUrl = getApiBaseUrl();
  try {
    const response = await fetch(`${baseUrl}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${refreshToken}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearAuthStorage();
      return null;
    }

    const data = await response.json();
    const newAccessToken = data.access_token || data.token;
    if (newAccessToken) {
      localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken);
      if (data.refresh_token) {
        localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
      }
      return newAccessToken;
    }

    clearAuthStorage();
    return null;
  } catch (err) {
    console.error('Token refresh network error:', err);
    clearAuthStorage();
    return null;
  } finally {
    activeRefreshPromise = null;
  }
};

export interface RequestOptions extends RequestInit {
  skipAuth?: boolean;
  isRetry?: boolean;
}

export async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${normalizedEndpoint}`;

  const headers = new Headers(options.headers || {});

  // Set default JSON Content-Type if sending body and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Attach Bearer token if not skipped
  if (!options.skipAuth) {
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    // If fetch failed, determine if backend is truly unreachable or if it rejected with a 500/CORS error
    try {
      await fetch(`${baseUrl}/docs`, { method: 'HEAD', mode: 'no-cors' });
      // If we reach here, backend IS running and reachable!
      const netMsg = netErr instanceof Error ? netErr.message : 'Network error';
      throw new ApiError(
        `Server error: ${netMsg}. Backend is reachable at ${baseUrl} but the request could not be completed.`,
        500,
        netErr
      );
    } catch (checkErr) {
      if (checkErr instanceof ApiError) {
        throw checkErr;
      }
      throw new ApiError(
        `Unable to reach backend at ${baseUrl}. Please verify the server is running.`,
        0,
        netErr
      );
    }
  }

  // Intercept 401 Unauthorized for refresh token handling
  const isAuthEndpoint =
    normalizedEndpoint.includes('/auth/login') ||
    normalizedEndpoint.includes('/auth/refresh') ||
    normalizedEndpoint.includes('/auth/logout') ||
    normalizedEndpoint.includes('/auth/register');

  if (response.status === 401 && !options.isRetry && !isAuthEndpoint) {
    if (!activeRefreshPromise) {
      activeRefreshPromise = performTokenRefresh();
    }

    const newAccessToken = await activeRefreshPromise;

    if (newAccessToken) {
      // Retry original request once with new token
      const retryHeaders = new Headers(options.headers || {});
      if (options.body && !(options.body instanceof FormData) && !retryHeaders.has('Content-Type')) {
        retryHeaders.set('Content-Type', 'application/json');
      }
      retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);

      return request<T>(normalizedEndpoint, {
        ...options,
        headers: retryHeaders,
        isRetry: true,
      });
    } else {
      // Refresh failed: clear storage and redirect
      clearAuthStorage();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new ApiError('Session expired. Please log in again.', 401);
    }
  }

  // Handle other error responses
  if (!response.ok) {
    let errorData: unknown = null;
    let errorMessage = `Server error (HTTP ${response.status})`;
    try {
      errorData = await response.json();
      errorMessage = parseFastApiError(errorData, errorMessage);
    } catch {
      // Failed to parse JSON error, fall back to status text
      errorMessage = response.statusText ? `HTTP ${response.status}: ${response.statusText}` : errorMessage;
    }

    throw new ApiError(errorMessage, response.status, errorData);
  }

  // 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  // Parse success response
  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

export const apiClient = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};
