"use client";
import Link from "next/link";
import { useLayoutEffect, useState } from "react";
import type { ApiPlan, ApiRange, ApiTask } from "@/lib/api";
import { actions, formatDate } from "@/lib/demo";
import ProcessingTimesForm from "@/components/ProcessingTimesForm";

const RANGE_STYLE: Record<ApiRange["kind"], string> = {
  LEGAL_WINDOW: "bg-[#e7f3ea] border-l-4 border-[#4f8f63]",
  ESTIMATE: "bg-[#fdf3de] border-l-4 border-[#e0a845]",
  NEEDS_DATE: "border border-dashed border-[#9a9a9a] bg-[repeating-linear-gradient(45deg,#f3f3f3,#f3f3f3_6px,#fff_6px,#fff_12px)]",
};
const LEGEND: { kind: ApiRange["kind"]; text: string; swatch: string }[] = [
  { kind: "LEGAL_WINDOW", text: "Legal window · confirm with UW ISS", swatch: "bg-[#e7f3ea] border border-[#4f8f63]" },
  { kind: "ESTIMATE", text: "Estimate · you can adjust", swatch: "bg-[#fdf3de] border border-[#e0a845]" },
  { kind: "NEEDS_DATE", text: "Waiting for your real date", swatch: RANGE_STYLE.NEEDS_DATE },
];
const DUE_CHIP: Record<ApiTask["due_type"], string> = {
  FEDERAL: "Federal deadline", SCHOOL: "School deadline", RECOMMENDED: "Recommended date", EVENT_BASED: "When it happens",
  ESTIMATE: "Estimate", USER_DECISION: "Your date", UNKNOWN: "Date not set",
};
const BLOCKING_RISKS: Record<string, string> = {
  WINDOW_CLOSED: "The filing window has closed. Contact UW ISS before taking any step.",
  CONFLICT: "Your dates conflict with the filing rules. Check your DSO recommendation date with UW ISS.",
  OUT_OF_SCOPE: "Your start date is on or before your program end date, which is outside post-completion OPT. Check with UW ISS.",
};
const ISS_URL = "https://iss.washington.edu/";

type Item =
  | { type: "task"; date: string | null; task: ApiTask }
  | { type: "range"; date: string; range: ApiRange }
  | { type: "milestone"; date: string; label: string; chip: string }
  | { type: "today"; date: string };

function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** The student's plan as one dated column: task cards, colored ranges and a Today line (design 2026-11-27). */
export default function VerticalTimeline({ plan, linkTasks = false }: { plan: ApiPlan; linkTasks?: boolean }) {
  const [open, setOpen] = useState<ApiRange["id"] | null>(null);
  useLayoutEffect(() => () => setOpen(null), []);  // pages stay mounted while hidden (cacheComponents)

  const start = plan.nodes.find(n => n.id === "N5");
  const items: Item[] = [
    ...plan.tasks.map(t => ({ type: "task" as const, date: t.due_at ?? t.deadline_at, task: t })),
    ...plan.ranges.map(r => ({ type: "range" as const, date: r.start, range: r })),
    ...(start?.date ? [{ type: "milestone" as const, date: start.date, label: "OPT start date", chip: start.date_state === "USER_CONFIRMED" ? "Your date" : "Planned" }] : []),
    { type: "today", date: todayIso() },
  ];
  // Dated items in date order (ranges before tasks on the same day); undated tasks last.
  const order = { today: 0, range: 1, milestone: 2, task: 3 };
  items.sort((a, b) => (a.date === null ? 1 : 0) - (b.date === null ? 1 : 0)
    || (a.date ?? "").localeCompare(b.date ?? "") || order[a.type] - order[b.type]);
  const blocking = plan.risk_labels.filter(r => r in BLOCKING_RISKS);

  return <div>
    {blocking.map(r => <div key={r} role="alert" className="mb-4 rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-950"><strong className="block text-xs tracking-wide">{r.replaceAll("_", " ")}</strong>{BLOCKING_RISKS[r]} <a href={ISS_URL} target="_blank" rel="noreferrer" className="font-semibold underline">UW ISS ↗</a></div>)}
    <div className="mb-5 flex flex-wrap gap-4 text-xs text-gray-600">{LEGEND.map(l => <span key={l.kind} className="flex items-center gap-2"><span className={`inline-block h-3 w-6 rounded ${l.swatch}`} />{l.text}</span>)}</div>
    <ol className="relative space-y-3 border-l-2 border-[#cfd8cf] pl-6 sm:ml-28">
      {items.map((item, i) => {
        const when = item.date ? formatDate(item.date) : "No date yet";
        const dateLabel = <span className="mb-1 block text-xs text-gray-500 sm:absolute sm:-left-32 sm:top-2 sm:mb-0 sm:w-24 sm:text-right">{item.type === "range" ? `from ${when}` : when}</span>;
        if (item.type === "today") return <li key="today" className="relative py-1">{dateLabel}<span className="absolute -left-[31px] top-2 h-3 w-3 rounded-full bg-[#c0392b]" /><span className="text-xs font-bold uppercase tracking-wider text-[#c0392b]">Today</span></li>;
        if (item.type === "milestone") return <li key={`m-${i}`} className="relative">{dateLabel}<span className="absolute -left-[31px] top-3 h-3 w-3 rounded-full border-2 border-white bg-[#336a48] ring-1 ring-[#336a48]" /><div className="rounded-xl border border-[#e3e8e2] bg-white px-4 py-3"><strong className="block">{item.label}</strong><span className="text-xs text-gray-600">{item.chip}</span></div></li>;
        if (item.type === "task") {
          const t = item.task, done = t.status === "COMPLETED";
          const card = <div className={`rounded-xl border bg-white px-4 py-3 ${t.label === "OVERDUE" ? "border-red-300" : "border-[#e3e8e2]"}`}>
            <strong className="block">{t.id} · {t.title}</strong>
            <span className="text-xs text-gray-600">{done ? "Done ✓" : DUE_CHIP[t.due_type]}{t.label && !done ? ` · ${t.label}` : ""}</span>
          </div>;
          return <li key={t.id} className="relative">{dateLabel}<span className={`absolute -left-[31px] top-3 h-3 w-3 rounded-full border-2 border-white ring-1 ${done ? "bg-[#3b8253] ring-[#3b8253]" : "bg-white ring-[#336a48]"}`} />{linkTasks ? <Link href={`/opt/tasks/${t.id}`} className="block hover:opacity-80">{card}</Link> : card}</li>;
        }
        const r = item.range;
        return <li key={r.id} className="relative">{dateLabel}<div className={`rounded-lg px-4 py-3 text-sm text-[#252d29] ${RANGE_STYLE[r.kind]}`}>
          <strong className="block">{r.label}: {formatDate(r.start)} – {formatDate(r.end)}</strong>
          <p className="mt-1 text-gray-700">{r.note}</p>
          <RangeAction range={r} plan={plan} open={open === r.id} onToggle={() => setOpen(open === r.id ? null : r.id)} onDone={() => setOpen(null)} />
        </div></li>;
      })}
    </ol>
  </div>;
}

function RangeAction({ range, plan, open, onToggle, onDone }: { range: ApiRange; plan: ApiPlan; open: boolean; onToggle: () => void; onDone: () => void }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const link = "mt-2 inline-block text-xs font-semibold text-[#2f6b45] underline";

  if (range.action === "CONFIRM_WITH_SCHOOL") return <a href={ISS_URL} target="_blank" rel="noreferrer" className={link}>Confirm with UW ISS ↗</a>;
  const label = range.action === "ADJUST_PROCESSING" ? "Adjust processing time" : range.action === "ENTER_DSO_REC_DATE" ? "Enter date when you get it" : "Pick a start date";

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      if (range.action === "ENTER_DSO_REC_DATE") await actions.enterDsoRecDate(value);
      else await actions.pickStartDate(value);
      setValue(""); onDone();
    } catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setBusy(false); }
  }

  return <div>
    <button type="button" onClick={onToggle} aria-expanded={open} className={link}>{open ? "Close" : label}</button>
    {open && <div className="mt-3 rounded-lg border border-[#e3e8e2] bg-white p-3">
      {range.action === "ADJUST_PROCESSING"
        ? <ProcessingTimesForm items={plan.processing} onSaved={onDone} />
        : <form onSubmit={save} className="flex flex-wrap items-end gap-3">
          <label className="text-xs font-semibold text-gray-700">{range.action === "ENTER_DSO_REC_DATE" ? "DSO recommendation date (from your OPT I-20)" : "Your OPT start date"}
            <input type="date" required value={value} onChange={e => setValue(e.target.value)}
              min={range.action === "PICK_START_DATE" ? range.start : undefined} max={range.action === "PICK_START_DATE" ? range.end : undefined}
              className="mt-1 block rounded-lg border border-[#d9e0d8] px-3 py-2 text-sm font-normal" />
          </label>
          <button disabled={busy || !value} className="rounded-lg bg-[#336a48] px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">{busy ? "Saving…" : "Save"}</button>
        </form>}
      {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
    </div>}
  </div>;
}
