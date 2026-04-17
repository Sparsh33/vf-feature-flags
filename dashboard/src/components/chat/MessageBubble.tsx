import { cn } from "@/lib/utils";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  ts: Date;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

function renderContent(content: string): JSX.Element[] {
  // Split into code blocks (``` fenced) and plain text.
  const parts = content.split(/(```[\s\S]*?```)/g);
  return parts.map((part, idx) => {
    if (part.startsWith("```") && part.endsWith("```")) {
      const inner = part
        .replace(/^```[a-zA-Z0-9_-]*\n?/, "")
        .replace(/```$/, "");
      return (
        <pre
          key={idx}
          className="my-2 overflow-x-auto rounded-md bg-zinc-900 p-3 font-mono text-xs text-zinc-100"
        >
          {inner}
        </pre>
      );
    }
    return (
      <span key={idx} className="whitespace-pre-wrap">
        {part}
      </span>
    );
  });
}

export function MessageBubble({ message }: MessageBubbleProps): JSX.Element {
  const isUser = message.role === "user";
  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-lg px-4 py-2 text-sm",
          isUser
            ? "bg-slate-700 text-slate-50"
            : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50",
        )}
      >
        <div className="mb-1 text-[10px] uppercase tracking-wide opacity-60">
          {isUser ? "You" : "Assistant"} ·{" "}
          {message.ts.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
        <div>{renderContent(message.content)}</div>
      </div>
    </div>
  );
}
