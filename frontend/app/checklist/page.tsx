"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Panel, PrimaryLink, Shell } from "@/components/Shell";
import { api, type ApiChecklist } from "@/lib/api";
import { actions, formatDate, taskState, useDemoProfile } from "@/lib/demo";
import { useEffect, useState } from "react";
export default function ChecklistPage() {
  const {profile,ready,tasks:TASKS}=useDemoProfile(); const [filter,setFilter]=useState<"All"|"To do"|"Done">("All");
  const [overview, setOverview] = useState<ApiChecklist | null>(null);
  const [overviewError, setOverviewError] = useState("");
  const router = useRouter(); const [resetting, setResetting] = useState(false); const [resetError, setResetError] = useState("");
  async function startOver() {
    if (!window.confirm("Start over? Your current plan and progress will be saved to History on your Home page, and you'll enter your program details again.")) return;
    setResetting(true); setResetError("");
    try { await actions.startOver(); router.push("/setup"); }
    catch (e) { setResetError(e instanceof Error ? e.message : String(e)); }
    finally { setResetting(false); }  // the page stays mounted while hidden, so don't leave the button stuck
  }
  useEffect(() => {
    if (!profile.programEndDate) return;
    let active = true;
    api<ApiChecklist>("GET", "/api/me/checklist").then(data => {
      if (active) { setOverview(data); setOverviewError(""); }
    }).catch(() => {
      if (active) setOverviewError("Checklist links and filing window could not be loaded.");
    });
    return () => { active = false; };
  }, [profile.programEndDate]);
  const completed = TASKS.filter(t => profile.taskStatuses[t.id] === "COMPLETED").length;
  const progress = TASKS.length ? Math.round(completed/TASKS.length*100) : 0;
  const hasPlan = profile.optIntent === "AFTER_GRADUATION";
  const visibleTasks = TASKS.filter(t=>filter==="All"||(filter==="Done"?profile.taskStatuses[t.id]==="COMPLETED":profile.taskStatuses[t.id]!=="COMPLETED"));
  return <Shell><div><h1 className="text-4xl font-bold tracking-tight">Your journey, step by step.</h1><p className="mt-3 text-gray-600">Your UW OPT preparation hub. Start a plan, track actions, and review key dates.</p></div>
    <Panel className="mt-8"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-bold">Your Situation</h2><p className="mt-1 text-sm text-gray-600">UW · {profile.degree} · {profile.programEndDate ? `Program end ${formatDate(profile.programEndDate)}` : "Program End Date needed"}</p></div><div className="flex items-center gap-4"><button type="button" disabled={!ready || resetting} onClick={startOver} className="rounded-lg border border-[#abc5af] px-3 py-1.5 text-sm font-medium text-[#336a48] disabled:opacity-50">{resetting ? "Starting over…" : "Start over"}</button><Link href="/home" className="text-sm font-semibold text-[#336a48] underline">Edit →</Link></div></div>{resetError && <p role="alert" className="mt-3 text-sm text-red-700">{resetError}</p>}</Panel>
    {overviewError && <p role="alert" className="mt-4 text-sm text-red-700">{overviewError}</p>}
    {overview && <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 px-5 py-4 text-sm text-blue-950">Indicative program-end filing window: {formatDate(overview.graduation_banner.window_opens_on)} to {formatDate(overview.graduation_banner.window_closes_on)}. Actual filing requires DSO recommendation and official confirmation.</div>}
    <div className="mt-8"><h2 className="mb-4 text-xl font-bold">My Checklist</h2>
      <Panel className="border-[#c7dccb]"><div className="flex flex-wrap justify-between gap-4"><div><span className="text-xs font-bold uppercase tracking-wider text-[#37744d]">Work authorization</span><h3 className="mt-2 text-xl font-bold">Post-Completion OPT</h3><p className="mt-2 text-sm text-gray-600">Step-by-step tasks, timing, school guidance and official sources.</p></div>{hasPlan && <Link className="text-sm font-semibold text-[#336a48] underline" href="/opt/timeline">View Timeline →</Link>}</div>
        {!hasPlan ? <div className="mt-5"><PrimaryLink href="/opt/select">Start OPT plan →</PrimaryLink></div> : <>
          <div className="mt-6 flex justify-between gap-4 text-sm"><strong>OPT progress</strong><span>{completed} of {TASKS.length} done</span></div><div className="mt-3 h-3 overflow-hidden rounded-full bg-[#e9ece7]"><div className="h-full rounded-full bg-[#3d7953]" style={{width:`${progress}%`}}/></div>
          <div className="mt-5 flex flex-wrap gap-2">{(["All","To do","Done"] as const).map(f=><button key={f} onClick={()=>setFilter(f)} className={`rounded-full border px-4 py-2 text-xs ${filter===f?"border-[#336a48] bg-[#eef5ee] font-semibold":"border-gray-200"}`}>{f}</button>)}</div>
          <div className="mt-4 divide-y divide-gray-100">{visibleTasks.map(t=>{const state=taskState(profile,t.id);return <Link key={t.id} href={`/opt/tasks/${t.id}`} className="flex items-center gap-3 py-4 hover:bg-[#fafbf9]"><span aria-hidden className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md border text-sm ${state==="COMPLETED"?"border-[#3b8253] bg-[#3b8253] text-white":"border-[#cfd9ce] text-gray-400"}`}>{state==="COMPLETED"?"✓":""}</span><span className="min-w-0 flex-1"><span className="block font-medium">{t.title}</span></span><span className={`rounded-full px-3 py-1 text-[11px] font-semibold ${state==="BLOCKED"?"bg-gray-100 text-gray-600":state==="COMPLETED"?"bg-green-50 text-green-800":"bg-[#eef3e9] text-[#315b41]"}`}>{state.replaceAll("_"," ")}</span><span className="text-[#336a48]">›</span></Link>})}</div>
        </>}
      </Panel>
      <div className="mt-4 grid gap-3">{overview?.modules.filter(m => m.status === "COMING_SOON").map(m=><div className="flex items-center justify-between gap-4 rounded-xl border border-[#e9e9e6] bg-[#f4f4f1] px-5 py-4" key={m.id}><div><strong>{m.title}</strong><p className="text-xs text-gray-500">Coming soon · Not available in OPT MVP</p></div>{m.link && <a className="shrink-0 text-xs text-[#336a48] underline" href={m.link} target="_blank" rel="noreferrer">UW ISS ↗</a>}</div>)}</div>
    </div>
    {!ready && <p className="mt-4 text-sm text-gray-500">Loading your plan…</p>}
  </Shell>;
}
