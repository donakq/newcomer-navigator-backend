"use client";
import Link from "next/link";
import { useState } from "react";
import OfferForm from "@/components/OfferForm";
import VerticalTimeline from "@/components/VerticalTimeline";
import ProcessingTimesForm from "@/components/ProcessingTimesForm";
import { buildDemoTimeline, formatDate, useDemoProfile, type TimelineWarning } from "@/lib/demo";
import { Panel, PrimaryLink, Shell } from "@/components/Shell";

const riskStyles: Record<TimelineWarning["code"], string> = {
  SEVIS_DATE_UNCONFIRMED: "border-red-300 bg-red-50 text-red-950",
  AT_RISK: "border-amber-300 bg-amber-50 text-amber-950",
  GAP_WARNING: "border-amber-300 bg-amber-50 text-amber-950",
  WINDOW_CLOSED: "border-red-300 bg-red-50 text-red-950",
  CONFLICT: "border-red-300 bg-red-50 text-red-950",
  OUT_OF_SCOPE: "border-red-300 bg-red-50 text-red-950",
  MISSING_INFO: "border-slate-200 bg-slate-50 text-slate-800",
};
function dayCount(date: string): string {
  if (!date) return "Date not confirmed";
  const now = new Date();
  const todayUTC = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const remaining = Math.round((Date.parse(`${date}T00:00:00Z`) - todayUTC) / 86400000);
  return remaining < 0 ? `${-remaining} days ago` : remaining === 0 ? "Today" : `${remaining} days remaining`;
}
export default function TimelinePage() {
  const { profile: savedProfile, plan, ready } = useDemoProfile();
  const [saving, setSaving] = useState(false);
  const [offerPreset, setOfferPreset] = useState<boolean | undefined>(undefined);
  const profile = savedProfile;
  const [edit, setEdit] = useState(true);
  const timeline = buildDemoTimeline(savedProfile, plan);
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
      <div className="mt-5"><OfferForm key={String(offerPreset)} presetHasOffer={offerPreset} onSaved={() => { setEdit(false); setOfferPreset(undefined); }} submitLabel="Calculate My Timeline →" showDsoDate onSavingChange={setSaving} /></div>
    </Panel>}
    {plan && plan.processing.length > 0 && <Panel className="mt-6">
      <h2 className="text-xl font-bold">Processing time estimates</h2>
      <p className="mt-2 mb-4 text-sm text-gray-600">Choose an estimate within each range, or leave it blank to use the default.</p>
      <ProcessingTimesForm key={JSON.stringify(plan.processing.map(item => item.chosen))} items={plan.processing} disabled={saving} />
    </Panel>}
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
        <Link className="mt-3 inline-block text-sm font-bold text-[#336a48] underline" href={`/opt/tasks/${timeline.next.taskId}`}>View this task →</Link>
      </> : <p className="mt-2 text-sm">Add your Program End Date and choose a planning branch.</p>}
    </Panel>}
    <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_285px]">
      <Panel>
        <h2 className="mb-5 text-xl font-bold">Your timeline</h2>
        {!profile.programEndDate || !plan ? <PrimaryLink href="/setup">Finish setting up your plan →</PrimaryLink> : <VerticalTimeline plan={plan} linkTasks notices={false} />}
      </Panel>
      <div className="space-y-6">
        <Panel>
          <h2 className="text-lg font-bold">Your checklist</h2>
          <p className="mt-2 text-sm text-gray-600">Open a milestone to see documents, sources, and the task you can update.</p>
          <Link className="mt-4 inline-block text-sm font-bold text-[#336a48] underline" href="/checklist">Open My Checklist →</Link>
        </Panel>
        {profile.hasOffer !== true && <Panel>
          <h2 className="text-lg font-bold">Have a job offer now?</h2>
          <p className="mt-2 text-sm text-gray-600">Switch to backward planning with an offer start date.</p>
          <button type="button" onClick={() => { setOfferPreset(true); setEdit(true); }} className="mt-3 text-sm font-bold text-[#336a48] underline">I got an offer! →</button>
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

