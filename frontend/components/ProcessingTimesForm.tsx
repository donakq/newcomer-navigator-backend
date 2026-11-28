"use client";
import { useState } from "react";
import type { ApiProcessingTime } from "@/lib/api";
import { actions } from "@/lib/demo";
import { Field, inputClass } from "@/components/Shell";

/** The student's own processing-time estimates. Used by /setup Step 5, the timeline range editor and /opt/timeline. */
export default function ProcessingTimesForm({ items, disabled = false, onSavingChange, onSaved, onSkip }: {
  items: ApiProcessingTime[];
  disabled?: boolean;
  onSavingChange?: (saving: boolean) => void;
  onSaved?: () => void;
  onSkip?: () => void;  // shows a "Skip" button (setup wizard)
}) {
  const [choices, setChoices] = useState<Partial<Record<ApiProcessingTime["id"], string>>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true); onSavingChange?.(true); setError("");
    const payload = Object.fromEntries(items.map(item => {
      const value = choices[item.id];
      return [item.id, value === undefined ? item.chosen : value === "" ? null : Number(value)];
    }));
    try {
      await actions.saveProcessingTimes(payload);
      setChoices({});
      onSaved?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false); onSavingChange?.(false);
    }
  }

  return <form onSubmit={submit}>
    <fieldset disabled={saving || disabled} className="grid gap-5 sm:grid-cols-3">
      {items.map(item => {
        const unit = item.unit.replaceAll("_", " ");
        return <div key={item.id}>
          <Field label={item.label} hint={item.min + "–" + item.max + " " + unit + " · Default " + item.default + " · Plan uses " + item.used}>
            <input type="number" className={inputClass} min={item.min} max={item.max} step={1}
              placeholder={String(item.default)} value={choices[item.id] ?? item.chosen ?? ""}
              onChange={event => {
                const value = event.target.value;
                setChoices(current => ({ ...current, [item.id]: value }));
              }} />
          </Field>
          {item.note && <p className="mt-2 text-xs text-gray-600">{item.note}</p>}
        </div>;
      })}
    </fieldset>
    <div className="mt-5 flex flex-wrap gap-3">
      <button type="submit" disabled={saving || disabled || Object.keys(choices).length === 0} className="rounded-xl border border-[#336a48] px-4 py-2 text-sm font-semibold text-[#336a48] disabled:opacity-50">{saving ? "Saving…" : "Save processing times"}</button>
      {onSkip && <button type="button" onClick={onSkip} disabled={saving} className="rounded-xl px-4 py-2 text-sm font-semibold text-[#336a48] underline disabled:opacity-50">Skip — use the defaults</button>}
    </div>
    {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
  </form>;
}
