import axios from "axios";
import { env } from "@/config/env";

const API_BASE = `${env.apiUrl}/api/v1`;

/**
 * Public QR ordering never sends a staff Authorization header and never
 * goes through the staff 401/refresh interceptor — it's a completely
 * separate, unauthenticated client so a customer's browser can never end
 * up carrying (or being confused with) staff credentials.
 */
export const qrClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});
