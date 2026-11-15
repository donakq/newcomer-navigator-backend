"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
import { actions, useDemoProfile } from "@/lib/demo";
export default function SelectOPT() {
  const {profile,ready}=useDemoProfile(); const router=useRouter(); const [error,setError]=useState("");
  const [intent,setIntent]=useState("AFTER_GRADUATION");
  const [first,setFirst]=useState<"yes"|"no"|"">(profile.firstTime===true?"yes":profile.firstTime===false?"no":"");
  useEffect(() => { if (ready) { setFirst(profile.firstTime===true?"yes":profile.firstTime===false?"no":""); setIntent(profile.optIntent||"AFTER_GRADUATION"); } }, [ready]);
  const isValid=intent==="AFTER_GRADUATION"&&first==="yes";
  return <Shell><Link href="/checklist" className="text-sm text-[#336a48]">← My Checklist</Link><div className="mt-7 max-w-2xl"><p className="text-sm font-bold tracking-wider text-[#336a48]">SELECT OPT · STEP 1 OF 3</p><h1 className="mt-3 text-4xl font-bold">Confirm your OPT path</h1><p className="mt-3 text-gray-600">This demo supports first-time post-completion OPT for UW F-1 students.</p>
    <Panel className="mt-7"><div className="space-y-6"><Field label="When do you plan to use OPT?"><select className={inputClass} value={intent} onChange={e=>setIntent(e.target.value)}><option value="AFTER_GRADUATION">After I graduate</option><option value="WHILE_STUDYING">While I'm still studying</option><option value="STEM_EXTENSION">I'm on OPT and want a STEM extension</option><option value="NOT_SURE">I'm not sure</option></select></Field>
      {intent!=="AFTER_GRADUATION" ? <div className="rounded-xl bg-amber-50 p-4 text-sm text-amber-950">{intent==="NOT_SURE"?"Post-completion OPT is typically used after finishing your program; pre-completion OPT is during study; STEM OPT is a possible extension. Confirm which applies with UW ISS.":"This pathway is coming soon in this MVP."} <a href="https://iss.washington.edu/f1-employment/" target="_blank" rel="noreferrer" className="font-bold underline">UW ISS guidance ↗</a></div> : <Field label="Is this your first post-completion OPT application at this degree level?"><select className={inputClass} value={first} onChange={e=>setFirst(e.target.value as "yes"|"no")}><option value="">Choose an answer</option><option value="yes">Yes</option><option value="no">No</option></select></Field>}
      {intent==="AFTER_GRADUATION" && first==="no" && <div className="rounded-xl bg-amber-50 p-4 text-sm">This situation is outside the demo's supported scope. Please check with <a className="underline" href="https://iss.washington.edu/" target="_blank" rel="noreferrer">UW ISS</a>.</div>}
      {isValid && <div className="rounded-xl bg-[#f1f5f0] p-4 text-sm"><strong>You're planning for Post-Completion OPT.</strong><p className="mt-1 text-gray-600">UW · {profile.degree} · {profile.programEndDate || "Program End Date not set"}</p></div>}
      {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}<button disabled={!isValid} onClick={async()=>{try{await actions.selectOpt("AFTER_GRADUATION",true);router.push("/opt/status");}catch(e){setError(e instanceof Error?e.message:String(e));}}} className="w-full rounded-xl bg-[#336a48] p-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Confirm & continue →</button>
    </div></Panel>
  </div></Shell>;
}
