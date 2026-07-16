"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, type Message } from "@/components/ChatMessage";
import { StarterPrompts } from "@/components/StarterPrompts";
import { LanguageSelect } from "@/components/LanguageSelect";
import { SessionFeedback } from "@/components/SessionFeedback";
import { sendChatMessage } from "@/lib/api";

function BrandMark() {
  return (
    <div
      className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-blue-600 shadow-sm"
      aria-hidden="true"
    >
      <svg className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
        <path
          fillRule="evenodd"
          d="M10 2c-4.418 0-8 3.134-8 7 0 2.254 1.225 4.26 3.132 5.541-.13.826-.507 1.561-1.06 2.14a.5.5 0 0 0 .37.844c1.437-.03 2.75-.52 3.81-1.315.567.122 1.157.19 1.748.19 4.418 0 8-3.134 8-7s-3.582-7-8-7Zm-3.5 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Zm3.5 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2Zm3.5 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"
          clipRule="evenodd"
        />
      </svg>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-label="Antwort wird erstellt">
      <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-zinc-200 bg-white px-4 py-3.5 shadow-sm dark:border-zinc-700/80 dark:bg-zinc-900">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-zinc-400 dark:bg-zinc-500"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("de");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [sessionFeedbackDone, setSessionFeedbackDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const answerCount = messages.filter((m) => m.role === "assistant").length;
  const showSessionFeedback = answerCount >= 3 && !isLoading && !sessionFeedbackDone;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function handleSend(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      const history = messages.map(({ role, content }) => ({ role, content }));
      const response = await sendChatMessage(trimmed, language, history);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          topic: response.topic,
        },
      ]);
    } catch {
      setError("Die Anfrage ist fehlgeschlagen. Bitte versuchen Sie es erneut.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-zinc-100 dark:bg-zinc-950">
      <header className="sticky top-0 z-10 border-b border-zinc-200 bg-white/90 px-4 py-3 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <BrandMark />
            <div>
              <h1 className="text-base font-bold leading-tight text-zinc-900 dark:text-zinc-50">
                BürgerChat
              </h1>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Behördendeutsch in einfache Sprache — mit Quellenangabe
              </p>
            </div>
          </div>
          <LanguageSelect value={language} onChange={setLanguage} />
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-1 flex-col justify-center gap-8 pb-16">
            <div className="text-center">
              <h2 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                Womit können wir helfen?
              </h2>
              <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
                Einfache Antworten mit offiziellen Quellen zu: Bürgergeld,
                Kindergeld &amp; Familienleistungen, Rente, Wohngeld, Steuer-ID,
                Aufenthalt &amp; Einbürgerung. Wir finden auch Ihre zuständige
                Behörde — nennen Sie dafür Ihre Postleitzahl.
              </p>
            </div>
            <StarterPrompts onSelect={handleSend} />
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-4" role="log" aria-live="polite">
            {messages.map((message, i) => (
              <ChatMessage key={message.id ?? i} message={message} sessionId={sessionId} />
            ))}
            {isLoading && <TypingIndicator />}
            {showSessionFeedback && (
              <SessionFeedback
                sessionId={sessionId}
                onDismiss={() => setSessionFeedbackDone(true)}
              />
            )}
            {error && (
              <div className="flex justify-start">
                <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
                  {error}
                </p>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      <div className="sticky bottom-0 border-t border-zinc-200 bg-white px-4 pb-4 pt-3 dark:border-zinc-800 dark:bg-zinc-950">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="mx-auto flex max-w-3xl items-center gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Stellen Sie Ihre Frage …"
            dir="auto"
            className="h-11 flex-1 rounded-full border border-zinc-300 bg-white px-4 text-[15px] text-zinc-900 shadow-sm transition placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            aria-label="Senden"
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-blue-600 text-white shadow-sm transition hover:bg-blue-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.155.75.75 0 0 0 0-1.114A28.897 28.897 0 0 0 3.105 2.288Z" />
            </svg>
          </button>
        </form>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-zinc-400 dark:text-zinc-500">
          BürgerChat erklärt amtliche Informationen, ersetzt aber keine Rechtsberatung.
        </p>
      </div>
    </div>
  );
}
