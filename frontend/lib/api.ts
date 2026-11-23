// Thin client for the backend OPT API (backend/README.md, PRD v1.3 §8.3).
// Every /api/me and /api/assistant call sends the login token as a bearer token.

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const TOKEN_KEY = "paperwork-navigator-token";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* private mode: token lives only for this page */ }
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}${path}`, {
    method,
    cache: "no-store",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (resp.status === 204) return undefined as T;
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new ApiError(resp.status, data?.error?.code ?? "http_error", data?.error?.message ?? resp.statusText);
  return data as T;
}

// --- Response shapes (subset of /openapi.json the UI uses) ---

export type ApiStage = "PLANNING" | "I20_REQUESTED" | "I20_RECEIVED" | "I765_FILED" | "APPROVED";
export type ApiTaskStatus = "NOT_STARTED" | "IN_PROGRESS" | "WAITING_EXTERNAL" | "COMPLETED" | "BLOCKED";
export type YesNoNotSure = "YES" | "NO" | "NOT_SURE";

export type ApiStageDates = {
  i20_request_date: string | null;
  dso_rec_date: string | null;
  i20_issue_date: string | null;
  uscis_receipt_date: string | null;
  requested_start_date: string | null;
};

export type ApiOffer = {
  has_offer: boolean;
  offer_start_date: string | null;
  start_flexible: YesNoNotSure | null;
  start_preference: "ASAP" | "SPECIFIC_DATE" | "NOT_SURE" | null;
  preferred_start_date: string | null;
  premium_intent: YesNoNotSure;
};

export type ApiProfile = {
  email: string;
  degree_level: "BACHELOR" | "MASTER" | "PHD";
  program_end_date: string;
  opt_selection: { opt_intent: string; first_time_at_level: boolean; opt_type: string | null } | null;
  stage: ApiStage | null;
  stage_dates: ApiStageDates;
  offer: ApiOffer | null;
  policy_last_reviewed: string | null;
};

export type ApiNode = {
  id: string;
  date: string | null;
  due_type: "FEDERAL" | "SCHOOL" | "RECOMMENDED" | "EVENT_BASED" | "ESTIMATE" | "USER_DECISION" | "UNKNOWN";
  date_state: "USER_CONFIRMED" | "PARTIAL" | "UNKNOWN" | "CONFLICT";
};

export type ApiTask = {
  id: string;
  title: string;
  status: ApiTaskStatus;
  due_at: string | null;
  due_type: ApiNode["due_type"];
  date_state: ApiNode["date_state"];
  deadline_at: string | null;
  label: "URGENT" | "OVERDUE" | null;
  blocked_by: string[];
  node_ids: string[];
};

export type ApiProcessingTime = {
  id: "school_business_days" | "uscis_standard_days" | "uscis_premium_business_days";
  label: string;
  min: number;
  max: number;
  default: number;
  unit: "calendar_days" | "business_days";
  chosen: number | null;
  used: number;
  note: string | null;
  source_ids: string[];
};

export type ApiChecklist = {
  graduation_banner: { window_opens_on: string; window_closes_on: string };
  modules: { id: string; title: string; status: "OPEN" | "COMING_SOON"; link: string | null }[];
};

export type ApiOffice = {
  office_display_name: string;
  contact_email: string | null;
  phone: string | null;
  office_hours: string | null;
  contact_page_url: string | null;
  preferred_channel: "EMAIL" | "FORM" | "PORTAL";
  advising_form_url: string | null;
  notes: string | null;
};

export type ApiPlan = {
  processing: ApiProcessingTime[];
  version: number;
  branch: "OFFER" | "NO_OFFER";
  window: string;
  too_early: boolean;
  nodes: ApiNode[];
  risk_labels: string[];
  warnings: string[];
  tasks: ApiTask[];
};

export type ApiSource = { id: string; title: string; url: string | null; publisher: string; last_reviewed: string | null };

export type ApiTaskDetail = {
  task: ApiTask;
  template_content: { steps: string[]; documents: { name: string; where_to_get: string | null }[] };
  sources: ApiSource[];
  field_hints: Record<string, string>;
};

export type ApiAssistantReply = {
  conversation_id: string;
  scope: "IN" | "OUT" | "UNSUPPORTED_OPT";
  language: string;
  answer: string;
  sources: ApiSource[];
};

export type ApiDraft = { recipient: string | null; subject: string; body: string; placeholders: string[] };
