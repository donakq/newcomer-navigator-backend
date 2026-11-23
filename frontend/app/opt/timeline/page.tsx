"use client";
import Link from "next/link";
import { useState } from "react";
import type { ApiProcessingTime } from "@/lib/api";
import { actions, buildDemoTimeline, formatDate, useDemoProfile, type Profile, type TimelineWarning } from "@/lib/demo";
import { Field, inputClass, Panel, PrimaryLink, Shell } from "@/components/Shell";

const riskStyles: Record<TimelineWarning["code"], string> = {
  SEVIS_DATE_UNCONFIRMED: "border-red-300 bg-red-50 text-red-950",
  AT_RISK: "border-amber-300 bg-amber-50 text-amber-950",
  GAP_WARNING: "border-amber-300 bg-amber-50 text-amber-950",
  WINDOW_CLOSED: "border-red-300 bg-red-50 text-red-950",
  CONFLICT: "border-red-300 bg-red-50 text-red-950",
  OUT_OF_SCOPE: "border-red-300 bg-red-50 text-red-950",
  MISSING_INFO: "border-slate-200 bg-slate-50 text-slate-800",
};
const labelStyles: Record<string, string> = {
  "Federal deadline": "border-red-200 bg-red-50 text-red-800",
  School: "border-sky-200 bg-sky-50 text-sky-800",
  Recommended: "border-green-200 bg-green-50 text-green-800",
  Estimate: "border-violet-200 bg-violet-50 text-violet-800",
  "Not confirmed": "border-slate-200 bg-slate-100 text-slate-700",
  "Your choice": "border-amber-200 bg-amber-50 text-amber-800",
};
function dayCount(date: string): string {
  if (!date) return "Date not confirmed";
  const now = new Date();
  const todayUTC = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const remaining = Math.round((Date.parse(`${date}T00:00:00Z`) - todayUTC) / 86400000);
  return remaining < 0 ? `${-remaining} days ago` : remaining === 0 ? "Today" : `${remaining} days remaining`;
}
export default function TimelinePage() {
  const { profile: savedProfile, plan, ready, error: loadError } = useDemoProfile();
  const [draft, setDraft] = useState<Partial<Profile>>({});
  const [saving, setSaving] = useState(false);
  const [processingSaving, setProcessingSaving] = useState(false);
  const [error, setError] = useState("");
  const profile = { ...savedProfile, ...draft };
  const [edit, setEdit] = useState(true);
  const timeline = buildDemoTimeline(savedProfile, plan);
  function change<K extends keyof Profile>(key: K, value: Profile[K]) {
    setDraft(current => ({ ...current, [key]: value }));
  }
  async function calculate() {
    setSaving(true);
    setError("");
    try {
      await actions.calculateTimeline(profile);
      setDraft({});
      setEdit(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }
  const selectedBranch = profile.hasOffer === true ? "Backward plan · offer" : profile.hasOffer === false ? "Forward plan · no offer" : "Choose planning branch";
  return <Shell wide>
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p className="text-sm font-bold tracking-wider text-[#336a48]">APPLICATION TIMELINE · STEP 3 OF 3</p>
        <h1 className="mt-2 text-4xl font-bold">Your OPT timeline</h1>
        <p className="mt-3 max-w-2xl text-gray-600">Plan with or without an offer, see what is confirmed, and identify which task to complete next.</p>
      </div>
      <button type="button" className="rounded-xl border border-[#b9cfbd] px-4 py-2 text-sm font-semibold text-[#336a48]" onClick={() => setEdit(!edit)}>{edit ? "Hide inputs" : "Edit dates"}</button>
    </div>
    <Panel className="mt-7">
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-600">
        <span><strong>UW · {profile.degree}</strong></span>
        <span>Program ends: <strong>{formatDate(profile.programEndDate)}</strong></span>
        <span>Stage: <strong>{profile.stage.replaceAll("_", " ")}</strong></span>
        <span className="font-semibold text-[#336a48]">{selectedBranch}</span>
      </div>
      <Link className="mt-3 inline-block text-sm text-[#336a48] underline" href="/home">Edit your profile →</Link>
    </Panel>
    {edit && <Panel className="mt-6">
      <h2 className="text-xl font-bold">Plan your next steps</h2>
      <fieldset disabled={!ready || saving} className="mt-5 grid gap-5 sm:grid-cols-2">
        <Field label="Do you have a job offer with a start date?">
          <select className={inputClass} value={profile.hasOffer === null ? "" : profile.hasOffer ? "yes" : "no"} onChange={e => change("hasOffer", e.target.value === "" ? null : e.target.value === "yes")}>
            <option value="">Choose</option><option value="yes">Yes</option><option value="no">No</option>
          </select>
        </Field>
        {profile.hasOffer === true && <>
          <Field label="Offer start date"><input type="date" className={inputClass} value={profile.offerStartDate} onChange={e => change("offerStartDate", e.target.value)} /></Field>
          <Field label="Is your start date flexible?"><select className={inputClass} value={profile.startFlexible} onChange={e => change("startFlexible", e.target.value as Profile["startFlexible"])}><option value="yes">Yes</option><option value="no">No</option><option value="unsure">Not sure</option></select></Field>
        </>}
        {profile.hasOffer === false && <>
          <Field label="Preferred OPT start"><select className={inputClass} value={profile.startPreference} onChange={e => change("startPreference", e.target.value as Profile["startPreference"])}><option value="ASAP">As soon as possible</option><option value="SPECIFIC">Specific date</option><option value="UNSURE">Not sure</option></select></Field>
          {profile.startPreference === "SPECIFIC" && <Field label="Preferred start date"><input type="date" className={inputClass} value={profile.preferredStartDate} onChange={e => change("preferredStartDate", e.target.value)} /></Field>}
        </>}
        <Field label="Plan to use premium processing?"><select className={inputClass} value={profile.premiumIntent} onChange={e => change("premiumIntent", e.target.value as Profile["premiumIntent"])}><option value="unsure">Not sure</option><option value="yes">Yes</option><option value="no">No</option></select></Field>
        {(profile.stage === "I20_RECEIVED" || !!profile.dsoRecDate) && <Field label="DSO recommendation date (SEVIS)" hint="Confirm the SEVIS date with UW ISS. The I-20 issue date may differ."><input type="date" className={inputClass} value={profile.dsoRecDate} onChange={e => change("dsoRecDate", e.target.value)} /></Field>}
      </fieldset>
      {profile.hasOffer === false && <p className="mt-4 rounded-lg bg-[#eef4ef] p-4 text-sm leading-relaxed text-[#31533f]">Choosing an earlier requested OPT start date may permit an earlier start once authorized, but can also begin the unemployment-day period sooner. A later date may reduce that exposure but delays possible work authorization. Confirm your choice with UW ISS.</p>}
      <button type="button" onClick={calculate} disabled={!ready || saving || processingSaving} className="mt-6 rounded-xl bg-[#336a48] px-6 py-3 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Calculating…" : "Calculate My Timeline →"}</button>
      {(error || loadError) && <p role="alert" className="mt-3 text-sm text-red-700">{error || loadError}</p>}
    </Panel>}
    {plan && plan.processing.length > 0 && <ProcessingTimes
      key={JSON.stringify(plan.processing.map(item => item.chosen))}
      items={plan.processing}
      timelineSaving={saving}
      onSavingChange={setProcessingSaving}
    />}
    {ready && timeline.warnings.length > 0 && <div className="mt-6 space-y-3" aria-label="Timeline notices">
      {timeline.warnings.map((warning, i) => <div key={`${warning.code}-${i}`} role="status" className={`rounded-xl border p-4 ${riskStyles[warning.code]}`}>
        <div className="text-xs font-bold tracking-wide">{warning.code.replaceAll("_", " ")}</div>
        <p className="mt-1 text-sm">{warning.message}</p>
        <div className="mt-2 text-sm font-semibold">Next action: {warning.taskId ? <Link href={`/opt/tasks/${warning.taskId}`} className="underline">{warning.action} →</Link> : warning.action}</div>
      </div>)}
    </div>}
    {ready && <Panel className="mt-6 border-[#bed6c5] bg-[#f7faf7]">
      <p className="text-xs font-bold uppercase tracking-wide text-[#366e4b]">Your next step</p>
      {timeline.blocked ? <><h2 className="mt-2 text-lg font-bold">Resolve a date or eligibility conflict</h2><p className="mt-2 text-sm text-gray-600">A conflict or closed window prevents this demo from suggesting actionable filing dates. Check the warnings above and contact UW ISS.</p></> : timeline.next ? <>
        <h2 className="mt-2 text-lg font-bold">{timeline.next.label}</h2>
        <p className="mt-1 text-sm text-gray-600">{timeline.next.date ? `${formatDate(timeline.next.date)} · ${dayCount(timeline.next.date)}` : "Date not confirmed"} · {timeline.next.kind}</p>
        <Link className="mt-3 inline-block text-sm font-bold text-[#336a48] underline" href={`/opt/tasks/${timeline.next.taskId}`}>View task {timeline.next.taskId} →</Link>
      </> : <p className="mt-2 text-sm">Add your Program End Date and choose a planning branch.</p>}
    </Panel>}
    <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_285px]">
      <Panel>
        <h2 className="text-xl font-bold">Timeline milestones</h2>
        <p className="mt-2 text-xs text-gray-500">Dated milestones appear in chronological order. Milestones with unknown dates follow their prerequisites when possible.</p>
        {!profile.programEndDate ? <div className="mt-5"><PrimaryLink href="/onboarding">Set Program End Date →</PrimaryLink></div> : <ol className="mt-6 space-y-3">
          {timeline.nodes.map(node => <li key={node.id} className="border-l-[3px] border-[#bcd0be] pb-4 pl-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Link href={`/opt/tasks/${node.taskId}`} className="font-semibold text-[#2f5145] underline-offset-2 hover:underline">{node.label} ↗</Link>
              <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${labelStyles[node.kind]}`}>{node.kind}</span>
            </div>
            <div className="mt-1 text-lg font-bold">{node.date ? `${node.kind === "Estimate" ? "~" : ""}${formatDate(node.date)}` : node.dateState === "CONFLICT" ? "Unavailable · conflict" : "Not confirmed"}</div>
            <p className="mt-1 text-xs leading-relaxed text-gray-600">{node.note}</p>
          </li>)}
        </ol>}
      </Panel>
      <div className="space-y-6">
        <Panel>
          <h2 className="text-lg font-bold">Date labels</h2>
          <ul className="mt-4 space-y-3 text-sm">{["Federal deadline", "School", "Recommended", "Estimate", "Not confirmed", "Your choice"].map(k => <li key={k}><span className={`inline-block rounded-full border px-3 py-1 text-xs font-semibold ${labelStyles[k]}`}>{k}</span></li>)}</ul>
          <p className="mt-3 text-xs text-gray-500">Federal boundaries, school planning targets, estimates, and choices are different kinds of dates. Color is not the only indicator.</p>
        </Panel>
        <Panel>
          <h2 className="text-lg font-bold">Your checklist</h2>
          <p className="mt-2 text-sm text-gray-600">Open a milestone to see documents, sources, and the task you can update.</p>
          <Link className="mt-4 inline-block text-sm font-bold text-[#336a48] underline" href="/checklist">Open My Checklist →</Link>
        </Panel>
        {profile.hasOffer !== true && <Panel>
          <h2 className="text-lg font-bold">Have a job offer now?</h2>
          <p className="mt-2 text-sm text-gray-600">Switch to backward planning with an offer start date.</p>
          <button type="button" onClick={() => { change("hasOffer", true); setEdit(true); }} className="mt-3 text-sm font-bold text-[#336a48] underline">I got an offer! →</button>
        </Panel>}
      </div>
    </div>
    {!!plan?.warnings.length && <Panel className="mt-6">
      <h2 className="text-lg font-bold">Policy notes</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-gray-600">{plan.warnings.map(note => <li key={note}>{note}</li>)}</ul>
    </Panel>}
    <p className="mt-7 text-xs leading-relaxed text-gray-500">This timeline is for informational purposes only and is not legal advice. Dates are based on the information you provide and may require confirmation by UW ISS or USCIS.</p>
  </Shell>;
}

function ProcessingTimes({ items, timelineSaving, onSavingChange }: {
  items: ApiProcessingTime[];
  timelineSaving: boolean;
  onSavingChange: (saving: boolean) => void;
}) {
  const [choices, setChoices] = useState<Partial<Record<ApiProcessingTime["id"], string>>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    onSavingChange(true);
    setError("");
    const payload = Object.fromEntries(items.map(item => {
      const value = choices[item.id];
      return [item.id, value === undefined ? item.chosen : value === "" ? null : Number(value)];
    }));
    try {
      await actions.saveProcessingTimes(payload);
      setChoices({});
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
      onSavingChange(false);
    }
  }

  return <Panel className="mt-6">
    <h2 className="text-xl font-bold">Processing time estimates</h2>
    <p className="mt-2 text-sm text-gray-600">Choose an estimate within each range, or leave it blank to use the default.</p>
    <form onSubmit={submit}>
      <fieldset disabled={saving || timelineSaving} className="mt-4 grid gap-5 sm:grid-cols-3">
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
      <button type="submit" disabled={saving || timelineSaving || Object.keys(choices).length === 0} className="mt-5 rounded-xl border border-[#336a48] px-4 py-2 text-sm font-semibold text-[#336a48] disabled:opacity-50">{saving ? "Saving…" : "Save processing times"}</button>
      {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
    </form>
  </Panel>;
}
