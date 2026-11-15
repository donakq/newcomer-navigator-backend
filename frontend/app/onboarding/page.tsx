"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
import { actions, type Profile } from "@/lib/demo";
export default function Onboarding() {
  const router = useRouter(); const [programEndDate, setP] = useState(""); const [degree, setDegree] = useState<Profile["degree"]>("Master");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!programEndDate) { setErr("Please enter your Program End Date."); return; }
    setBusy(true); setErr("");
    try { await actions.onboard(programEndDate, degree); router.push("/checklist"); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }
  return <Shell><div className="mx-auto max-w-2xl"><p className="text-sm font-bold tracking-wider text-[#346b48]">STEP 2 · ONBOARDING</p><h1 className="mt-3 text-4xl font-bold">Tell us about your program</h1><p className="mt-3 text-gray-600">We'll use this information to shape your OPT journey. The v1 demo supports University of Washington.</p><Panel className="mt-8"><form className="space-y-5" onSubmit={submit}><Field label="School"><select className={inputClass} value="uw" disabled><option value="uw">University of Washington (UW)</option></select></Field><Field label="Program End Date" hint="Use the Program End Date shown on your current Form I-20."><input required type="date" className={inputClass} value={programEndDate} onChange={e=>setP(e.target.value)}/></Field><Field label="Degree level"><select className={inputClass} value={degree} onChange={e=>setDegree(e.target.value as Profile["degree"])}><option>Bachelor</option><option>Master</option><option>PhD</option></select></Field>{err&&<p role="alert" className="text-red-700">{err}</p>}<button disabled={busy} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">Continue to My Checklist →</button></form></Panel></div></Shell>;
}
