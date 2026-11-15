"use client";

import { usePathname } from "next/navigation";
import { useState } from "react";
import { api, type ApiAssistantReply, type ApiDraft } from "@/lib/api";
import { useDemoProfile } from "@/lib/demo";

type View = "default" | "answer" | "contact";
type Message = { role: "user" | "assistant"; text: string; sources?: { title: string; url: string | null }[] };
const QUESTION_TYPES: Record<string, string> = { "Confirm dates": "CONFIRM_DATES", "I-20 status": "I20_STATUS", Documents: "DOCUMENTS", "RFE or denial": "RFE_OR_DENIAL", Other: "OTHER" };

function pageOf(path: string): { page: string; taskId: string | null } {
  const task = path.match(/\/opt\/tasks\/(T\d+)/);
  if (task) return { page: "task", taskId: task[1] };
  const page = path.startsWith("/opt/timeline") ? "timeline" : path.startsWith("/opt/select") ? "select_opt" : path.startsWith("/opt/status") ? "status" : path.startsWith("/home") ? "home" : "checklist";
  return { page, taskId: null };
}
const DISCLAIMER = "This product does not provide legal advice. Please verify requirements and filing dates with your international student office and USCIS.";

function suggestedQuestions(path: string, stage: string): string[] {
  if (path.includes("/opt/tasks/T02")) return ["What is an OPT I-20?", "How do I request it at UW?", "How long does UW take?"];
  if (path.includes("/opt/tasks/T03")) return ["Where do I find my recommendation date?", "What if my I-20 has an error?"];
  if (path.includes("/opt/tasks/T04")) return ["What documents do I need?", "Where do I get my I-94?"];
  if (path.includes("/opt/tasks/T05")) return ["What is Form I-765?", "How do I file it?", "What happens after I file?"];
  if (path.includes("/opt/tasks/T06")) return ["How do I check my case status?", "What if I get an RFE?", "When can I start working?"];
  if (path.startsWith("/opt/timeline")) return ["How should I pick my start date?", "What if my EAD comes late?", "Why is this date unconfirmed?"];
  if (path.startsWith("/opt/select")) return ["Which OPT is right for me?", "What's the difference between OPT types?"];
  if (path.startsWith("/checklist")) return stage === "PLANNING" ? ["What is OPT?", "What's my first step?", "Who do I contact at UW?"] : ["What should I do next?", "When is my filing deadline?", "What documents do I need?"];
  if (path.startsWith("/home")) return ["Why does my graduation date matter?", "How do I change my OPT selection?"];
  return ["What is OPT?", "What's my next step?", "Who do I contact at UW?"];
}

function fallbackDraft(topic: string, question: string, stage: string): { subject: string; body: string } {
  const subject = `Question about ${topic === "Other" ? "post-completion OPT" : topic.toLowerCase()}`;
  const body = `Dear UW International Student Services,\n\nMy name is [YOUR FULL NAME], and I am a UW F-1 student preparing for post-completion OPT.\n\nMy current application stage is ${stage.replaceAll("_", " ").toLowerCase()}.\n\nI would appreciate guidance on the following question:\n${question.trim() || "[DESCRIBE YOUR QUESTION]"}\n\nThank you for your time and assistance.\n\nBest regards,\n[YOUR FULL NAME]`;
  return { subject, body };
}

export default function OptAssistantWidget() {
  const path = usePathname() || "";
  const { profile } = useDemoProfile();
  const [open, setOpen] = useState(false);
  const [view, setView] = useState<View>("default");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);
  const [topic, setTopic] = useState("Confirm dates");
  const [contactQuestion, setContactQuestion] = useState("");
  const [draft, setDraft] = useState<{ subject: string; body: string } | null>(null);
  const [copyNote, setCopyNote] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const officePage = "https://iss.washington.edu/";
  const chips = suggestedQuestions(path, profile.stage);

  async function submitQuestion(value: string) {
    const entered = value.trim();
    if (!entered || busy) return;
    setMessages(old => [...old, { role: "user", text: entered }]);
    setQuestion("");
    setFeedback(null);
    setView("answer");
    setBusy(true);
    const { page, taskId } = pageOf(path);
    try {
      const reply = await api<ApiAssistantReply>("POST", "/api/assistant/messages", { message: entered, current_page: page, current_task_id: taskId, conversation_id: conversationId });
      setConversationId(reply.conversation_id);
      setMessages(old => [...old, { role: "assistant", text: reply.answer, sources: reply.sources }]);
    } catch (e) {
      setMessages(old => [...old, { role: "assistant", text: `The assistant is unavailable right now (${e instanceof Error ? e.message : "error"}). Please check with UW ISS.` }]);
    } finally {
      setBusy(false);
    }
  }

  async function prepareDraft() {
    setCopyNote("");
    const { taskId } = pageOf(path);
    try {
      const d = await api<ApiDraft>("POST", "/api/me/dso-drafts", { question_type: QUESTION_TYPES[topic] ?? "OTHER", user_question: contactQuestion.trim() || "[DESCRIBE YOUR QUESTION]", current_task_id: taskId, conversation_id: conversationId });
      setDraft({ subject: d.subject, body: d.body });
    } catch {
      setDraft(fallbackDraft(topic, contactQuestion, profile.stage));
    }
  }

  function showContact() {
    setContactQuestion(messages.filter(m => m.role === "user").at(-1)?.text || question);
    setView("contact");
    setCopyNote("");
  }

  async function copyDraft() {
    if (!draft) return;
    try { await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`); setCopyNote("Draft copied. Review before sending."); }
    catch { setCopyNote("Copy failed. Select and copy the draft manually."); }
  }

  const available = !["/", "/login", "/onboarding"].includes(path);
  if (!available) return null;

  return <div id="ask-ai" className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
    {open && <section role="dialog" aria-label="OPT assistant" aria-modal="false" className="fixed inset-0 flex h-[100dvh] w-screen flex-col overflow-hidden bg-white shadow-2xl sm:static sm:mb-3 sm:h-[min(680px,calc(100dvh-95px))] sm:w-[390px] sm:rounded-2xl sm:border sm:border-[#dbe4d9]">
      <header className="flex shrink-0 items-center justify-between bg-[#eef4ed] px-5 py-4">
        <div><h2 className="font-semibold text-[#244b35]">✦ OPT Assistant</h2><p className="text-xs text-gray-600">UW · Post-Completion OPT · Demo</p></div>
        <button type="button" onClick={() => setOpen(false)} aria-label="Close assistant" className="rounded-lg px-2 py-1 text-lg hover:bg-white">×</button>
      </header>
      <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm sm:p-5">
        {view === "contact" ? <>
          <button type="button" onClick={() => setView(messages.length ? "answer" : "default")} className="font-semibold text-[#336a48] hover:underline">← Back to assistant</button>
          <h3 className="text-base font-semibold">Contact My International Student Office</h3>
          <div className="rounded-xl bg-[#f3f6f1] p-4">
            <p className="font-semibold">University of Washington · International Student Services (ISS)</p>
            <p className="mt-1 text-xs text-gray-600">Official contact details and preferred contact channel must be verified in the UW Policy Pack before release.</p>
            <a href={officePage} target="_blank" rel="noreferrer" className="mt-3 inline-block font-semibold text-[#336a48] underline">Visit official UW ISS website ↗</a>
          </div>
          <label className="block space-y-1 font-medium">What do you need help with?
            <select value={topic} onChange={e => { setTopic(e.target.value); setDraft(null); }} className="mt-1 w-full rounded-xl border border-[#d9e0d8] p-3 font-normal">
              {["Confirm dates", "I-20 status", "Documents", "RFE or denial", "Other"].map(x => <option key={x}>{x}</option>)}
            </select>
          </label>
          <label className="block space-y-1 font-medium">Describe your question
            <textarea rows={3} value={contactQuestion} onChange={e => { setContactQuestion(e.target.value); setDraft(null); }} className="mt-1 w-full rounded-xl border border-[#d9e0d8] p-3 font-normal" placeholder="What would you like to ask your school's international student office?" />
          </label>
          <button type="button" onClick={prepareDraft} className="w-full rounded-xl bg-[#336a48] px-4 py-3 font-semibold text-white">Draft my email</button>
          {draft && <div className="space-y-2 rounded-xl border border-[#dbe4d9] p-3">
            <p className="text-xs text-gray-600">Editable draft — fill in the [PLACEHOLDERS]. The app never sends it.</p>
            <label className="block text-xs font-semibold">Subject<input value={draft.subject} onChange={e => setDraft({ ...draft, subject: e.target.value })} className="mt-1 w-full rounded-lg border p-2 text-sm font-normal" /></label>
            <label className="block text-xs font-semibold">Body<textarea rows={9} value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })} className="mt-1 w-full rounded-lg border p-2 text-sm font-normal" /></label>
            <button type="button" onClick={copyDraft} className="rounded-lg border border-[#336a48] px-3 py-2 font-semibold text-[#336a48]">Copy draft</button>
            {copyNote && <p role="status" className="text-xs text-gray-600">{copyNote}</p>}
          </div>}
        </> : <>
          {view === "default" ? <>
            <div className="rounded-xl bg-[#f3f6f1] p-4"><p className="font-semibold">Hi! How can I help with your OPT journey?</p><p className="mt-1 text-gray-600">Ask about OPT steps, dates, or which school office to contact.</p></div>
            <p className="text-xs text-gray-500">Current stage: {profile.stage.replaceAll("_", " ")}</p>
          </> : <div aria-live="polite" className="space-y-3">
            {messages.map((m, i) => <div key={i} className={`rounded-xl p-3 leading-relaxed ${m.role === "user" ? "ml-7 bg-[#eaf2e9]" : "mr-5 border border-[#e4e9e3] bg-[#fafbf9]"}`}><p className="mb-1 text-xs font-semibold text-gray-600">{m.role === "user" ? "You" : "OPT Assistant · Demo"}</p><p className="whitespace-pre-line">{m.text}</p>{m.sources && m.sources.length > 0 && <p className="mt-2 text-xs text-gray-500">Sources: {m.sources.map(src => src.url ? <a key={src.title} href={src.url} target="_blank" rel="noreferrer" className="underline">{src.title}</a> : <span key={src.title}>{src.title} (link pending review)</span>)}</p>}{m.role === "assistant" && i === messages.length - 1 && <div className="mt-3 flex gap-3 text-xs"><button type="button" onClick={() => setFeedback("up")} aria-label="Helpful response" aria-pressed={feedback === "up"}>👍</button><button type="button" onClick={() => setFeedback("down")} aria-label="Not helpful response" aria-pressed={feedback === "down"}>👎</button><a className="text-[#336a48] underline" href={officePage} target="_blank" rel="noreferrer">UW ISS official website ↗</a></div>}</div>)}
          </div>}
          <div><p className="mb-2 text-xs font-semibold text-gray-600">Suggested questions</p><div className="flex flex-wrap gap-2">{chips.map(q => <button type="button" key={q} onClick={() => submitQuestion(q)} className="rounded-full border border-[#dce4da] px-3 py-2 text-xs text-[#2c5d40] hover:bg-[#f2f6f0]">{q}</button>)}</div></div>
          <form onSubmit={e => { e.preventDefault(); submitQuestion(question); }} className="space-y-2"><label htmlFor="opt-assistant-input" className="block text-xs font-semibold">Ask a question about OPT</label><textarea id="opt-assistant-input" rows={2} value={question} onChange={e => setQuestion(e.target.value)} className="w-full rounded-xl border border-[#d9e0d8] p-3" placeholder="Type your question..."/><button type="submit" disabled={!question.trim() || busy} className="rounded-xl bg-[#336a48] px-4 py-2 font-semibold text-white disabled:opacity-50">{busy ? "Sending…" : "Send"}</button></form>
          <button type="button" onClick={showContact} className="w-full rounded-xl border border-[#336a48] p-3 font-semibold text-[#336a48]">Contact My International Student Office</button>
        </>}
      </div>
      <footer className="shrink-0 border-t border-[#e4e9e3] bg-[#fafbf9] px-4 py-3"><p className="text-[11px] leading-relaxed text-gray-600">{DISCLAIMER}</p><p className="mt-1 text-[11px] text-gray-500">Mock assistant: answers are placeholders and contact data is not verified. Do not enter passport, SEVIS, I-94 or student ID numbers.</p></footer>
    </section>}
    <button id="opt-assistant-toggle" type="button" onClick={() => setOpen(x => !x)} aria-expanded={open} aria-label="Toggle OPT assistant" className="ml-auto block rounded-full bg-[#336a48] px-5 py-3 text-sm font-semibold text-white shadow-xl">{open ? "Close" : "✦ Ask AI"}</button>
  </div>;
}
