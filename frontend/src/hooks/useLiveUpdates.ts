import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { env } from "@/config/env";
import { useAuthStore } from "@/stores/authStore";

const RECONNECT_DELAY_MS = 3000;

interface InvalidateMessage {
  type: "invalidate";
  keys: string[];
}

function isInvalidateMessage(value: unknown): value is InvalidateMessage {
  if (typeof value !== "object" || value === null) return false;
  const record = value as Record<string, unknown>;
  return record.type === "invalidate" && Array.isArray(record.keys);
}

/** Opens one WebSocket per authenticated session and turns each incoming
 * `{"type": "invalidate", "keys": [...]}` frame into React Query
 * invalidations — see backend/app/core/ws_manager.py for why the wire
 * format is this thin (a "go refetch" signal, not the data itself).
 *
 * Every screen's existing `refetchInterval` polling stays exactly as it
 * was: this hook is purely additive. If the socket never connects, drops,
 * or the backend hasn't been redeployed with WS support yet, the app
 * behaves exactly like it did before this hook existed — a few seconds
 * slower to notice a change, never wrong or broken. */
export function useLiveUpdates() {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!accessToken) return;

    let cancelled = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (cancelled) return;
      const wsBase = env.apiUrl.replace(/^http/, "ws");
      socket = new WebSocket(`${wsBase}/api/v1/ws?token=${encodeURIComponent(accessToken)}`);

      socket.onmessage = (event) => {
        let message: unknown;
        try {
          message = JSON.parse(event.data as string);
        } catch {
          return;
        }
        if (isInvalidateMessage(message)) {
          for (const key of message.keys) {
            void queryClient.invalidateQueries({ queryKey: [key] });
          }
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [accessToken, queryClient]);
}
