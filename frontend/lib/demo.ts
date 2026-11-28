"use client";
// Shared client state for the OPT pages, backed by the backend API.
// The backend owns all rules and dates (Plan Service); this module only fetches, adapts field
// names for the pages, and sends edits. Pages read it through useDemoProfile().

import { useEffect, useSyncExternalStore } from "react";
import { api, ApiError, getToken, setToken, type ApiFeedback, type ApiHistoryEntry, type ApiOffer, type ApiProcessingTime, type ApiPlan, type ApiProfile, type ApiTask } from "./api";

export type Stage = "PLANNING" | "I20_REQUESTED" | "I20_RECEIVED" | "I765_FILED" | "APPROVED";
export type TaskStatus = "NOT_STARTED" | "IN_PROGRESS" | "WAITING_EXTERNAL" | "COMPLETED" | "BLOCKED";

export type Profile = {
  email: string;
  programEndDate: string;
  degree: "Bachelor" | "Master" | "PhD";
  optIntent: string;
  firstTime: boolean | null;
  stage: Stage;
  i20RequestDate: string;
  dsoRecDate: string;
  i20IssueDate: string;
  uscisReceiptDate: string;
  requestedStartDate: string;
  hasOffer: boolean | null;
  offerStartDate: string;
  startFlexible: "yes" | "no" | "unsure";
  startPreference: "ASAP" | "SPECIFIC" | "UNSURE";
  preferredStartDate: string;
  premiumIntent: "yes" | "no" | "unsure";
  taskStatuses: Record<string, TaskStatus>;
};

const EMPTY: Profile = {
  email: "", programEndDate: "", degree: "Master", optIntent: "", firstTime: null, stage: "PLANNING",
  i20RequestDate: "", dsoRecDate: "", i20IssueDate: "", uscisReceiptDate: "", requestedStartDate: "",
  hasOffer: null, offerStartDate: "", startFlexible: "unsure", startPreference: "UNSURE", preferredStartDate: "",
  premiumIntent: "unsure", taskStatuses: {},
};

/** Where a student is in /setup. Processing times and the timeline review are optional, so they never block. */
export type SetupStep = "program" | "opt" | "progress" | "offer" | "done";

export function nextSetupStep(p: ApiProfile | null): SetupStep {
  if (!p) return "program";
  const sel = p.opt_selection;
  if (!sel || sel.opt_intent !== "AFTER_GRADUATION" || !sel.first_time_at_level) return "opt";
  if (p.stage === null) return "progress";
  if (p.offer === null) return "offer";
  return "done";
}

type State = { profile: Profile; plan: ApiPlan | null; ready: boolean; onboarded: boolean; setupStep: SetupStep; error: string };
let state: State = { profile: EMPTY, plan: null, ready: false, onboarded: false, setupStep: "program", error: "" };
let loading: Promise<void> | null = null;
const listeners = new Set<() => void>();

function setState(patch: Partial<State>) {
  state = { ...state, ...patch };
  listeners.forEach(l => l());
}

// --- Field mapping between the API (snake_case enums) and the pages ---

const DEGREE_TO_UI = { BACHELOR: "Bachelor", MASTER: "Master", PHD: "PhD" } as const;
const DEGREE_TO_API = { Bachelor: "BACHELOR", Master: "MASTER", PhD: "PHD" } as const;
const YN_TO_UI = { YES: "yes", NO: "no", NOT_SURE: "unsure" } as const;
const YN_TO_API = { yes: "YES", no: "NO", unsure: "NOT_SURE" } as const;
const PREF_TO_UI = { ASAP: "ASAP", SPECIFIC_DATE: "SPECIFIC", NOT_SURE: "UNSURE" } as const;
const PREF_TO_API = { ASAP: "ASAP", SPECIFIC: "SPECIFIC_DATE", UNSURE: "NOT_SURE" } as const;

function fromApi(p: ApiProfile, plan: ApiPlan): Profile {
  const d = p.stage_dates, o = p.offer;
  return {
    email: p.email,
    programEndDate: p.program_end_date,
    degree: DEGREE_TO_UI[p.degree_level],
    optIntent: p.opt_selection?.opt_intent ?? "",
    firstTime: p.opt_selection?.first_time_at_level ?? null,
    stage: p.stage ?? "PLANNING",
    i20RequestDate: d.i20_request_date ?? "",
    dsoRecDate: d.dso_rec_date ?? "",
    i20IssueDate: d.i20_issue_date ?? "",
    uscisReceiptDate: d.uscis_receipt_date ?? "",
    requestedStartDate: d.requested_start_date ?? "",
    hasOffer: o?.has_offer ?? null,
    offerStartDate: o?.offer_start_date ?? "",
    startFlexible: o?.start_flexible ? YN_TO_UI[o.start_flexible] : "unsure",
    startPreference: o?.start_preference ? PREF_TO_UI[o.start_preference] : "UNSURE",
    preferredStartDate: o?.preferred_start_date ?? "",
    premiumIntent: o ? YN_TO_UI[o.premium_intent] : "unsure",
    taskStatuses: Object.fromEntries((plan?.tasks ?? []).map(t => [t.id, t.status])),
  };
}

function offerBody(p: Profile): ApiOffer | null {
  if (p.hasOffer === null) return null;
  if (p.hasOffer && !p.offerStartDate) return null;
  if (!p.hasOffer && p.startPreference === "SPECIFIC" && !p.preferredStartDate) return null;
  return {
    has_offer: p.hasOffer,
    offer_start_date: p.hasOffer ? p.offerStartDate : null,
    start_flexible: p.hasOffer ? YN_TO_API[p.startFlexible] : null,
    start_preference: p.hasOffer ? null : PREF_TO_API[p.startPreference],
    preferred_start_date: !p.hasOffer && p.startPreference === "SPECIFIC" ? p.preferredStartDate : null,
    premium_intent: YN_TO_API[p.premiumIntent],
  };
}

function stageDates(p: Profile) {
  const v = (s: string) => s || null;
  return {
    i20_request_date: v(p.i20RequestDate), dso_rec_date: v(p.dsoRecDate), i20_issue_date: v(p.i20IssueDate),
    uscis_receipt_date: v(p.uscisReceiptDate), requested_start_date: v(p.requestedStartDate),
  };
}

// --- Loading and errors ---

function handleError(e: unknown): never {
  if (e instanceof ApiError && e.status === 401) {
    setToken(null);
    setState({ profile: EMPTY, plan: null, onboarded: false, setupStep: "program" });
    if (typeof window !== "undefined" && !["/", "/login"].includes(window.location.pathname)) window.location.href = "/login";
  }
  throw e;
}

export async function refresh(): Promise<void> {
  if (!getToken()) { setState({ profile: EMPTY, plan: null, ready: true, onboarded: false, setupStep: "program" }); return; }
  try {
    const { profile } = await api<{ profile: ApiProfile }>("GET", "/api/me/profile");
    const plan = await api<ApiPlan>("GET", "/api/me/opt-plan");
    setState({ profile: fromApi(profile, plan), plan, ready: true, onboarded: true, setupStep: nextSetupStep(profile), error: "" });
  } catch (e) {
    if (e instanceof ApiError && e.code === "onboarding_required") {
      setState({ profile: EMPTY, plan: null, ready: true, onboarded: false, setupStep: "program" });
      return;
    }
    setState({ ready: true, error: e instanceof Error ? e.message : String(e) });
    handleError(e);
  }
}

function ensureLoaded() {
  if (!loading) loading = refresh().catch(() => {});
}

// --- Actions ---

export const actions = {
  async startLogin(email: string) {
    await api("POST", "/api/auth/email/start", { email });
  },
  async verify(email: string, code: string, tosAccepted = true) {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const res = await api<{ token: string }>("POST", "/api/auth/email/verify", { email, code, tos_accepted: tosAccepted, timezone });
    setToken(res.token);
    await refresh();
    return state.setupStep;
  },
  async onboard(programEndDate: string, degree: Profile["degree"]) {
    await api("PUT", "/api/me/onboarding", { school_id: "uw", program_end_date: programEndDate, degree_level: DEGREE_TO_API[degree] }).catch(handleError);
    await refresh();
  },
  /** Setup Step 1 for a student who is already onboarded: PATCH keeps later answers (PUT /onboarding resets them). */
  async updateProgram(programEndDate: string, degree: Profile["degree"]) {
    await api("PATCH", "/api/me/profile", { program_end_date: programEndDate, degree_level: DEGREE_TO_API[degree] }).catch(handleError);
    await refresh();
  },
  async selectOpt(optIntent: string, firstTime: boolean) {
    await api("PUT", "/api/me/opt-selection", { opt_intent: optIntent, first_time_at_level: firstTime }).catch(handleError);
    await refresh();
  },
  async saveStatus(stage: Stage, dates: Partial<Profile>) {
    await api("PUT", "/api/me/status", { stage, ...stageDates({ ...state.profile, ...dates }) }).catch(handleError);
    await refresh();
  },
  async calculateTimeline(profile: Profile) {
    const body = offerBody(profile);
    if (!body) throw new Error("Choose a planning option and enter any required start date.");
    if (profile.dsoRecDate !== state.profile.dsoRecDate) {
      await api("PUT", "/api/me/status", { stage: profile.stage, ...stageDates(profile) }).catch(handleError);
    }
    await api("PUT", "/api/me/offer", body).catch(handleError);
    await refresh();
  },
  /** Range editor: the student got their OPT I-20, so the stage moves to I20_RECEIVED with the real R. */
  async enterDsoRecDate(date: string) {
    await api("PUT", "/api/me/status", { ...stageDates(state.profile), stage: "I20_RECEIVED", dso_rec_date: date }).catch(handleError);
    await refresh();
  },
  /** Range editor: a student without an offer picks a specific OPT start date. */
  async pickStartDate(date: string) {
    const p = state.profile;
    await api("PUT", "/api/me/offer", { has_offer: false, offer_start_date: null, start_flexible: null,
      start_preference: "SPECIFIC_DATE", preferred_start_date: date, premium_intent: YN_TO_API[p.premiumIntent] }).catch(handleError);
    await refresh();
  },
  async saveProcessingTimes(choices: Partial<Record<ApiProcessingTime["id"], number | null>>) {
    await api("PUT", "/api/me/processing-times", choices).catch(handleError);
    await refresh();
  },
  async updateTask(taskId: string, status: TaskStatus, dates: Record<string, string> = {}) {
    const res = await api<{ task: ApiTask }>("PATCH", `/api/me/tasks/${taskId}`, { status, ...dates }).catch(handleError);
    await refresh();
    return res.task;
  },
  async deleteAccount() {
    await api("DELETE", "/api/me").catch(() => {});
    setToken(null);
    setState({ profile: EMPTY, plan: null, onboarded: false, setupStep: "program" });
  },
  /** Start over: the backend keeps the current plan in history, then the user re-does onboarding. */
  async startOver() {
    await api("POST", "/api/me/reset").catch(handleError);
    setState({ profile: EMPTY, plan: null, onboarded: false, setupStep: "program" });
  },
  /** Make a past plan current again. The backend moves the current plan into history. */
  async restorePlan(entryId: string) {
    await api("POST", `/api/me/history/${encodeURIComponent(entryId)}/restore`).catch(handleError);
    await refresh();
    return state.setupStep;
  },
  async history() {
    const res = await api<{ entries: ApiHistoryEntry[] }>("GET", "/api/me/history").catch(handleError);
    return res.entries;
  },
  async sendFeedback(feedback: ApiFeedback) {
    await api("POST", "/api/assistant/feedback", feedback).catch(handleError);
  },
};

/** Profile edits from Home. */
async function save(patch: Partial<Profile>) {
  const next = { ...state.profile, ...patch };
  setState({ profile: next });
  const keys = Object.keys(patch) as (keyof Profile)[];
  try {
    if (keys.includes("programEndDate") || keys.includes("degree")) {
      await api("PATCH", "/api/me/profile", { program_end_date: next.programEndDate || null, degree_level: DEGREE_TO_API[next.degree] });
    }
    await refresh();
  } catch (e) {
    setState({ error: e instanceof Error ? e.message : String(e) });
    handleError(e);
  }
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const SERVER_STATE: State = { profile: EMPTY, plan: null, ready: false, onboarded: false, setupStep: "program", error: "" };

export function useDemoProfile() {
  const s = useSyncExternalStore(subscribe, () => state, () => SERVER_STATE);
  useEffect(ensureLoaded, []);
  return {
    profile: s.profile,
    plan: s.plan,
    tasks: s.plan?.tasks ?? [],
    ready: s.ready,
    onboarded: s.onboarded,
    setupStep: s.setupStep,
    error: s.error,
    save: (patch: Partial<Profile>) => { save(patch).catch(() => {}); },
    clear: () => { actions.deleteAccount(); },
  };
}

// --- Helpers used by the pages ---

export function taskState(profile: Profile, taskId: string): TaskStatus {
  return profile.taskStatuses[taskId] ?? "NOT_STARTED";
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Not set";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

// --- Timeline view model (from the backend plan; no date math here) ---

export type TimelineWarning = {
  code: "AT_RISK" | "GAP_WARNING" | "WINDOW_CLOSED" | "CONFLICT" | "OUT_OF_SCOPE" | "MISSING_INFO" | "SEVIS_DATE_UNCONFIRMED";
  message: string;
  action: string;
  taskId?: string;
};
export type TimelineNode = { id: string; label: string; date: string; kind: string; dateState: string; note: string; taskId: string };
export type TimelineView = {
  nodes: TimelineNode[];
  warnings: TimelineWarning[];
  next: { label: string; date: string; kind: string; taskId: string } | null;
  blocked: boolean;
};

const NODE_INFO: Record<string, { label: string; taskId: string; note: string }> = {
  N1: { label: "Request your OPT I-20 from UW ISS", taskId: "T02", note: "Target date based on UW's estimated processing time." },
  N1b: { label: "OPT I-20 expected", taskId: "T03", note: "Estimated until you enter your DSO recommendation date." },
  N1d: { label: "UW deadline to request your OPT I-20", taskId: "T02", note: "School deadline set by UW ISS." },
  N2: { label: "Earliest I-765 filing date", taskId: "T05", note: "Based on your program end date and OPT I-20 recommendation." },
  N3: { label: "Recommended I-765 filing date", taskId: "T05", note: "File by this date so your EAD can arrive in time." },
  N4: { label: "Latest I-765 filing date", taskId: "T05", note: "USCIS must receive your I-765 by this date." },
  N5: { label: "OPT start date on your I-765", taskId: "T04", note: "The start date you request on Form I-765." },
  N6: { label: "EAD card expected", taskId: "T06", note: "Estimated from USCIS processing times." },
  N7: { label: "Earliest day you can start working", taskId: "T06", note: "You need the EAD card in hand and its start date reached." },
};

function kindOf(dueType: string, date: string | null, dateState = ""): string {
  if (!date) return "Not confirmed";
  if (dueType === "EVENT_BASED" && dateState === "USER_CONFIRMED") return "School";  // e.g. your DSO recommendation date
  return { FEDERAL: "Federal deadline", SCHOOL: "School", RECOMMENDED: "Recommended", ESTIMATE: "Estimate", EVENT_BASED: "Estimate", USER_DECISION: "Your choice" }[dueType] ?? "Not confirmed";
}

const RISK_TEXT: Record<string, Omit<TimelineWarning, "code">> = {
  SEVIS_DATE_UNCONFIRMED: { message: "Your latest filing date is based on your I-20 issue date. The actual deadline may be earlier. Confirm your SEVIS recommendation date with UW ISS.", action: "Enter your confirmed SEVIS date", taskId: "T03" },
  AT_RISK: { message: "Based on current processing estimates, your EAD may not arrive before your offer start date.", action: "Prepare your documents now and talk to UW ISS", taskId: "T04" },
  GAP_WARNING: { message: "Your offer starts more than 60 days after your Program End Date. Your OPT start date can be no later than that, and the days in between may count as unemployment.", action: "Review your OPT start date", taskId: "T04" },
  WINDOW_CLOSED: { message: "The filing window closed 60 days after your Program End Date.", action: "Contact UW ISS" },
  CONFLICT: { message: "The dates you entered don't leave a valid filing date.", action: "Check your dates with UW ISS", taskId: "T03" },
  OUT_OF_SCOPE: { message: "An offer that starts on or before your Program End Date is not post-completion OPT.", action: "Contact UW ISS" },
};

export function buildDemoTimeline(profile: Profile, plan: ApiPlan | null): TimelineView {
  if (!plan) return { nodes: [], warnings: [], next: null, blocked: false };
  const nodes = plan.nodes.map(n => ({
    id: n.id,
    label: NODE_INFO[n.id]?.label ?? n.id,
    date: n.date ?? "",
    kind: kindOf(n.due_type, n.date, n.date_state),
    dateState: n.date_state,
    note: n.id === "N4" && n.date_state === "PARTIAL"
      ? "May be earlier once you add your DSO recommendation date."
      : n.id === "N1b" && n.due_type === "EVENT_BASED" && n.date_state === "USER_CONFIRMED"
        ? profile.i20IssueDate ? "The issue date you entered for your OPT I-20." : "The DSO recommendation date you entered."
        : NODE_INFO[n.id]?.note ?? "",
    taskId: NODE_INFO[n.id]?.taskId ?? "T01",
  }));
  const warnings: TimelineWarning[] = plan.risk_labels.filter(code => code in RISK_TEXT)
    .map(code => ({ code: code as TimelineWarning["code"], ...RISK_TEXT[code] }));
  if (!plan.risk_labels.includes("SEVIS_DATE_UNCONFIRMED") && !profile.dsoRecDate && plan.nodes.some(n => n.id === "N4" && n.date_state === "PARTIAL")) {
    warnings.push({ code: "MISSING_INFO", message: "Your latest filing date may be earlier once you add your DSO recommendation date.", action: "Add your recommendation date", taskId: "T03" });
  }
  // Your next step: something you can act on now (not done, not blocked, not waiting on the school or USCIS).
  const open = plan.tasks.filter(t => !["COMPLETED", "BLOCKED", "WAITING_EXTERNAL"].includes(t.status));
  const nextTask = open.find(t => t.due_at) ?? open[0];
  return {
    nodes,
    warnings,
    next: nextTask ? { label: nextTask.title, date: nextTask.due_at ?? "", kind: kindOf(nextTask.due_type, nextTask.due_at), taskId: nextTask.id } : null,
    blocked: plan.risk_labels.some(r => ["WINDOW_CLOSED", "CONFLICT", "OUT_OF_SCOPE"].includes(r)),
  };
}
