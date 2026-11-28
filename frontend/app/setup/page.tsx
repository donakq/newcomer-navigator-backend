"use client";
import { useEffect, useLayoutEffect, useState, type ReactNode } from "react";
import { Field, inputClass, Panel, PrimaryLink, Shell } from "@/components/Shell";
import OfferForm from "@/components/OfferForm";
import ProcessingTimesForm from "@/components/ProcessingTimesForm";
import VerticalTimeline from "@/components/VerticalTimeline";
import { actions, refresh, useDemoProfile, type Profile, type SetupStep, type Stage } from "@/lib/demo";

// Six steps (design 2026-11-27). Steps 1–4 are required; 5 (processing times) can be skipped; 6 is the review.
const TITLES = ["School & program", "Your OPT path", "Where you are now", "Job offer and start date", "Processing times", "Your timeline"];
const RESUME_AT: Record<SetupStep, number> = { program: 1, opt: 2, progress: 3, offer: 4, done: 6 };
const button = "rounded-xl bg-[#336a48] px-6 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40";

export default function Setup() {
  const { profile, plan, ready, onboarded, setupStep, error } = useDemoProfile();
  const [step, setStep] = useState<number | null>(null);
  // Next keeps this page mounted while hidden: forget the step so a later visit resumes from saved data.
  useLayoutEffect(() => () => setStep(null), []);
  useEffect(() => { if (ready && step === null) setStep(RESUME_AT[setupStep]); }, [ready, step, setupStep]);

  if (!ready || step === null) return <Shell showNav={false}><p role="status">Loading your answers…</p></Shell>;
  const next = () => setStep(s => Math.min((s ?? 1) + 1, 6));

  return <Shell showNav={false} wide={step === 6}><div className={step === 6 ? "" : "mx-auto max-w-2xl"}>
    <p className="text-sm font-bold tracking-wider text-[#336a48]">SET UP YOUR PLAN · STEP {step} OF 6</p>
    <h1 className="mt-3 text-4xl font-bold">{TITLES[step - 1]}</h1>
    <div className="mt-4 flex gap-1" aria-hidden>{TITLES.map((_, i) => <span key={i} className={`h-1.5 flex-1 rounded-full ${i < step ? "bg-[#336a48]" : "bg-[#e1e7df]"}`} />)}</div>
    {step > 1 && <button type="button" onClick={() => setStep(step - 1)} className="mt-5 text-sm text-[#336a48]">← Back</button>}
    <Panel className="mt-5">
      {step === 1 && <ProgramStep profile={profile} onboarded={onboarded} onNext={next} />}
      {step === 2 && <OptStep profile={profile} onNext={next} />}
      {step === 3 && <ProgressStep profile={profile} onNext={next} />}
      {step === 4 && <><p className="mb-5 text-sm text-gray-600">With an offer we plan backward from your start date; without one we plan forward from the filing window.</p><OfferForm onSaved={next} submitLabel="Save & continue →" /></>}
      {step === 5 && plan && <><p className="mb-5 text-sm text-gray-600">We use the slowest official times unless you choose otherwise. You can change these later on your timeline.</p><ProcessingTimesForm items={plan.processing} onSaved={next} onSkip={next} /></>}
      {step >= 5 && !plan && <div role="alert" className="text-sm text-red-700">We couldn&apos;t calculate your plan{error ? `: ${error}` : "."} Go back and check your dates, or <button type="button" onClick={() => refresh()} className="font-semibold underline">try again</button>.</div>}
      {step === 6 && plan && <>
        <p className="mb-6 text-sm text-gray-600">Here is your plan. Colored ranges show what to confirm with UW ISS, what is an estimate, and which dates we still need from you.</p>
        <VerticalTimeline plan={plan} />
        <div className="mt-8"><PrimaryLink href="/checklist">Go to My Checklist →</PrimaryLink></div>
      </>}
    </Panel>
  </div></Shell>;
}

function useSubmit(onNext: () => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(fn: () => Promise<void>) {
    setBusy(true); setError("");
    try { await fn(); onNext(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }
  return { busy, error, setError, run };
}

function Errors({ error }: { error: string }): ReactNode {
  return error ? <p role="alert" className="text-sm text-red-700">{error}</p> : null;
}

function ProgramStep({ profile, onboarded, onNext }: { profile: Profile; onboarded: boolean; onNext: () => void }) {
  const [end, setEnd] = useState(profile.programEndDate);
  const [degree, setDegree] = useState<Profile["degree"]>(profile.degree);
  const { busy, error, setError, run } = useSubmit(onNext);
  return <form className="space-y-5" onSubmit={e => {
    e.preventDefault();
    if (!end) { setError("Please enter your Program End Date."); return; }
    run(() => onboarded ? actions.updateProgram(end, degree) : actions.onboard(end, degree));
  }}>
    <Field label="School"><select className={inputClass} value="uw" disabled><option value="uw">University of Washington (UW)</option></select></Field>
    <Field label="Degree level"><select className={inputClass} value={degree} onChange={e => setDegree(e.target.value as Profile["degree"])}><option>Bachelor</option><option>Master</option><option>PhD</option></select></Field>
    <Field label="Program End Date" hint="Use the Program End Date shown on your current Form I-20."><input required type="date" className={inputClass} value={end} onChange={e => setEnd(e.target.value)} /></Field>
    <Errors error={error} />
    <button disabled={busy} className={button}>Continue →</button>
  </form>;
}

function OptStep({ profile, onNext }: { profile: Profile; onNext: () => void }) {
  const [intent, setIntent] = useState(profile.optIntent || "AFTER_GRADUATION");
  const [first, setFirst] = useState<"yes" | "no" | "">(profile.firstTime === true ? "yes" : profile.firstTime === false ? "no" : "");
  const { busy, error, run } = useSubmit(onNext);
  const inScope = intent === "AFTER_GRADUATION" && first === "yes";
  return <form className="space-y-5" onSubmit={e => { e.preventDefault(); if (inScope) run(() => actions.selectOpt("AFTER_GRADUATION", true)); }}>
    <Field label="When do you plan to use OPT?"><select className={inputClass} value={intent} onChange={e => setIntent(e.target.value)}><option value="AFTER_GRADUATION">After I graduate</option><option value="WHILE_STUDYING">While I&apos;m still studying</option><option value="STEM_EXTENSION">I&apos;m on OPT and want a STEM extension</option><option value="NOT_SURE">I&apos;m not sure</option></select></Field>
    {intent !== "AFTER_GRADUATION"
      ? <div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950">{intent === "NOT_SURE" ? "Post-completion OPT is typically used after finishing your program; pre-completion OPT is during study; STEM OPT is a possible extension. Confirm which applies with UW ISS." : "This pathway is coming soon in this MVP."} <a href="https://iss.washington.edu/f1-employment/" target="_blank" rel="noreferrer" className="font-bold underline">UW ISS guidance ↗</a></div>
      : <Field label="Is this your first post-completion OPT application at this degree level?"><select className={inputClass} value={first} onChange={e => setFirst(e.target.value as "yes" | "no")}><option value="">Choose an answer</option><option value="yes">Yes</option><option value="no">No</option></select></Field>}
    {intent === "AFTER_GRADUATION" && first === "no" && <div className="rounded-xl bg-amber-50 p-4 text-sm">This situation is outside the demo&apos;s supported scope. Please check with <a className="underline" href="https://iss.washington.edu/" target="_blank" rel="noreferrer">UW ISS</a>.</div>}
    <Errors error={error} />
    <button disabled={!inScope || busy} className={button}>Continue →</button>
  </form>;
}

function ProgressStep({ profile, onNext }: { profile: Profile; onNext: () => void }) {
  const [stage, setStage] = useState<Stage>(profile.stage);
  const [requestDate, setRequestDate] = useState(profile.i20RequestDate);
  const [recDate, setRecDate] = useState(profile.dsoRecDate);
  const [issueDate, setIssueDate] = useState(profile.i20IssueDate);
  const [receiptDate, setReceiptDate] = useState(profile.uscisReceiptDate);
  const [requestedStart, setRequestedStart] = useState(profile.requestedStartDate);
  const { busy, error, setError, run } = useSubmit(onNext);
  const date = (value: string, set: (v: string) => void, required = false) => <input type="date" required={required} className={inputClass} value={value} onChange={e => set(e.target.value)} />;
  return <form className="space-y-5" onSubmit={e => {
    e.preventDefault();
    if (stage === "I20_RECEIVED" && !recDate) { setError("Please enter the date your DSO recorded the recommendation in SEVIS."); return; }
    if (stage === "I765_FILED" && (!receiptDate || !requestedStart)) { setError("Receipt date and requested OPT start date are required for this stage."); return; }
    run(() => actions.saveStatus(stage, { i20RequestDate: requestDate, dsoRecDate: recDate, i20IssueDate: issueDate, uscisReceiptDate: receiptDate, requestedStartDate: requestedStart }));
  }}>
    <Field label="Your OPT stage"><select value={stage} onChange={e => { setStage(e.target.value as Stage); setError(""); }} className={inputClass}><option value="PLANNING">I haven&apos;t started</option><option value="I20_REQUESTED">I&apos;ve requested my OPT I-20</option><option value="I20_RECEIVED">I&apos;ve received my OPT I-20</option><option value="I765_FILED">I&apos;ve filed my I-765</option><option value="APPROVED">My OPT is approved</option></select></Field>
    {stage === "I20_REQUESTED" && <Field label="Date you requested your OPT I-20 (optional)" hint="Find this in your school's submission record.">{date(requestDate, setRequestDate)}</Field>}
    {stage === "I20_RECEIVED" && <Field label="DSO recommendation date in SEVIS (required)" hint="Confirm the actual SEVIS recommendation date with your DSO; it may differ from the I-20 issue date.">{date(recDate, setRecDate, true)}</Field>}
    {(stage === "I20_REQUESTED" || stage === "I20_RECEIVED") && <Field label="OPT I-20 Date Issued (optional)" hint="Find the Date Issued next to the DSO signature on page 1 of your OPT I-20.">{date(issueDate, setIssueDate)}</Field>}
    {stage === "I765_FILED" && <><Field label="USCIS receipt date (required)" hint="Refer to your Form I-797C receipt notice.">{date(receiptDate, setReceiptDate, true)}</Field><Field label="Requested OPT start date (required)">{date(requestedStart, setRequestedStart, true)}</Field></>}
    {stage === "APPROVED" && <p className="rounded-xl bg-[#f1f5f0] p-4 text-sm">Post-approval obligations are planned for a future version. See <a href="https://iss.washington.edu/f1-employment/post-completion/" target="_blank" rel="noreferrer" className="font-semibold underline">UW ISS official guidance</a>.</p>}
    <Errors error={error} />
    <button disabled={busy} className={button}>Continue →</button>
  </form>;
}
