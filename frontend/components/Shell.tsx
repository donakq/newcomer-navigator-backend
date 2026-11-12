"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode, useState } from "react";
import { useDemoProfile } from "@/lib/demo";

export function Shell({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const pathname = usePathname();
  return <main className="min-h-screen bg-[#faf9f6] px-4 py-6 text-[#252d29] sm:px-7 sm:py-9">
    <div className={`mx-auto ${wide ? "max-w-6xl" : "max-w-5xl"}`}>
      <header className="mb-9 flex flex-wrap items-center justify-between gap-3 border-b border-[#e5e9e2] pb-5">
        <Link href="/" className="text-lg font-bold tracking-tight text-[#315f42]">✦ Paperwork Navigator</Link>
        <nav className="flex flex-wrap items-center gap-4 text-sm text-[#48564d]" aria-label="Main navigation">
          <Link className={pathname === "/home" ? "font-bold text-[#315f42]" : "hover:text-[#315f42]"} href="/home">Home</Link>
          <Link className={pathname?.startsWith("/checklist") ? "font-bold text-[#315f42]" : "hover:text-[#315f42]"} href="/checklist">My Checklist</Link>
          <Link href="/opt/timeline" className={pathname?.startsWith("/opt/timeline") ? "font-bold text-[#315f42]" : "hover:text-[#315f42]"}>Timeline</Link>
          <a href="#ask-ai" className="hover:text-[#315f42]">Ask AI</a>
        </nav>
      </header>
      <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs leading-relaxed text-amber-950" role="note">
        DEMO MODE · Sample workflow and locally stored test data. Dates and school guidance have not been policy-reviewed. Do not use for real immigration filing decisions.
      </div>
      {children}
      <AssistantWidget />
    </div>
  </main>;
}
export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-[#e4e9e3] bg-white p-5 shadow-[0_4px_16px_rgba(46,76,54,.04)] sm:p-7 ${className}`}>{children}</section>;
}
export function PrimaryLink({ href, children }: { href: string; children: ReactNode }) {
  return <Link href={href} className="inline-flex items-center justify-center rounded-xl bg-[#336a48] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#28583b]">{children}</Link>;
}
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return <label className="block space-y-2"><span className="block text-sm font-semibold">{label}</span>{children}{hint && <span className="block text-xs leading-relaxed text-gray-500">{hint}</span>}</label>;
}
export const inputClass = "block w-full rounded-xl border border-[#d9e0d8] bg-white px-4 py-3 text-sm text-[#223329] outline-none focus:border-[#488362] focus:ring-2 focus:ring-[#dcece0]";
export function AssistantWidget() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [sent, setSent] = useState(false);
  const { profile } = useDemoProfile();
  const [contact, setContact] = useState(false);
  return <div id="ask-ai" className="fixed bottom-5 right-5 z-50">
    {open && <section role="dialog" aria-label="OPT assistant preview" className="mb-3 flex max-h-[76vh] w-[min(370px,calc(100vw-40px))] flex-col overflow-auto rounded-2xl border border-[#dbe4d9] bg-white shadow-2xl">
      <div className="flex items-center justify-between bg-[#eef4ed] px-5 py-4"><strong>OPT assistant · Demo preview</strong><button aria-label="Close assistant" onClick={() => setOpen(false)}>✕</button></div>
      <div className="space-y-3 p-5 text-sm">
        {contact ? <>
          <h3 className="font-semibold">Contact UW ISS</h3>
          <p>For a case-specific question, contact the university through its official channels.</p>
          <a className="font-semibold text-[#336a48] underline" target="_blank" rel="noreferrer" href="https://iss.washington.edu/">Visit UW International Student Services ↗</a>
          <p className="text-xs text-gray-500">We do not send email or collect student IDs in this prototype.</p>
          <button onClick={() => setContact(false)} className="text-[#336a48] underline">← Back to assistant</button>
        </> : <>
          <p className="rounded-lg bg-[#f3f6f1] p-3 text-gray-700">This is a UI preview. Live AI answers are not connected. For verified guidance, use UW ISS and USCIS sources.</p>
          <p className="text-xs text-gray-500">Your current stage: {profile.stage.replaceAll("_", " ")}</p>
          <div className="flex flex-wrap gap-2">{["What is OPT?", "What's my next step?", "Who do I contact at UW?"].map(q => <button key={q} onClick={() => { setQuestion(q); setSent(false); }} className="rounded-full border border-[#dce4da] px-3 py-2 text-xs hover:bg-[#f2f6f0]">{q}</button>)}</div>
          <label className="block text-xs font-semibold">Ask about OPT (preview only)<textarea rows={2} className={`${inputClass} mt-2`} value={question} onChange={e => { setQuestion(e.target.value); setSent(false); }} placeholder="Type your OPT question" /></label>
          <button disabled={!question.trim()} onClick={() => setSent(true)} className="rounded-xl bg-[#336a48] px-4 py-2 text-white disabled:opacity-50">Preview response</button>
          {sent && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3">AI service not connected yet. Please refer to the official UW ISS or USCIS links; this prototype cannot verify a case-specific answer.</p>}
          <button onClick={() => setContact(true)} className="w-full rounded-xl border border-[#336a48] p-3 font-semibold text-[#336a48]">Contact My International Student Office</button>
        </>}
      </div>
    </section>}
    <button onClick={() => setOpen(x => !x)} aria-expanded={open} aria-label="Open OPT assistant preview" className="ml-auto block rounded-full bg-[#336a48] px-5 py-3 text-sm font-semibold text-white shadow-xl">{open ? "Close" : "✦ Ask AI"}</button>
  </div>;
}
