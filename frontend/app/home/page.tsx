"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ApiHistoryEntry } from "@/lib/api";
import { actions, formatDate, useDemoProfile, type Profile } from "@/lib/demo";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
export default function ProfileHome() {
  const {profile,save,clear,ready}=useDemoProfile(); const router=useRouter();
  const [history,setHistory]=useState<ApiHistoryEntry[]|null>(null); const [restoring,setRestoring]=useState<string|null>(null); const [historyError,setHistoryError]=useState("");
  useEffect(()=>{ if(ready) actions.history().then(setHistory).catch(()=>setHistory([])); },[ready]);
  async function restore(entry:ApiHistoryEntry) {
    if(!window.confirm(`Restore the plan saved ${savedOn(entry)}? Your current plan will be saved to History, so you can switch back later.`)) return;
    setRestoring(entry.id); setHistoryError("");
    try {
      const step = await actions.restorePlan(entry.id);
      if (step !== "done") { router.push("/setup"); return; }  // an older plan may be missing answers
      setHistory(await actions.history());
    }
    catch(e) { setHistoryError(e instanceof Error ? e.message : String(e)); }
    finally { setRestoring(null); }
  }
  function updateP(value:string) { if(value!==profile.programEndDate && window.confirm("Changing your Program End Date will recalculate the preview timeline. Continue?")) save({programEndDate:value}); }
  function change<K extends keyof Profile>(key:K,value:Profile[K]) { save({[key]:value}); }
  return <Shell><h1 className="text-4xl font-bold">Your situation</h1><p className="mt-3 text-gray-600">Keep your information current. Your checklist and timeline are recalculated from it.</p>
    <div className="mt-8 grid gap-6 lg:grid-cols-2">
      <Panel><h2 className="mb-5 text-xl font-bold">School & program</h2><div className="space-y-5"><Field label="School"><input disabled className={inputClass} value="University of Washington" readOnly/></Field><Field label="Degree level"><select className={inputClass} value={profile.degree} onChange={e=>change("degree",e.target.value as Profile["degree"])}>{["Bachelor","Master","PhD"].map(v=><option key={v}>{v}</option>)}</select></Field><Field label="Program End Date"><input type="date" className={inputClass} value={profile.programEndDate} onChange={e=>updateP(e.target.value)} /></Field></div></Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">OPT progress</h2><p className="text-sm text-gray-600">Selection: {profile.optIntent ? "Post-Completion OPT" : "Not selected"}</p><p className="mt-3 text-sm text-gray-600">Current stage: {profile.stage.replaceAll("_"," ")}</p><div className="mt-6 flex flex-wrap gap-3"><Link className="rounded-lg border border-[#abc5af] px-4 py-2 text-sm font-medium text-[#336a48]" href="/opt/select">Change OPT selection</Link><Link className="rounded-lg border border-[#abc5af] px-4 py-2 text-sm font-medium text-[#336a48]" href="/opt/status">Update status</Link></div></Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">Offer & timeline</h2><p className="text-sm text-gray-600">Offer: {profile.hasOffer === null ? "Not provided" : profile.hasOffer ? "Yes" : "No"}</p><p className="mt-2 text-sm text-gray-600">Offer start date: {profile.offerStartDate||"Not provided"}</p><Link className="mt-5 inline-block font-semibold text-[#336a48] underline" href="/opt/timeline">Edit timeline inputs →</Link></Panel>
      <Panel><h2 className="mb-2 text-xl font-bold">History</h2><p className="text-sm text-gray-600">Plans you saved by starting over. Restore one to make it your current plan again; your current plan is kept here.</p>
        {history===null?<p className="mt-4 text-sm text-gray-500">Loading…</p>:history.length===0?<p className="mt-4 text-sm text-gray-500">No past plans yet. Use Start over on My Checklist to begin a new plan.</p>:<ul className="mt-3 divide-y divide-[#eef1ec] text-sm">{history.map(h=>{const done=Object.values(h.task_statuses).filter(s=>s==="COMPLETED").length; return <li key={h.id} className="flex items-center justify-between gap-3 py-3"><div><p className="font-medium">Saved {savedOn(h)}</p><p className="text-gray-600">Program end {formatDate(h.profile.program_end_date)} · {h.profile.stage?h.profile.stage.replaceAll("_"," ").toLowerCase():"no stage"} · {done} task{done===1?"":"s"} done</p></div><button type="button" disabled={restoring!==null} onClick={()=>restore(h)} className="shrink-0 rounded-lg border border-[#abc5af] px-3 py-1.5 text-sm font-medium text-[#336a48] disabled:opacity-50">{restoring===h.id?"Restoring…":"Restore"}</button></li>;})}</ul>}
        {historyError&&<p role="alert" className="mt-3 text-sm text-red-700">{historyError}</p>}
      </Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">Privacy & account</h2><p className="text-sm text-gray-600">Signed in as {profile.email}.</p><button disabled={!ready} className="mt-5 rounded-lg border border-red-200 px-4 py-2 text-sm text-red-700" onClick={()=>{if(window.confirm("Delete your account and all your data? This cannot be undone.")){clear();router.push("/");}}}>Delete account and data</button></Panel>
    </div>
  </Shell>;
}

function savedOn(entry: ApiHistoryEntry): string {
  return new Date(entry.archived_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
