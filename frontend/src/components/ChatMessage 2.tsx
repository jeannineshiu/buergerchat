import type { Source } from "@/lib/api";

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  topic?: string;
}

// Shown whenever an answer touches Bürgergeld — pinned in the UI rather than
// left to the model, which doesn't reliably mention the rename on its own.
function BuergergeldNotice() {
  return (
    <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
      Hinweis: Seit dem 1. Juli 2026 heißt „Bürgergeld“ offiziell
      „Grundsicherungsgeld“ (Neue Grundsicherung). Es handelt sich um dieselbe Leistung.
    </div>
  );
}

export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>

        {!isUser && message.topic === "buergergeld" && <BuergergeldNotice />}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 border-t border-gray-300 pt-2 dark:border-gray-700">
            <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Quellen</p>
            <ul className="space-y-1">
              {message.sources.map((source, i) => (
                <li key={i}>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {source.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
