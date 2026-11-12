"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
import { useDemoProfile } from "@/lib/demo";
export default function Onboarding() {
  const router = useRouter(); const {profile, save, ready} = useDemoProfile(); const [err,setErr]=useState("");
  return <Shell><div className="mx-auto max-w-2xl"><p className="text-sm font-bold tracking-wider text-[#346b48]">STEP 2 · ONBOARDING</p><h1 className="mt-3 text-4xl font-bold">Tell us about your program</h1><p className="mt-3 text-gray-600">We'll use this information to shape your OPT journey. The v1 demo supports University of Washington.</p><Panel className="mt-8"><form className="space-y-5" onSubmit={e=>{e.preventDefault();if(!profile.programEndDate){setErr("Please enter your Program End Date.");return;} router.push("/checklist");}}><Field label="School"><select className={inputClass} value="uw" disabled><option value="uw">University of Washington (UW)</option></select></Field><Field label="Program End Date" hint="Use the Program End Date shown on your current Form I-20."><input required type="date" className={inputClass} value={profile.programEndDate} onChange={e=>save({programEndDate:e.target.value})}/></Field><Field label="Degree level"><select className={inputClass} value={profile.degree} onChange={e=>save({degree:e.target.value as "Bachelor"|"Master"|"PhD"})}><option>Bachelor</option><option>Master</option><option>PhD</option></select></Field>{err&&<p role="alert" className="text-red-700">{err}</p>}<button disabled={!ready} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">Continue to My Checklist →</button></form></Panel></div></Shell>;
}
