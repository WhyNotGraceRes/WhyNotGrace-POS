import axios, { type InternalAxiosRequestConfig } from "axios";
import { env } from "@/config/env";
import { usePlatformAuthStore } from "@/stores/platformAuthStore";
import type { PlatformAccessTokenResponse } from "@/types/models";

const API_BASE = `${env.apiUrl}/api/v1`;

/** Platform-only client — every src/features/platform API call goes
 * through this, never the business apiClient (src/api/client.ts). Same
 * refresh-on-401 shape as that file, pointed at the platform's own
 * store/refresh endpoint instead — see that file's comments for why each
 * piece is built the way it is; not repeated here. */
export const platformApiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

const refreshClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

platformApiClient.interceptors.request.use((config) => {
  const token = usePlatformAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

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
  const { refreshToken, setTokens, clearSession } = usePlatformAuthStore.getState();
  if (!refreshToken) {
    clearSession();
    throw new Error("No refresh token available");
  }

  try {
    const { data } = await refreshClient.post<PlatformAccessTokenResponse>("/platform/auth/refresh", {
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

platformApiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as RetryableConfig | undefined;

    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      original.url?.includes("/platform/auth/login") ||
      original.url?.includes("/platform/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        queue.push({
          resolve: (token) => {
            original.headers.set("Authorization", `Bearer ${token}`);
            resolve(platformApiClient(original));
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
      return platformApiClient(original);
    } catch (refreshError) {
      flushQueue(refreshError, null);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
