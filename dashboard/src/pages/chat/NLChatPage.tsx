import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";

import { nlApi } from "@/lib/nl_api";
import type {
  ExtractedParams,
  FlagCreateRequest,
  NLChatResponse,
} from "@/types/feature_api";
import {
  MessageBubble,
  type ChatMessage,
} from "@/components/chat/MessageBubble";
import { ExtractedParamsPanel } from "@/components/chat/ExtractedParamsPanel";
import { DraftFlagPreview } from "@/components/chat/DraftFlagPreview";

type SidePanelTab = "extracted" | "draft";

export default function NLChatPage(): JSX.Element {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [extracted, setExtracted] = useState<ExtractedParams>({});
  const [draftFlag, setDraftFlag] = useState<FlagCreateRequest | null>(null);
  const [readyToCommit, setReadyToCommit] = useState(false);
  const [committedFlagId, setCommittedFlagId] = useState<string | null>(null);
  const [compactedThisSession, setCompactedThisSession] = useState(false);
  const [input, setInput] = useState("");
  const [tab, setTab] = useState<SidePanelTab>("extracted");
  const [toast, setToast] = useState<{
    message: string;
    flagId: string;
  } | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  const mutation = useMutation<NLChatResponse, Error, string>({
    mutationFn: async (message: string) => {
      return nlApi.chat({ session_id: sessionId, message });
    },
    onSuccess: (data) => {
      setSessionId(data.session_id);
      setExtracted(data.extracted);
      setDraftFlag(data.draft_flag ?? null);
      setReadyToCommit(data.ready_to_commit);
      if (data.compacted) setCompactedThisSession(true);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, ts: new Date() },
      ]);
      if (data.committed_flag_id) {
        setCommittedFlagId(data.committed_flag_id);
        setToast({ message: "Flag created", flagId: data.committed_flag_id });
        setTab("draft");
      }
    },
    onError: (error) => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${error.message}`,
          ts: new Date(),
        },
      ]);
    },
  });

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const locked = Boolean(committedFlagId);
  const sending = mutation.isPending;

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || sending || locked) return;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed, ts: new Date() },
    ]);
    setInput("");
    mutation.mutate(trimmed);
  };

  const handleCommit = () => {
    if (!readyToCommit || locked) return;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: "Commit the flag.", ts: new Date() },
    ]);
    mutation.mutate("commit");
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] w-full">
      {/* Left: message thread + input */}
      <div className="flex w-[60%] flex-col border-r">
        <div className="flex items-center gap-2 border-b px-4 py-3">
          <Sparkles className="h-4 w-4 text-emerald-600" />
          <h1 className="text-sm font-semibold">Flag builder</h1>
          {compactedThisSession ? (
            <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              Context compacted
            </span>
          ) : null}
        </div>
        <div
          ref={threadRef}
          className="flex-1 space-y-3 overflow-y-auto px-4 py-6"
        >
          {messages.length === 0 ? (
            <div className="mx-auto max-w-md rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              Describe the flag in plain English. Example:{" "}
              <span className="font-mono">
                &ldquo;Roll out the new checkout to 20% of users in the
                US&rdquo;
              </span>
              .
            </div>
          ) : null}
          {messages.map((message, idx) => (
            <MessageBubble key={idx} message={message} />
          ))}
          {sending ? (
            <div className="text-xs italic text-muted-foreground">
              Assistant is typing…
            </div>
          ) : null}
        </div>
        <div className="border-t p-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={locked}
            placeholder={
              locked
                ? "Flag committed. Start a new chat to create another."
                : "Describe the flag (Enter to send, Shift+Enter for newline)…"
            }
            rows={3}
            className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:bg-muted"
          />
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={handleSend}
              disabled={sending || locked || !input.trim()}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-slate-50 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      </div>
      {/* Right: side panel with tabs */}
      <div className="flex w-[40%] flex-col">
        <div className="flex border-b">
          <button
            type="button"
            onClick={() => setTab("extracted")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition ${
              tab === "extracted"
                ? "border-b-2 border-slate-900 text-slate-900 dark:border-slate-50 dark:text-slate-50"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Extracted params
          </button>
          <button
            type="button"
            onClick={() => setTab("draft")}
            className={`flex-1 px-4 py-3 text-sm font-medium transition ${
              tab === "draft"
                ? "border-b-2 border-slate-900 text-slate-900 dark:border-slate-50 dark:text-slate-50"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Draft flag preview
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {tab === "extracted" ? (
            <ExtractedParamsPanel extracted={extracted} />
          ) : (
            <DraftFlagPreview
              draft={draftFlag}
              readyToCommit={readyToCommit}
              committing={sending}
              committedFlagId={committedFlagId}
              onCommit={handleCommit}
            />
          )}
        </div>
      </div>
      {toast ? (
        <div className="fixed bottom-6 right-6 z-50 rounded-md border border-emerald-300 bg-emerald-50 px-4 py-3 shadow-lg dark:border-emerald-800 dark:bg-emerald-950/60">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-emerald-900 dark:text-emerald-100">
              {toast.message}
            </span>
            <Link
              to={`/flags/${toast.flagId}`}
              className="text-xs font-semibold text-emerald-700 underline hover:text-emerald-900 dark:text-emerald-300"
            >
              View flag
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
