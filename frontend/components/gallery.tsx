"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import type { GeneratedImage } from "@/lib/schemas";

interface Props {
  images: GeneratedImage[];
  prompt?: string;
}

export function Gallery({ images, prompt }: Props) {
  const [open, setOpen] = useState<GeneratedImage | null>(null);

  if (images.length === 0) {
    return (
      <div className="flex h-[420px] items-center justify-center rounded-xl border border-dashed text-sm text-[var(--color-muted-foreground)]">
        Your images will appear here.
      </div>
    );
  }

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {images.map((img) => (
          <button
            key={img.filename}
            type="button"
            onClick={() => setOpen(img)}
            className="group overflow-hidden rounded-lg border bg-[var(--color-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={img.url}
              alt={img.filename}
              className="aspect-square w-full object-cover transition-transform group-hover:scale-[1.02]"
            />
          </button>
        ))}
      </div>

      <Dialog open={!!open} onOpenChange={(v) => !v && setOpen(null)}>
        <DialogContent>
          {open && (
            <>
              <DialogTitle className="text-base font-semibold">{open.filename}</DialogTitle>
              <DialogDescription className="text-xs text-[var(--color-muted-foreground)]">
                Seed: {open.seed}
              </DialogDescription>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={open.url} alt={open.filename} className="max-h-[70vh] w-full rounded-md object-contain" />
              {prompt && (
                <p className="mt-2 text-xs leading-relaxed text-[var(--color-muted-foreground)]">
                  <span className="font-medium text-[var(--color-foreground)]">Prompt:</span> {prompt}
                </p>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
