"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Panel, Shell, inputClass } from "@/components/Shell";
import { formatDate, TASKS, taskState, useDemoProfile, type TaskStatus } from "@/lib/demo";
const TABS=["Steps","Documents","Official Sources","Timeline & Dependencies"] as const;
function TaskDetailsContent() {
  const params=useParams(); const id=String(params.id||"");const task=TASKS.find(t=>t.id===id);
  const {profile,save}=useDemoProfile(); const [tab,setTab]=useState<(typeof TABS)[number]>("Steps"); const [date,setDate]=useState("");
  if(!task)return <Shell><p>Task not found.</p><Link href="/checklist">Back to checklist</Link></Shell>;
  const state=taskState(profile,id);
  const needsDate=id==="T03"||id==="T05";
  const update=(status:TaskStatus)=>{
    if(state==="BLOCKED")return;
    if(status==="COMPLETED" && id==="T03"&&!date&&!profile.dsoRecDate){alert("Please enter the DSO recommendation date before completing this task.");return;}
    if(status==="COMPLETED" && id==="T05"&&!date&&!profile.uscisReceiptDate){alert("Please enter the USCIS receipt date before completing this task.");return;}
    const patch:Partial<typeof profile>={taskStatuses:{...profile.taskStatuses,[id]:status}};
    if(id==="T02"&&status==="WAITING_EXTERNAL"&&date)patch.i20RequestDate=date;
    if(id==="T03"&&date){patch.dsoRecDate=date; patch.stage="I20_RECEIVED";}
    if(id==="T05"&&date){patch.uscisReceiptDate=date;patch.stage="I765_FILED";}
    save(patch);
  };
  return <Shell><Link href="/checklist" className="text-sm text-[#336a48]">← Back to My Checklist</Link><div className="mt-7 flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-bold text-[#336a48]">{id} · OPT TASK</p><h1 className="mt-3 text-4xl font-bold">{task.title}</h1><p className="mt-3 max-w-3xl text-gray-600">{task.description}</p></div><span className="rounded-full bg-[#eef3e9] px-4 py-2 text-xs font-bold text-[#2f5145]">{state.replaceAll("_"," ")}</span></div>
    <Panel className="mt-7"><div className="flex flex-wrap gap-2 border-b border-[#e8ece5] pb-4" role="tablist" aria-label="Task details">{TABS.map(t=><button key={t} role="tab" aria-selected={tab===t} onClick={()=>setTab(t)} className={`rounded-lg px-4 py-2 text-sm ${tab===t?"bg-[#eaf3e8] font-semibold text-[#315b41]":"text-gray-600"}`}>{t}</button>)}</div>
      <div className="mt-6 min-h-40">{tab==="Steps"&&<ol className="list-decimal space-y-4 pl-5 text-sm leading-relaxed">{task.steps.map(s=><li key={s}>{s}</li>)}</ol>}{tab==="Documents"&&<ul className="list-disc space-y-3 pl-5 text-sm">{task.documents.map(x=><li key={x}>{x}</li>)}</ul>}{tab==="Official Sources"&&<ul className="space-y-4">{task.sources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noreferrer" className="font-semibold text-[#336a48] underline">{s.title} ↗</a><p className="mt-1 text-xs text-gray-500">External official resource · Review date not confirmed in demo</p></li>)}</ul>}{tab==="Timeline & Dependencies"&&<div className="space-y-3 text-sm"><p>Task status: <strong>{state.replaceAll("_"," ")}</strong></p><p>Program end: {formatDate(profile.programEndDate)}</p><p>DSO recommendation: {formatDate(profile.dsoRecDate)}</p><p>Task prerequisites are checked using the saved demo progress.</p><Link href="/opt/timeline" className="font-semibold text-[#336a48] underline">Open Timeline →</Link></div>}</div>
    </Panel>
    <Panel className="mt-5"><h2 className="text-lg font-bold">Update task status</h2>{state==="BLOCKED"?<p className="mt-2 text-sm text-amber-900">This task is blocked until its prerequisite has been completed. Return to your checklist.</p>:<>
      {((id==="T02")||needsDate)&&<label className="mt-4 block text-sm font-semibold">{id==="T02"?"School request submission date (when waiting)":id==="T03"?"DSO recommendation date (SEVIS)":"USCIS receipt date"}<input type="date" className={`${inputClass} mt-2 max-w-xs`} value={date} onChange={e=>setDate(e.target.value)}/></label>}
      <div className="mt-5 flex flex-wrap gap-3"><button onClick={()=>update("IN_PROGRESS")} className="rounded-xl border border-[#a6c2aa] px-4 py-2 text-sm font-semibold text-[#336a48]">Mark In Progress</button>{(id==="T02"||id==="T05")&&<button onClick={()=>update("WAITING_EXTERNAL")} className="rounded-xl border border-[#a6c2aa] px-4 py-2 text-sm font-semibold text-[#336a48]">I've submitted, waiting</button>}<button onClick={()=>update("COMPLETED")} className="rounded-xl bg-[#336a48] px-4 py-2 text-sm font-semibold text-white">Mark Complete</button></div>
    </>}
    </Panel><div className="mt-5 rounded-xl bg-[#f1f5f0] p-5 text-sm"><strong>Need help with this step?</strong><p className="mt-2 text-gray-600">Open the Ask AI preview, or contact UW ISS through its official website. This demo does not generate or send real emails.</p><a href="https://iss.washington.edu/" target="_blank" rel="noreferrer" className="mt-2 inline-block font-semibold text-[#336a48] underline">Contact My International Student Office ↗</a></div>
  </Shell>;
}


export default function TaskDetails() {
  return (
    <Suspense fallback={<div className="p-8">Loading task...</div>}>
      <TaskDetailsContent />
    </Suspense>
  );
}
