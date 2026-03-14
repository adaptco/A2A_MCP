import { ApiClient } from "@world-os/sdk";

export const api = new ApiClient({
  baseUrl: (window as any)["__API_URL__"] || import.meta.env.VITE_API_URL || "http://localhost:3001"
});
