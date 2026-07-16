"use client";

import { useState } from "react";
import { sendMessageFeedback } from "@/lib/api";

interface Props {
  messageId: string;
  sessionId: string;
  topic?: string;
}

function ThumbIcon({ down = false }: { down?: boolean }) {
  return (
    <svg
      className={`h-4 w-4 ${down ? "rotate-180" : ""}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M1 8.25a1.25 1.25 0 1 1 2.5 0v7.5a1.25 1.25 0 1 1-2.5 0v-7.5ZM11 3V1.7c0-.268.14-.526.395-.607A2 2 0 0 1 14 3c0 .995-.182 1.948-.514 2.826-.204.54.166 1.174.744 1.174h2.52c1.243 0 2.261 1.01 2.146 2.247a23.864 23.864 0 0 1-1.341 5.974C17.153 16.323 16.072 17 14.9 17h-3.192a3 3 0 0 1-1.341-.317l-2.734-1.366A3 3 0 0 0 6.292 15H5V8h.963c.685 0 1.258-.483 1.612-1.068a4.011 4.011 0 0 1 2.166-1.73c.432-.143.853-.386 1.011-.814.16-.432.248-.9.248-1.388Z" />
    </svg>
  );
}

// Thumbs on a single answer. up → sent immediately; down → optional comment
// first. Errors are swallowed into the thanked state on purpose: feedback is
// never worth surfacing an error to the user for.
export function MessageFeedback({ messageId, sessionId, topic }: Props) {
  const [phase, setPhase] = useState<"idle" | "commenting" | "done">("idle");
  const [comment, setComment] = useState("");

  async function submit(rating: "up" | "down", withComment?: string) {
    setPhase("done");
    try {
      await sendMessageFeedback({
        message_id: messageId,
        session_id: sessionId,
        rating,
        comment: withComment?.trim() || undefined,
        topic,
      });
    } catch {
      // ignore — see note above
    }
  }

  if (phase === "done") {
    return (
      <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500" role="status">
        Thanks for your feedback
      </p>
    );
  }

  return (
    <div className="mt-3">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => submit("up")}
          aria-label="Gute Antwort"
          className="rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
        >
          <ThumbIcon />
        </button>
        <button
          type="button"
          onClick={() => setPhase("commenting")}
          aria-label="Schlechte Antwort"
          className={`rounded-lg p-1.5 transition hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 ${
            phase === "commenting" ? "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300" : "text-zinc-400"
          }`}
        >
          <ThumbIcon down />
        </button>
      </div>

      {phase === "commenting" && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit("down", comment);
          }}
          className="mt-2 flex flex-col gap-2"
        >
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="What was wrong? (optional)"
            rows={2}
            dir="auto"
            autoFocus
            className="w-full resize-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
          />
          <button
            type="submit"
            className="self-start rounded-full bg-zinc-800 px-3.5 py-1.5 text-xs font-medium text-white transition hover:bg-zinc-700 dark:bg-zinc-200 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
