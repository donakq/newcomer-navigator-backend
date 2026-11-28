"use client";
import Link from "next/link";
import { useState } from "react";
import OfferForm from "@/components/OfferForm";
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

