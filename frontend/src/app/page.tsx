"use client";

import { useEffect, useRef, useState } from "react";
import { ChatMessage, type Message } from "@/components/ChatMessage";
import { StarterPrompts } from "@/components/StarterPrompts";
import { LanguageSelect } from "@/components/LanguageSelect";
import { sendChatMessage } from "@/lib/api";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [language, setLanguage] = useState("de");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

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
    <div className="flex min-h-screen flex-col bg-zinc-50 dark:bg-black">
      <header className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-950">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">BürgerChat</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Behördendeutsch in einfache Sprache — mit Quellenangabe
            </p>
          </div>
          <LanguageSelect value={language} onChange={setLanguage} />
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-6">
        {messages.length === 0 && (
          <div className="flex flex-1 flex-col justify-center gap-4">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              Womit kann ich helfen?
            </p>
            <StarterPrompts onSelect={handleSend} />
          </div>
        )}

        {messages.length > 0 && (
          <div className="flex flex-1 flex-col gap-4">
            {messages.map((message, i) => (
              <ChatMessage key={i} message={message} />
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-gray-100 px-4 py-3 text-sm text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                  Einen Moment …
                </div>
              </div>
            )}
            {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="border-t border-gray-200 bg-white px-4 py-3 dark:border-gray-800 dark:bg-gray-950"
      >
        <div className="mx-auto flex max-w-3xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Stellen Sie Ihre Frage …"
            className="flex-1 rounded-full border border-gray-300 bg-white px-4 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="rounded-full bg-blue-600 px-5 py-2 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Senden
          </button>
        </div>
      </form>
    </div>
  );
}
