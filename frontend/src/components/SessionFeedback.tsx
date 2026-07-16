"use client";

import { useState } from "react";
import { sendSessionFeedback } from "@/lib/api";

interface Props {
  sessionId: string;
  onDismiss: () => void;
}

function Star({ filled }: { filled: boolean }) {
  return (
    <svg
      className={`h-6 w-6 transition ${filled ? "text-amber-400" : "text-zinc-300 dark:text-zinc-600"}`}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.381c-.833.067-1.171 1.107-.536 1.651l3.62 3.102-1.106 4.637c-.194.813.691 1.456 1.405 1.02L10 15.591l4.069 2.485c.713.436 1.598-.207 1.404-1.02l-1.106-4.637 3.62-3.102c.635-.544.297-1.584-.536-1.65l-4.752-.382-1.831-4.401Z"
        clipRule="evenodd"
      />
    </svg>
  );
}

// One-shot rating for the whole conversation; shown once the conversation
// has enough rounds to be worth rating (see page.tsx). Submit and Skip both
// dismiss it for the rest of the session.
export function SessionFeedback({ sessionId, onDismiss }: Props) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState("");

  async function submit() {
    onDismiss();
    try {
      await sendSessionFeedback({
        session_id: sessionId,
        rating,
        comment: comment.trim() || undefined,
      });
    } catch {
      // feedback failures are never surfaced to the user
    }
  }

  return (
    <div className="mx-auto w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-4 text-center shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-800 dark:text-zinc-100">
        Wie hilfreich war dieses Gespräch?
      </p>

      <div
        className="mt-2 flex justify-center"
        role="radiogroup"
        aria-label="Bewertung von 1 bis 5 Sternen"
        onMouseLeave={() => setHovered(0)}
      >
        {[1, 2, 3, 4, 5].map((value) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={rating === value}
            aria-label={`${value} Sterne`}
            onClick={() => setRating(value)}
            onMouseEnter={() => setHovered(value)}
            className="p-1"
          >
            <Star filled={value <= (hovered || rating)} />
          </button>
        ))}
      </div>

      {rating > 0 && (
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Möchten Sie uns mehr sagen? (optional)"
          rows={2}
          dir="auto"
          className="mt-3 w-full resize-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
      )}

      <div className="mt-3 flex justify-center gap-2">
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-full px-4 py-1.5 text-xs font-medium text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200"
        >
          Skip
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={rating === 0}
          className="rounded-full bg-blue-600 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Submit
        </button>
      </div>
    </div>
  );
}
