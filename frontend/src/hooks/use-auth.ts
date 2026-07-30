"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiClient, type ApiError } from "@/lib/api/client";
import { useAuthStore, type User } from "@/stores/auth.store";

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  company_name: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

export function useAuth() {
  const router = useRouter();
  const { setUser, logout: storeLogout, user, isAuthenticated } = useAuthStore();

  // Fetch current user profile
  const profileQuery = useQuery({
    queryKey: ["auth", "profile"],
    queryFn: async () => {
      const response = await apiClient.get<User>("/api/v1/auth/me");
      setUser(response.data);
      return response.data;
    },
    enabled: isAuthenticated,
    retry: false,
  });

  // Login mutation
  const loginMutation = useMutation<AuthResponse, ApiError, LoginCredentials>({
    mutationFn: async (credentials) => {
      const response = await apiClient.post<AuthResponse>(
        "/api/v1/auth/login",
        credentials
      );
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("tenant_id", data.user.tenant_id);
      setUser(data.user);
      router.push("/chat");
    },
  });

  // Register mutation
  const registerMutation = useMutation<AuthResponse, ApiError, RegisterData>({
    mutationFn: async (data) => {
      const response = await apiClient.post<AuthResponse>(
        "/api/v1/auth/register",
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      localStorage.setItem("tenant_id", data.user.tenant_id);
      setUser(data.user);
      router.push("/chat");
    },
  });

  // Logout
  const logout = () => {
    storeLogout();
    router.push("/login");
  };

  return {
    user,
    isAuthenticated,
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    registerAsync: registerMutation.mutateAsync,
    registerError: registerMutation.error,
    isRegistering: registerMutation.isPending,
    logout,
    profileQuery,
  };
}
