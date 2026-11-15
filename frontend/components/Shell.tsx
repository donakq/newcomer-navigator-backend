"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import OptAssistantWidget from "./OptAssistantWidget";

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
          <button type="button" onClick={() => document.getElementById("opt-assistant-toggle")?.click()} className="hover:text-[#315f42]">Ask AI</button>
        </nav>
      </header>
      <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-xs leading-relaxed text-amber-950" role="note">
        DEMO MODE · Mock backend: data resets when the server restarts. Dates and school guidance have not been policy-reviewed. Do not use for real immigration filing decisions.
      </div>
      {children}
      <OptAssistantWidget />
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
