import { z } from "zod";

export const GenerateRequestSchema = z.object({
  model_label: z.string().min(1),
  bag_type: z.string().min(1),
  color: z.string().default(""),
  location: z.string().min(1),
  lighting: z.string().min(1),
  style: z.string().min(1),
  people: z.string().min(1),
  extra: z.string().default(""),
  aspect: z.string().min(1),
  count: z.coerce.number().int().min(1).max(4).default(2),
  seed_text: z.string().default(""),
});

export type GenerateRequest = z.infer<typeof GenerateRequestSchema>;

export interface Options {
  models: string[];
  aspects: string[];
  bag_types: string[];
  locations: string[];
  lighting: string[];
  styles: string[];
  people: string[];
}

export interface Preset {
  name: string;
  bag_type?: string;
  color?: string;
  location?: string;
  lighting?: string;
  style?: string;
  people?: string;
}

export interface GeneratedImage {
  filename: string;
  url: string;
  seed: number;
}

export interface HistoryItem {
  filename: string;
  url: string;
  prompt: string | null;
  seed: number | null;
  model: string | null;
  created_at: number;
}
