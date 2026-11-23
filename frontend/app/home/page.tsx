"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDemoProfile, type Profile } from "@/lib/demo";
import { Field, inputClass, Panel, Shell } from "@/components/Shell";
export default function ProfileHome() {
  const {profile,save,clear,ready}=useDemoProfile(); const router=useRouter();
  function updateP(value:string) { if(value!==profile.programEndDate && window.confirm("Changing your Program End Date will recalculate the preview timeline. Continue?")) save({programEndDate:value}); }
  function change<K extends keyof Profile>(key:K,value:Profile[K]) { save({[key]:value}); }
  return <Shell><h1 className="text-4xl font-bold">Your situation</h1><p className="mt-3 text-gray-600">Keep your information current. Your checklist and timeline are recalculated from it.</p>
    <div className="mt-8 grid gap-6 lg:grid-cols-2">
      <Panel><h2 className="mb-5 text-xl font-bold">School & program</h2><div className="space-y-5"><Field label="School"><input disabled className={inputClass} value="University of Washington" readOnly/></Field><Field label="Degree level"><select className={inputClass} value={profile.degree} onChange={e=>change("degree",e.target.value as Profile["degree"])}>{["Bachelor","Master","PhD"].map(v=><option key={v}>{v}</option>)}</select></Field><Field label="Program End Date"><input type="date" className={inputClass} value={profile.programEndDate} onChange={e=>updateP(e.target.value)} /></Field></div></Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">OPT progress</h2><p className="text-sm text-gray-600">Selection: {profile.optIntent ? "Post-Completion OPT" : "Not selected"}</p><p className="mt-3 text-sm text-gray-600">Current stage: {profile.stage.replaceAll("_"," ")}</p><div className="mt-6 flex flex-wrap gap-3"><Link className="rounded-lg border border-[#abc5af] px-4 py-2 text-sm font-medium text-[#336a48]" href="/opt/select">Change OPT selection</Link><Link className="rounded-lg border border-[#abc5af] px-4 py-2 text-sm font-medium text-[#336a48]" href="/opt/status">Update status</Link></div></Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">Offer & timeline</h2><p className="text-sm text-gray-600">Offer: {profile.hasOffer === null ? "Not provided" : profile.hasOffer ? "Yes" : "No"}</p><p className="mt-2 text-sm text-gray-600">Offer start date: {profile.offerStartDate||"Not provided"}</p><Link className="mt-5 inline-block font-semibold text-[#336a48] underline" href="/opt/timeline">Edit timeline inputs →</Link></Panel>
      <Panel><h2 className="mb-5 text-xl font-bold">Privacy & account</h2><p className="text-sm text-gray-600">Signed in as {profile.email}.</p><button disabled={!ready} className="mt-5 rounded-lg border border-red-200 px-4 py-2 text-sm text-red-700" onClick={()=>{if(window.confirm("Delete your account and all your data? This cannot be undone.")){clear();router.push("/");}}}>Delete account and data</button></Panel>
    </div>
  </Shell>;
}
