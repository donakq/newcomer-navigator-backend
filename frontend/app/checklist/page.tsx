"use client";
import Link from "next/link";
import { Panel, PrimaryLink, Shell } from "@/components/Shell";
import { addDays, formatDate, taskState, TASKS, useDemoProfile } from "@/lib/demo";
import { useState } from "react";
export default function ChecklistPage() {
  const {profile,ready}=useDemoProfile(); const [filter,setFilter]=useState<"All"|"To do"|"Done">("All");
  const completed = TASKS.filter(t => profile.taskStatuses[t.id] === "COMPLETED").length;
  const progress = Math.round(completed/TASKS.length*100);
  const hasPlan = profile.optIntent === "AFTER_GRADUATION";
  const visibleTasks = TASKS.filter(t=>filter==="All"||(filter==="Done"?profile.taskStatuses[t.id]==="COMPLETED":profile.taskStatuses[t.id]!=="COMPLETED"));
  return <Shell><div><h1 className="text-4xl font-bold tracking-tight">Your journey, step by step.</h1><p className="mt-3 text-gray-600">Your UW OPT preparation hub. Start a plan, track actions, and review key dates.</p></div>
    <Panel className="mt-8"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-bold">Your Situation</h2><p className="mt-1 text-sm text-gray-600">UW · {profile.degree} · {profile.programEndDate ? `Program end ${formatDate(profile.programEndDate)}` : "Program End Date needed"}</p></div><Link href="/home" className="text-sm font-semibold text-[#336a48] underline">Edit →</Link></div></Panel>
    {profile.programEndDate && <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm text-blue-950">Indicative program-end filing window: {formatDate(addDays(profile.programEndDate,-90))} to {formatDate(addDays(profile.programEndDate,60))}. Actual filing requires DSO recommendation and official confirmation.</div>}
    <div className="mt-8"><h2 className="mb-4 text-xl font-bold">My Checklist</h2>
      <Panel className="border-[#c7dccb]"><div className="flex flex-wrap justify-between gap-4"><div><span className="text-xs font-bold uppercase tracking-wider text-[#37744d]">Work authorization</span><h3 className="mt-2 text-xl font-bold">Post-Completion OPT</h3><p className="mt-2 text-sm text-gray-600">Step-by-step tasks, timing, school guidance and official sources.</p></div>{hasPlan && <Link className="text-sm font-semibold text-[#336a48] underline" href="/opt/timeline">View Timeline →</Link>}</div>
        {!hasPlan ? <div className="mt-5"><PrimaryLink href="/opt/select">Start OPT plan →</PrimaryLink></div> : <>
          <div className="mt-6 flex justify-between gap-4 text-sm"><strong>OPT progress</strong><span>{completed} of {TASKS.length} done</span></div><div className="mt-3 h-3 overflow-hidden rounded-full bg-[#e9ece7]"><div className="h-full rounded-full bg-[#3d7953]" style={{width:`${progress}%`}}/></div>
          <div className="mt-5 flex flex-wrap gap-2">{(["All","To do","Done"] as const).map(f=><button key={f} onClick={()=>setFilter(f)} className={`rounded-full border px-4 py-2 text-xs ${filter===f?"border-[#336a48] bg-[#eef5ee] font-semibold":"border-gray-200"}`}>{f}</button>)}</div>
          <div className="mt-4 divide-y divide-gray-100">{visibleTasks.map(t=>{const state=taskState(profile,t.id);return <Link key={t.id} href={`/opt/tasks/${t.id}`} className="flex items-center gap-3 py-4 hover:bg-[#fafbf9]"><span aria-hidden className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-sm ${state==="COMPLETED"?"border-[#3b8253] bg-[#3b8253] text-white":"border-[#cfd9ce] text-gray-400"}`}>{state==="COMPLETED"?"✓":""}</span><span className="min-w-0 flex-1"><span className="block font-medium">{t.title}</span><span className="block text-xs text-gray-500">{t.id}</span></span><span className={`rounded-full px-3 py-1 text-[11px] font-semibold ${state==="BLOCKED"?"bg-gray-100 text-gray-600":state==="COMPLETED"?"bg-green-50 text-green-800":"bg-[#eef3e9] text-[#315b41]"}`}>{state.replaceAll("_"," ")}</span><span className="text-[#336a48]">›</span></Link>})}</div>
        </>}
      </Panel>
      <div className="mt-4 grid gap-3">{[{name:"Maintaining status",url:"https://iss.washington.edu/"},{name:"Health insurance",url:"https://iss.washington.edu/"},{name:"Travel",url:"https://iss.washington.edu/"},{name:"Taxes",url:"https://iss.washington.edu/"}].map(m=><div className="flex items-center justify-between gap-4 rounded-xl border border-[#e9e9e6] bg-[#f4f4f1] px-5 py-4" key={m.name}><div><strong>{m.name}</strong><p className="text-xs text-gray-500">Coming soon · Not available in OPT MVP</p></div><a className="shrink-0 text-xs text-[#336a48] underline" href={m.url} target="_blank" rel="noreferrer">UW ISS ↗</a></div>)}</div>
    </div>
    {!ready && <p className="mt-4 text-sm text-gray-500">Loading demo profile…</p>}
  </Shell>;
}
