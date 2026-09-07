import type { Garment, Health, UserSettings, View } from "./types";
// Browser requests stay on the Next.js origin. next.config.mjs proxies /local-api to
// FastAPI, which avoids CORS/hostname mismatches between Windows and WSL.
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/local-api";
function apiUrl(path:string):string {
  if (!API_BASE) return path;
  if (API_BASE.startsWith("/")) return `${API_BASE}${path.replace(/^\/api/, "")}`;
  return `${API_BASE}${path}`;
}
export function assetUrl(path:string|null, version?:string|number):string|null {
  if (!path) return null;
  const url = apiUrl(path);
  return version === undefined ? url : `${url}${url.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}`;
}
async function request<T>(path:string, options?:RequestInit):Promise<T> {
  const response = await fetch(apiUrl(path), { ...options, cache:"no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?:string|Array<{msg:string}> };
      message = Array.isArray(body.detail) ? body.detail.map(i=>i.msg).join(". ") : body.detail ?? message;
    } catch { /* non-JSON error */ }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
export const api = {
  getUser:()=>request<UserSettings>("/api/user"), getGarments:()=>request<Garment[]>("/api/garments"),
  getGarment:(id:string)=>request<Garment>(`/api/garments/${id}`), getHealth:()=>request<Health>("/api/health"),
  updateProfile:(display_name:string)=>request<UserSettings>("/api/user",{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({display_name})}),
  uploadBody:(data:FormData)=>request<UserSettings>("/api/user/body-images",{method:"POST",body:data}),
  createGarment:(data:FormData)=>request<Garment>("/api/garments",{method:"POST",body:data}),
  generate:(id:string,view?:View)=>request<{garment:Garment;queued_views:string[];cached_views:string[]}>(`/api/garments/${id}/generate${view?`/${view}`:""}`,{method:"POST"}),
  deleteGarment:(id:string)=>request<void>(`/api/garments/${id}`,{method:"DELETE"}),
};
