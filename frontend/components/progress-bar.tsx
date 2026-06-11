"use client";

import { Progress } from "@/components/ui/progress";
import type { Progress as ProgressData } from "@/hooks/use-generation-stream";

interface Props {
  progress: ProgressData | null;
}

export function ProgressBar({ progress }: Props) {
  const pct = progress ? Math.round(progress.percent * 100) : 5;
  const desc = progress?.desc ?? "Warming up…";
  return (
    <div className="space-y-2 rounded-lg border bg-[var(--color-card)] p-4">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium">{desc}</span>
        <span className="tabular-nums text-[var(--color-muted-foreground)]">{pct}%</span>
      </div>
      <Progress value={pct} />
    </div>
  );
}
