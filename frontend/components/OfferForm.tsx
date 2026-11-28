"use client";
import { useState } from "react";
import { actions, useDemoProfile, type Profile } from "@/lib/demo";
import { Field, inputClass } from "@/components/Shell";

/** Offer or start-date preference, saved through the plan. Used by /setup Step 4 and /opt/timeline. */
export default function OfferForm({ onSaved, submitLabel, showDsoDate = false, onSavingChange, presetHasOffer }: {
  onSaved: () => void;
  submitLabel: string;
  showDsoDate?: boolean;
  onSavingChange?: (saving: boolean) => void;
  presetHasOffer?: boolean;  // "I got an offer!" on /opt/timeline opens the form with Yes chosen
}) {
  const { profile: saved, ready, error: loadError } = useDemoProfile();
  const [draft, setDraft] = useState<Partial<Profile>>(presetHasOffer === undefined ? {} : { hasOffer: presetHasOffer });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const profile = { ...saved, ...draft };

  function change<K extends keyof Profile>(key: K, value: Profile[K]) {
    setDraft(current => ({ ...current, [key]: value }));
  }
  async function submit() {
    setSaving(true); onSavingChange?.(true); setError("");
    try {
      await actions.calculateTimeline(profile);
      setDraft({});
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false); onSavingChange?.(false);
    }
  }

  return <>
    <fieldset disabled={!ready || saving} className="grid gap-5 sm:grid-cols-2">
      <Field label="Do you have a job offer with a start date?">
        <select className={inputClass} value={profile.hasOffer === null ? "" : profile.hasOffer ? "yes" : "no"} onChange={e => change("hasOffer", e.target.value === "" ? null : e.target.value === "yes")}>
          <option value="">Choose</option><option value="yes">Yes</option><option value="no">No</option>
        </select>
      </Field>
      {profile.hasOffer === true && <>
        <Field label="Offer start date"><input type="date" className={inputClass} value={profile.offerStartDate} onChange={e => change("offerStartDate", e.target.value)} /></Field>
        <Field label="Is your start date flexible?"><select className={inputClass} value={profile.startFlexible} onChange={e => change("startFlexible", e.target.value as Profile["startFlexible"])}><option value="yes">Yes</option><option value="no">No</option><option value="unsure">Not sure</option></select></Field>
      </>}
      {profile.hasOffer === false && <>
        <Field label="Preferred OPT start"><select className={inputClass} value={profile.startPreference} onChange={e => change("startPreference", e.target.value as Profile["startPreference"])}><option value="ASAP">As soon as possible</option><option value="SPECIFIC">Specific date</option><option value="UNSURE">Not sure</option></select></Field>
        {profile.startPreference === "SPECIFIC" && <Field label="Preferred start date"><input type="date" className={inputClass} value={profile.preferredStartDate} onChange={e => change("preferredStartDate", e.target.value)} /></Field>}
      </>}
      <Field label="Plan to use premium processing?"><select className={inputClass} value={profile.premiumIntent} onChange={e => change("premiumIntent", e.target.value as Profile["premiumIntent"])}><option value="unsure">Not sure</option><option value="yes">Yes</option><option value="no">No</option></select></Field>
      {showDsoDate && (profile.stage === "I20_RECEIVED" || !!profile.dsoRecDate) && <Field label="DSO recommendation date (SEVIS)" hint="Confirm the SEVIS date with UW ISS. The I-20 issue date may differ."><input type="date" className={inputClass} value={profile.dsoRecDate} onChange={e => change("dsoRecDate", e.target.value)} /></Field>}
    </fieldset>
    {profile.hasOffer === false && <p className="mt-4 rounded-lg bg-[#eef4ef] p-4 text-sm leading-relaxed text-[#31533f]">Choosing an earlier requested OPT start date may permit an earlier start once authorized, but can also begin the unemployment-day period sooner. A later date may reduce that exposure but delays possible work authorization. Confirm your choice with UW ISS.</p>}
    <button type="button" onClick={submit} disabled={!ready || saving} className="mt-6 rounded-xl bg-[#336a48] px-6 py-3 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : submitLabel}</button>
    {(error || loadError) && <p role="alert" className="mt-3 text-sm text-red-700">{error || loadError}</p>}
  </>;
}
