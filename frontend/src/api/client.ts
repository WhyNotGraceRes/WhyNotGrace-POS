import axios, { type InternalAxiosRequestConfig } from "axios";
import { env } from "@/config/env";
import { useAuthStore } from "@/stores/authStore";
import type { AccessTokenResponse } from "@/types/models";

const API_BASE = `${env.apiUrl}/api/v1`;

/** Main client — every feature API call goes through this. */
export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

/** Bare client for the refresh call itself — must never carry the
 * response-interceptor's own refresh logic, or a failed refresh would
 * try to refresh itself forever. */
const refreshClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

// --- 401 handling: refresh once, replay queued requests ------------------

type QueuedRequest = {
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
};

let isRefreshing = false;
let queue: QueuedRequest[] = [];

function flushQueue(error: unknown, token: string | null) {
  for (const { resolve, reject } of queue) {
    if (token) resolve(token);
    else reject(error);
  }
  queue = [];
}

async function refreshAccessToken(): Promise<string> {
  const { refreshToken, setTokens, clearSession } = useAuthStore.getState();
  if (!refreshToken) {
    clearSession();
    throw new Error("No refresh token available");
  }

  try {
    const { data } = await refreshClient.post<AccessTokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    setTokens(data);
    return data.access_token;
  } catch (err) {
    clearSession();
    throw err;
  }
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryableConfig | undefined;

    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      original.url?.includes("/auth/login") ||
      original.url?.includes("/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        queue.push({
          resolve: (token) => {
            original.headers.set("Authorization", `Bearer ${token}`);
            resolve(apiClient(original));
          },
          reject,
        });
      });
    }

    isRefreshing = true;
    try {
      const token = await refreshAccessToken();
      flushQueue(null, token);
      original.headers.set("Authorization", `Bearer ${token}`);
      return apiClient(original);
    } catch (refreshError) {
      flushQueue(refreshError, null);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
