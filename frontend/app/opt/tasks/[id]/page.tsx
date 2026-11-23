"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Panel, Shell, inputClass } from "@/components/Shell";
import { api, ApiError, type ApiTaskDetail } from "@/lib/api";
import { actions, formatDate, taskState, useDemoProfile, type TaskStatus } from "@/lib/demo";
const TABS=["Steps","Documents","Official Sources","Timeline & Dependencies"] as const;
// Which date each task records when its status changes (task templates: waiting_records / complete_requires).
const DATE_FIELD: Record<string,{field:string;label:string}> = {
  T02:{field:"i20_request_date",label:"School request submission date (when waiting)"},
  T03:{field:"dso_rec_date",label:"DSO recommendation date (SEVIS)"},
  T05:{field:"uscis_receipt_date",label:"USCIS receipt date"},
};
function TaskDetailsContent() {
  const params=useParams(); const id=String(params.id||"");
  const {profile,plan}=useDemoProfile(); const [tab,setTab]=useState<(typeof TABS)[number]>("Steps"); const [date,setDate]=useState<string>(); const [issueDate,setIssueDate]=useState<string>();
  const [detail,setDetail]=useState<ApiTaskDetail|null>(null); const [notFound,setNotFound]=useState(false); const [message,setMessage]=useState("");
  useEffect(()=>{ api<ApiTaskDetail>("GET",`/api/me/tasks/${id}`).then(setDetail).catch(e=>{ if(e instanceof ApiError&&e.status===404) setNotFound(true); else setMessage(e.message); }); },[id, plan?.version]);
  if(notFound)return <Shell><p>Task not found.</p><Link href="/checklist">Back to checklist</Link></Shell>;
  if(!detail)return <Shell><p className="text-sm text-gray-500">{message||"Loading task…"}</p></Shell>;
  const task=detail.task; const state=taskState(profile,id)||task.status; const dateField=DATE_FIELD[id];
  const deadlineNode = plan?.nodes.find(node => task.node_ids.includes(node.id)
    && node.date === task.deadline_at && (node.due_type === "FEDERAL" || node.due_type === "SCHOOL"));
  const deadlineLabel = deadlineNode?.due_type === "SCHOOL" ? "School deadline"
    : deadlineNode?.due_type === "FEDERAL" ? "Federal deadline" : "Deadline";
  const savedDate = dateField?.field === "i20_request_date" ? profile.i20RequestDate
    : dateField?.field === "dso_rec_date" ? profile.dsoRecDate : profile.uscisReceiptDate;
  const update=async(status:TaskStatus)=>{
    setMessage("");
    try { await actions.updateTask(id, status, {
      ...(dateField && date ? { [dateField.field]: date } : {}),
      ...(id === "T03" && issueDate ? { i20_issue_date: issueDate } : {}),
    }); setDate(undefined); setIssueDate(undefined); setMessage(`Saved: ${status.replaceAll("_"," ").toLowerCase()}.`); }
    catch(e){ setMessage(e instanceof Error?e.message:String(e)); }
  };
  return <Shell><Link href="/checklist" className="text-sm text-[#336a48]">← Back to My Checklist</Link><div className="mt-7 flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-bold text-[#336a48]">{id} · OPT TASK</p><h1 className="mt-3 text-4xl font-bold">{task.title}</h1>{(task.due_at || task.deadline_at) && <p className="mt-3 max-w-3xl text-gray-600">
      {task.due_at && task.due_at !== task.deadline_at && <>Target: {formatDate(task.due_at)}</>}
      {task.deadline_at && <>{task.due_at && task.due_at !== task.deadline_at && " · "}{deadlineLabel}: {formatDate(task.deadline_at)}</>}
    </p>}</div><span className="rounded-full bg-[#eef3e9] px-4 py-2 text-xs font-bold text-[#2f5145]">{state.replaceAll("_"," ")}</span></div>
    <Panel className="mt-7"><div className="flex flex-wrap gap-2 border-b border-[#e8ece5] pb-4" role="tablist" aria-label="Task details">{TABS.map(t=><button key={t} role="tab" aria-selected={tab===t} onClick={()=>setTab(t)} className={`rounded-lg px-4 py-2 text-sm ${tab===t?"bg-[#eaf3e8] font-semibold text-[#315b41]":"text-gray-600"}`}>{t}</button>)}</div>
      <div className="mt-6 min-h-40">{tab==="Steps"&&<ol className="list-decimal space-y-4 pl-5 text-sm leading-relaxed">{detail.template_content.steps.map(s=><li key={s}>{s}</li>)}</ol>}{tab==="Documents"&&<ul className="list-disc space-y-3 pl-5 text-sm">{detail.template_content.documents.map(x=><li key={x.name}>{x.name}{x.where_to_get&&<span className="text-gray-500"> · {x.where_to_get}</span>}</li>)}</ul>}{tab==="Official Sources"&&<ul className="space-y-4">{detail.sources.map(s=><li key={s.id}>{s.url?<a href={s.url} target="_blank" rel="noreferrer" className="font-semibold text-[#336a48] underline">{s.title} ↗</a>:<span className="font-semibold">{s.title}</span>}<p className="mt-1 text-xs text-gray-500">{s.url?"":"Link pending policy review · "}{s.last_reviewed?`Last reviewed ${formatDate(s.last_reviewed)}`:"Not yet reviewed"}</p></li>)}</ul>}{tab==="Timeline & Dependencies"&&<div className="space-y-3 text-sm"><p>Task status: <strong>{state.replaceAll("_"," ")}</strong></p>{task.blocked_by.length>0&&<p>Waiting on: {task.blocked_by.join(", ")}</p>}<p>Program end: {formatDate(profile.programEndDate)}</p><p>DSO recommendation: {formatDate(profile.dsoRecDate)}</p><Link href="/opt/timeline" className="font-semibold text-[#336a48] underline">Open Timeline →</Link></div>}</div>
    </Panel>
    <Panel className="mt-5"><h2 className="text-lg font-bold">Update task status</h2>{state==="BLOCKED"?<p className="mt-2 text-sm text-amber-900">This task is blocked until {task.blocked_by.join(", ")} is done. Return to your checklist.</p>:<>
      {dateField&&<label className="mt-4 block text-sm font-semibold">{dateField.label}<input type="date" className={`${inputClass} mt-2 max-w-xs`} value={date ?? savedDate} onChange={e=>setDate(e.target.value)}/>{detail.field_hints[dateField.field]&&<span className="mt-1 block text-xs font-normal text-gray-500">{detail.field_hints[dateField.field]}</span>}</label>}
      {id === "T03" && <label className="mt-4 block text-sm font-semibold">OPT I-20 Date Issued
        <input type="date" className={`${inputClass} mt-2 max-w-xs`} value={issueDate ?? profile.i20IssueDate} onChange={e => setIssueDate(e.target.value)} />
        <span className="mt-1 block text-xs font-normal text-gray-500">{detail.field_hints.i20_issue_date}</span>
      </label>}
      <div className="mt-5 flex flex-wrap gap-3"><button onClick={()=>update("IN_PROGRESS")} className="rounded-xl border border-[#a6c2aa] px-4 py-2 text-sm font-semibold text-[#336a48]">Mark In Progress</button>{(id==="T02"||id==="T05")&&<button onClick={()=>update("WAITING_EXTERNAL")} className="rounded-xl border border-[#a6c2aa] px-4 py-2 text-sm font-semibold text-[#336a48]">I&apos;ve submitted, waiting</button>}<button onClick={()=>update("COMPLETED")} className="rounded-xl bg-[#336a48] px-4 py-2 text-sm font-semibold text-white">Mark Complete</button></div>
    </>}
    {message&&<p role="status" className="mt-3 text-sm text-gray-700">{message}</p>}
    </Panel><div className="mt-5 rounded-xl bg-[#f1f5f0] p-5 text-sm"><strong>Need help with this step?</strong><p className="mt-2 text-gray-600">Ask AI about this step, or use Contact My International Student Office in the assistant to draft an email.</p><a href="https://iss.washington.edu/" target="_blank" rel="noreferrer" className="mt-2 inline-block font-semibold text-[#336a48] underline">UW ISS website ↗</a></div>
  </Shell>;
}


export default function TaskDetails() {
  return (
    <Suspense fallback={<div className="p-8">Loading task...</div>}>
      <TaskDetailsContent />
    </Suspense>
  );
}
