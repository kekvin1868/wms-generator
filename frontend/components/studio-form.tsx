"use client";

import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Sparkles, Loader2 } from "lucide-react";
import { GenerateRequestSchema, type GenerateRequest, type Options, type Preset } from "@/lib/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface Props {
  options: Options;
  presets: Preset[];
  onSubmit: (req: GenerateRequest) => void;
  busy: boolean;
}

const FROM_SCRATCH = "— Start from scratch —";

export function StudioForm({ options, presets, onSubmit, busy }: Props) {
  const form = useForm<GenerateRequest>({
    resolver: zodResolver(GenerateRequestSchema),
    defaultValues: {
      model_label: options.models[0],
      bag_type: options.bag_types[0],
      color: "",
      location: options.locations[0],
      lighting: options.lighting[0],
      style: options.styles[0],
      people: options.people[0],
      extra: "",
      aspect: options.aspects[0],
      count: 2,
      seed_text: "",
    },
  });

  function applyPreset(name: string) {
    const p = presets.find((pp) => pp.name === name);
    if (!p || name === FROM_SCRATCH) return;
    if (p.bag_type) form.setValue("bag_type", p.bag_type);
    if (p.color !== undefined) form.setValue("color", p.color);
    if (p.location) form.setValue("location", p.location);
    if (p.lighting) form.setValue("lighting", p.lighting);
    if (p.style) form.setValue("style", p.style);
    if (p.people) form.setValue("people", p.people);
  }

  useEffect(() => {
    if (busy) return;
  }, [busy]);

  return (
    <form
      onSubmit={form.handleSubmit(onSubmit)}
      className="space-y-5 rounded-xl border bg-[var(--color-card)] p-6 shadow-sm"
    >
      <Field label="1. Campaign preset (optional shortcut)">
        <Select onValueChange={applyPreset} defaultValue={FROM_SCRATCH}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            {presets.map((p) => (
              <SelectItem key={p.name} value={p.name}>{p.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>

      <ControllerField name="bag_type" control={form.control} label="2. What kind of bag?">
        {(field) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {options.bag_types.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </ControllerField>

      <Field label="3. Bag color (plain words are fine)">
        <Input
          placeholder="e.g. midnight navy, sand beige"
          {...form.register("color")}
        />
      </Field>

      <ControllerField name="location" control={form.control} label="4. Where is the photo taken?">
        {(field) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {options.locations.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </ControllerField>

      <ControllerField name="lighting" control={form.control} label="5. Lighting">
        {(field) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {options.lighting.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </ControllerField>

      <ControllerField name="style" control={form.control} label="6. Photo style">
        {(field) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {options.styles.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </ControllerField>

      <ControllerField name="people" control={form.control} label="7. People in the shot?">
        {(field) => (
          <Select value={field.value} onValueChange={field.onChange}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {options.people.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </ControllerField>

      <Accordion type="single" collapsible>
        <AccordionItem value="more">
          <AccordionTrigger>More options (you can ignore these)</AccordionTrigger>
          <AccordionContent>
            <Field label="Extra details (optional)">
              <Input
                placeholder="e.g. leather straps, brass zippers"
                {...form.register("extra")}
              />
            </Field>

            <ControllerField name="aspect" control={form.control} label="Image shape">
              {(field) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {options.aspects.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              )}
            </ControllerField>

            <ControllerField name="count" control={form.control} label="How many variations?">
              {(field) => (
                <div className="flex items-center gap-4">
                  <Slider
                    min={1}
                    max={4}
                    step={1}
                    value={[Number(field.value) || 2]}
                    onValueChange={(v) => field.onChange(v[0])}
                    className="flex-1"
                  />
                  <span className="w-8 text-center text-sm font-semibold">{Number(field.value) || 2}</span>
                </div>
              )}
            </ControllerField>

            <Field label="Seed (leave blank for new ideas; enter a number to repeat a result)">
              <Input placeholder="e.g. 42" {...form.register("seed_text")} />
            </Field>

            <ControllerField name="model_label" control={form.control} label="Model">
              {(field) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {options.models.map((v) => <SelectItem key={v} value={v}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              )}
            </ControllerField>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <Button type="submit" size="lg" disabled={busy} className="w-full">
        {busy ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" /> Working…
          </>
        ) : (
          <>
            <Sparkles className="h-5 w-5" /> Create my images
          </>
        )}
      </Button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function ControllerField<T extends keyof GenerateRequest>({
  name,
  control,
  label,
  children,
}: {
  name: T;
  control: ReturnType<typeof useForm<GenerateRequest>>["control"];
  label: string;
  children: (field: { value: GenerateRequest[T]; onChange: (v: GenerateRequest[T]) => void }) => React.ReactNode;
}) {
  return (
    <Field label={label}>
      <Controller
        name={name}
        control={control}
        render={({ field }) =>
          children({
            value: field.value as GenerateRequest[T],
            onChange: field.onChange as (v: GenerateRequest[T]) => void,
          }) as React.ReactElement
        }
      />
    </Field>
  );
}
