"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
import { actions, type Profile, type Stage, useDemoProfile } from "@/lib/demo";
export default function StatusPage() {
  const { profile, ready, error } = useDemoProfile();
  if (!ready || error) return <Shell><p role={error ? "alert" : "status"}>{error || "Loading your saved status…"}</p></Shell>;
  return <StatusForm profile={profile} />;
}

function StatusForm({ profile }: { profile: Profile }) {
  const router=useRouter();
  const [stage,setStage]=useState<Stage>(profile.stage); const [requestDate,setRequestDate]=useState(profile.i20RequestDate);
  const [recDate,setRecDate]=useState(profile.dsoRecDate); const [issueDate,setIssueDate]=useState(profile.i20IssueDate);
  const [receiptDate,setReceiptDate]=useState(profile.uscisReceiptDate); const [requestedStart,setRequestedStart]=useState(profile.requestedStartDate);
  const [error,setError]=useState("");
  async function submit(e:React.FormEvent) {e.preventDefault();if(stage==="I20_RECEIVED"&&!recDate){setError("Please enter the date your DSO recorded the recommendation in SEVIS.");return;} if(stage==="I765_FILED"&&(!receiptDate||!requestedStart)){setError("Receipt date and requested OPT start date are required for this stage.");return;}
    try{await actions.saveStatus(stage,{i20RequestDate:requestDate,dsoRecDate:recDate,i20IssueDate:issueDate,uscisReceiptDate:receiptDate,requestedStartDate:requestedStart});router.push("/opt/timeline");}
    catch(err){setError(err instanceof Error?err.message:String(err));}
  }
  return <Shell><Link href="/opt/select" className="text-sm text-[#336a48]">← Select OPT</Link><div className="mt-7 max-w-2xl"><p className="text-sm font-bold tracking-wider text-[#336a48]">CURRENT STATUS · STEP 2 OF 3</p><h1 className="mt-3 text-4xl font-bold">Where are you in the process?</h1><p className="mt-3 text-gray-600">We&apos;ll tailor the steps to your current application stage.</p><Panel className="mt-7"><form onSubmit={submit} className="space-y-6"><Field label="Your OPT stage"><select value={stage} onChange={e=>{setStage(e.target.value as Stage);setError("");}} className={inputClass}><option value="PLANNING">I haven&apos;t started</option><option value="I20_REQUESTED">I&apos;ve requested my OPT I-20</option><option value="I20_RECEIVED">I&apos;ve received my OPT I-20</option><option value="I765_FILED">I&apos;ve filed my I-765</option><option value="APPROVED">My OPT is approved</option></select></Field>
    {stage==="I20_REQUESTED"&&<Field label="Date you requested your OPT I-20 (optional)" hint="Find this in your school's submission record."><input type="date" className={inputClass} value={requestDate} onChange={e=>setRequestDate(e.target.value)}/></Field>}
    {stage==="I20_RECEIVED"&&<><Field label="DSO recommendation date in SEVIS (required)" hint="Confirm the actual SEVIS recommendation date with your DSO; it may differ from the I-20 issue date."><input type="date" required className={inputClass} value={recDate} onChange={e=>setRecDate(e.target.value)}/></Field></>}
    {(stage==="I20_REQUESTED" || stage==="I20_RECEIVED") && <Field label="OPT I-20 Date Issued (optional)" hint="Find the Date Issued next to the DSO signature on page 1 of your OPT I-20."><input type="date" className={inputClass} value={issueDate} onChange={e=>setIssueDate(e.target.value)}/></Field>}
    {stage==="I765_FILED"&&<><Field label="USCIS receipt date (required)" hint="Refer to your Form I-797C receipt notice."><input type="date" required className={inputClass} value={receiptDate} onChange={e=>setReceiptDate(e.target.value)}/></Field><Field label="Requested OPT start date (required)"><input type="date" required className={inputClass} value={requestedStart} onChange={e=>setRequestedStart(e.target.value)}/></Field></>}
    {stage==="APPROVED"&&<p className="rounded-xl bg-[#f1f5f0] p-4 text-sm">Post-approval obligations are planned for a future version. See <a href="https://iss.washington.edu/f1-employment/post-completion/" target="_blank" rel="noreferrer" className="font-semibold underline">UW ISS official guidance</a>.</p>}
    {error&&<p className="text-sm text-red-700" role="alert">{error}</p>}<button className="w-full rounded-xl bg-[#336a48] p-3 font-semibold text-white">Save & continue →</button></form></Panel></div></Shell>;
}
