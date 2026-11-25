import type {
  GenerateRequest,
  HistoryItem,
  Options,
  Preset,
  VideoForm,
  VideoJob,
  VideoQuota,
} from "./schemas";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = text;
    try {
      const d = JSON.parse(text).detail;
      if (d) detail = typeof d === "string" ? d : JSON.stringify(d);
    } catch {}
    throw new Error(detail);
  }
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
  videoQuota: () => jsonFetch<VideoQuota>("/api/video/quota"),
  videoSubmit: (body: VideoForm) =>
    jsonFetch<VideoJob>("/api/video", { method: "POST", body: JSON.stringify(body) }),
  videoStatus: (jobId: string) => jsonFetch<VideoJob>(`/api/video/${jobId}`),
};
