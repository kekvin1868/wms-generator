"use client";

import { useQuery } from "@tanstack/react-query";
import { History, Copy } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function HistoryDrawer() {
  const { data, refetch, isFetching } = useQuery({
    queryKey: ["history"],
    queryFn: api.history,
  });

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" onClick={() => refetch()}>
          <History className="h-4 w-4" /> History
        </Button>
      </SheetTrigger>
      <SheetContent side="right">
        <SheetTitle className="text-lg font-semibold">Past runs</SheetTitle>
        <p className="mb-3 text-xs text-[var(--color-muted-foreground)]">
          Files in your <code>outputs/</code> folder. {isFetching && "Refreshing…"}
        </p>
        <div className="space-y-3 overflow-y-auto pr-1" style={{ maxHeight: "calc(100vh - 130px)" }}>
          {(data ?? []).map((h) => (
            <div key={h.filename} className="flex gap-3 rounded-lg border p-2">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={h.url} alt={h.filename} className="h-20 w-20 rounded object-cover" />
              <div className="min-w-0 flex-1 space-y-1">
                <div className="truncate text-xs font-medium">{h.filename}</div>
                {h.seed != null && (
                  <div className="flex items-center gap-2 text-xs text-[var(--color-muted-foreground)]">
                    <span>Seed: {h.seed}</span>
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-[var(--color-primary)] hover:underline"
                      onClick={() => navigator.clipboard.writeText(String(h.seed))}
                    >
                      <Copy className="h-3 w-3" /> copy
                    </button>
                  </div>
                )}
                {h.model && (
                  <div className="text-xs text-[var(--color-muted-foreground)]">Model: {h.model}</div>
                )}
              </div>
            </div>
          ))}
          {data && data.length === 0 && (
            <p className="text-sm text-[var(--color-muted-foreground)]">No images yet.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
