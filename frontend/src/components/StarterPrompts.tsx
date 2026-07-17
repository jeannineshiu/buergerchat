import type { StarterPrompt } from "@/lib/i18n";

// Language-neutral icons: the audience may not read German fluently yet,
// so each theme gets a visual anchor alongside the text.
const TOPIC_ICONS: Record<string, string> = {
  buergergeld: "💶",
  kindergeld: "👨‍👩‍👧",
  behoerde: "🏛️",
};

export function StarterPrompts({
  starters,
  onSelect,
}: {
  starters: StarterPrompt[];
  onSelect: (prompt: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {starters.map((starter) => (
        <button
          key={starter.topic}
          onClick={() => onSelect(starter.prompt)}
          className="group rounded-2xl border border-zinc-200 bg-white p-4 text-start shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-blue-500/60"
        >
          <span className="text-xl" aria-hidden="true">
            {TOPIC_ICONS[starter.topic] ?? "💬"}
          </span>
          <p className="mt-2 font-semibold text-zinc-900 group-hover:text-blue-700 dark:text-zinc-100 dark:group-hover:text-blue-300">
            {starter.label}
          </p>
          <p className="mt-1 text-sm leading-snug text-zinc-500 dark:text-zinc-400">
            {starter.prompt}
          </p>
        </button>
      ))}
    </div>
  );
}
