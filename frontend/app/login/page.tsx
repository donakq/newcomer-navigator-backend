"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { actions } from "@/lib/demo";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
export default function Login() {
  const router = useRouter();
  const [email, setEmail] = useState(""); const [code, setCode] = useState(""); const [sent, setSent] = useState(false);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<void>) { setBusy(true); setError(""); try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); } }
  return <Shell><div className="mx-auto mt-10 max-w-xl"><Panel><p className="text-xs font-bold uppercase tracking-widest text-[#346b48]">Step 1 · Sign in</p><h1 className="mt-3 text-3xl font-bold">Welcome to Paperwork Navigator</h1><p className="mt-3 text-sm text-gray-600">Sign in with your email. We'll send you a 6-digit code.</p>
    {!sent ? <form className="mt-7 space-y-5" onSubmit={e => { e.preventDefault(); run(async () => { await actions.startLogin(email); setSent(true); }); }}>
      <Field label="Email"><input type="email" required className={inputClass} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@uw.edu" /></Field>
      <button disabled={busy} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">Continue with Email →</button>
    </form> : <form className="mt-7 space-y-5" onSubmit={e => { e.preventDefault(); run(async () => { const onboarded = await actions.verify(email, code); router.push(onboarded ? "/checklist" : "/onboarding"); }); }}>
      <Field label={`Code sent to ${email}`} hint="Mock backend: no email is sent. The code is always 000000."><input inputMode="numeric" pattern="\d{6}" required className={inputClass} value={code} onChange={e => setCode(e.target.value)} placeholder="000000" /></Field>
      <button disabled={busy} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">Verify →</button>
      <button type="button" className="text-sm text-[#336a48]" onClick={() => { setSent(false); setCode(""); }}>Use a different email</button>
    </form>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    <Link href="/" className="mt-4 inline-block text-sm text-[#336a48]">← Back to landing page</Link></Panel></div></Shell>;
}
