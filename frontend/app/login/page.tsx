"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDemoProfile } from "@/lib/demo";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
export default function Login() {
  const {profile, save} = useDemoProfile(); const router = useRouter();
  return <Shell><div className="mx-auto mt-10 max-w-xl"><Panel><p className="text-xs font-bold uppercase tracking-widest text-[#346b48]">Step 1 · Prototype access</p><h1 className="mt-3 text-3xl font-bold">Welcome to Paperwork Navigator</h1><p className="mt-3 text-sm text-gray-600">The PRD calls for email verification. Authentication is not connected in this demo, so this step is for navigation testing only.</p><form className="mt-7 space-y-5" onSubmit={e => {e.preventDefault(); router.push(profile.programEndDate ? "/checklist" : "/onboarding");}}><Field label="Email (optional demo label)" hint="No verification email will be sent. Avoid entering personal details for testing."><input type="email" className={inputClass} value={profile.email} onChange={e=>save({email:e.target.value})} placeholder="demo@example.com"/></Field><button className="w-full rounded-xl bg-[#336a48] px-5 py-3 font-semibold text-white">Continue in Demo Mode →</button></form><Link href="/" className="mt-4 inline-block text-sm text-[#336a48]">← Back to landing page</Link></Panel></div></Shell>;
}
