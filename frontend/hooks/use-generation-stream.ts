"use client";

import { useCallback, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { GeneratedImage, GenerateRequest } from "@/lib/schemas";

export interface Progress {
  step: number;
  total: number;
  percent: number;
  desc: string;
}

export interface DoneResult {
  images: GeneratedImage[];
  seed_used: number;
  prompt: string;
}

export type StreamState =
  | { phase: "idle" }
  | { phase: "running"; progress: Progress | null }
  | { phase: "done"; result: DoneResult }
  | { phase: "error"; message: string };

export function useGenerationStream() {
  const [state, setState] = useState<StreamState>({ phase: "idle" });
  const sourceRef = useRef<EventSource | null>(null);

  const cancel = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  const start = useCallback(async (req: GenerateRequest) => {
    cancel();
    setState({ phase: "running", progress: null });
    try {
      const { job_id } = await api.submit(req);
      const es = new EventSource(`/api/generate/${job_id}/stream`);
      sourceRef.current = es;

      es.addEventListener("progress", (ev) => {
        const data = JSON.parse((ev as MessageEvent).data) as Progress;
        setState({ phase: "running", progress: data });
      });
      es.addEventListener("done", (ev) => {
        const data = JSON.parse((ev as MessageEvent).data) as DoneResult;
        setState({ phase: "done", result: data });
        es.close();
        sourceRef.current = null;
      });
      es.addEventListener("error", (ev) => {
        const raw = (ev as MessageEvent).data;
        let message = "Stream interrupted";
        if (raw) {
          try {
            message = (JSON.parse(raw) as { message: string }).message;
          } catch {
            message = String(raw);
          }
        }
        setState({ phase: "error", message });
        es.close();
        sourceRef.current = null;
      });
    } catch (err) {
      setState({ phase: "error", message: (err as Error).message });
    }
  }, [cancel]);

  return { state, start, cancel };
}
