import type { Source } from "@/lib/api";
import type { UIStrings } from "@/lib/i18n";
import { Markdown } from "@/components/Markdown";
import { MessageFeedback } from "@/components/MessageFeedback";

export interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  topic?: string;
}

function hostnameOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

// Shown whenever an answer touches Bürgergeld — pinned in the UI rather than
// left to the model, which doesn't reliably mention the rename on its own.
function BuergergeldNotice({ text }: { text: string }) {
  return (
    <div className="mt-4 flex gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-[13px] leading-relaxed text-amber-900 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200">
      <svg
        className="mt-0.5 h-4 w-4 shrink-0"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
          clipRule="evenodd"
        />
      </svg>
      <span>{text}</span>
    </div>
  );
}

function SourceList({ sources, label }: { sources: Source[]; label: string }) {
  return (
    <div className="mt-4">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
        {label}
      </p>
      <ol className="flex flex-col gap-1.5">
        {sources.map((source, i) => (
          <li key={i}>
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-start gap-2.5 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 transition hover:border-blue-300 hover:bg-blue-50 dark:border-zinc-700 dark:bg-zinc-800/60 dark:hover:border-blue-500/50 dark:hover:bg-blue-500/10"
            >
              <span
                className="mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded bg-zinc-200 text-[10px] font-semibold text-zinc-600 group-hover:bg-blue-100 group-hover:text-blue-700 dark:bg-zinc-700 dark:text-zinc-300 dark:group-hover:bg-blue-500/20 dark:group-hover:text-blue-300"
                aria-hidden="true"
              >
                {i + 1}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium leading-snug text-zinc-700 group-hover:text-blue-800 dark:text-zinc-200 dark:group-hover:text-blue-300">
                  {source.title}
                </span>
                <span className="block text-[11px] text-zinc-400 dark:text-zinc-500">
                  {hostnameOf(source.url)}
                </span>
              </span>
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ChatMessage({
  message,
  sessionId,
  strings,
}: {
  message: Message;
  sessionId?: string;
  strings: UIStrings;
}) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-2.5 text-[15px] leading-relaxed text-white shadow-sm">
          <p dir="auto" className="whitespace-pre-wrap break-words">
            {message.content}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[95%] rounded-2xl rounded-bl-md border border-zinc-200 bg-white px-4 py-3.5 text-[15px] text-zinc-800 shadow-sm sm:max-w-[88%] dark:border-zinc-700/80 dark:bg-zinc-900 dark:text-zinc-100">
        <Markdown>{message.content}</Markdown>

        {message.topic === "buergergeld" && (
          <BuergergeldNotice text={strings.buergergeldNotice} />
        )}
        {message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} label={strings.sources} />
        )}
        {message.id && sessionId && (
          <MessageFeedback
            messageId={message.id}
            sessionId={sessionId}
            topic={message.topic}
            strings={strings}
          />
        )}
      </div>
    </div>
  );
}
