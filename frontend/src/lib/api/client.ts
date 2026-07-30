import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Configured Axios instance for all API calls.
 * Handles token injection, refresh, and error normalization.
 */
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor: inject access token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Inject tenant ID if available
    const tenantId = getTenantId();
    if (tenantId && config.headers) {
      config.headers["X-Tenant-ID"] = tenantId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 with token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && originalRequest && !isRefreshing) {
      isRefreshing = true;

      try {
        const newToken = await refreshAccessToken();
        if (newToken && originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
      } catch {
        // Refresh failed, redirect to login
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(normalizeError(error));
  }
);

let isRefreshing = false;

// Token management (localStorage for client-side)
function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getTenantId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("tenant_id");
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;

  const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
    refresh_token: refreshToken,
  });

  const { access_token, refresh_token: newRefresh } = response.data;
  localStorage.setItem("access_token", access_token);
  if (newRefresh) {
    localStorage.setItem("refresh_token", newRefresh);
  }

  return access_token;
}

function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("tenant_id");
}

// Error normalization
interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
  status: number;
}

function normalizeError(error: AxiosError): ApiError {
  const data = error.response?.data as { error?: Partial<ApiError> } | undefined;

  return {
    code: data?.error?.code || "NETWORK_ERROR",
    message: data?.error?.message || "An unexpected error occurred",
    details: data?.error?.details || {},
    status: error.response?.status || 0,
  };
}

export type { ApiError };
