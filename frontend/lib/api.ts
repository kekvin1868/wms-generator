import type { GenerateRequest, HistoryItem, Options, Preset } from "./schemas";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  options: () => jsonFetch<Options>("/api/options"),
  presets: () => jsonFetch<Preset[]>("/api/presets"),
  history: () => jsonFetch<HistoryItem[]>("/api/history"),
  submit: (body: GenerateRequest) =>
    jsonFetch<{ job_id: string }>("/api/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
