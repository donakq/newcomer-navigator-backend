"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { actions } from "@/lib/demo";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";

type Mode = "signin" | "signup";

const COPY: Record<Mode, { step: string; title: string; intro: string; cta: string }> = {
  signin: {
    step: "Step 1 · Sign in",
    title: "Welcome back",
    intro: "Sign in with your email. We'll send you a 6-digit code.",
    cta: "Continue with Email →",
  },
  signup: {
    step: "Step 1 · Create account",
    title: "Create your account",
    intro: "No password needed. Enter your email and we'll send you a 6-digit code.",
    cta: "Create Account →",
  },
};

export default function Login() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState(""); const [code, setCode] = useState(""); const [sent, setSent] = useState(false);
  const [tos, setTos] = useState(false);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);

  // Landing page "Get Started" links to /login?mode=signup. Read it after mount so the page stays static.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("mode") === "signup") setMode("signup");
  }, []);

  function switchMode(next: Mode) { setMode(next); setSent(false); setCode(""); setError(""); }
  async function run(fn: () => Promise<void>) { setBusy(true); setError(""); try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); } }

  const copy = COPY[mode];
  const tab = (m: Mode, label: string) => <button type="button" role="tab" aria-selected={mode === m} onClick={() => switchMode(m)}
    className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition ${mode === m ? "bg-white text-[#315f42] shadow-sm" : "text-[#5d6a62] hover:text-[#315f42]"}`}>{label}</button>;

  return <Shell showNav={false}><div className="mx-auto mt-10 max-w-xl"><Panel>
    <div role="tablist" aria-label="Sign in or create account" className="mb-7 flex gap-1 rounded-xl bg-[#f0f3ee] p-1">
      {tab("signin", "Sign in")}{tab("signup", "Create account")}
    </div>
    <p className="text-xs font-bold uppercase tracking-widest text-[#346b48]">{copy.step}</p><h1 className="mt-3 text-3xl font-bold">{copy.title}</h1><p className="mt-3 text-sm text-gray-600">{copy.intro}</p>
    {!sent ? <form className="mt-7 space-y-5" onSubmit={e => { e.preventDefault(); run(async () => { await actions.startLogin(email); setSent(true); }); }}>
      <Field label="Email"><input type="email" required className={inputClass} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@uw.edu" /></Field>
      {mode === "signup" && <label className="flex items-start gap-3 text-sm text-gray-600">
        <input type="checkbox" required checked={tos} onChange={e => setTos(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[#336a48]" />
        <span>I agree to the Terms of Use and Privacy Policy. I understand this tool gives general guidance, not legal advice.</span>
      </label>}
      <button disabled={busy} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">{copy.cta}</button>
    </form> : <form className="mt-7 space-y-5" onSubmit={e => { e.preventDefault(); run(async () => { const step = await actions.verify(email, code, mode === "signin" || tos); router.push(step === "done" ? "/checklist" : "/setup"); }); }}>
      <Field label={`Code sent to ${email}`} hint="Mock backend: no email is sent. The code is always 000000."><input inputMode="numeric" pattern="\d{6}" required className={inputClass} value={code} onChange={e => setCode(e.target.value)} placeholder="000000" /></Field>
      <button disabled={busy} className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white disabled:opacity-50">Verify →</button>
      <button type="button" className="text-sm text-[#336a48]" onClick={() => { setSent(false); setCode(""); }}>Use a different email</button>
    </form>}
    {error && <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>}
    <p className="mt-6 text-sm text-gray-600">{mode === "signin"
      ? <>New here? <button type="button" className="font-semibold text-[#336a48]" onClick={() => switchMode("signup")}>Create an account</button></>
      : <>Already have an account? <button type="button" className="font-semibold text-[#336a48]" onClick={() => switchMode("signin")}>Sign in</button></>}</p>
    <Link href="/" className="mt-3 inline-block text-sm text-[#336a48]">← Back to landing page</Link></Panel></div></Shell>;
}
