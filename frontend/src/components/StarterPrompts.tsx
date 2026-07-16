import { STARTER_PROMPTS } from "@/lib/constants";

export function StarterPrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {STARTER_PROMPTS.map((starter) => (
        <button
          key={starter.topic}
          onClick={() => onSelect(starter.prompt)}
          className="rounded-xl border border-gray-200 bg-white p-4 text-left transition hover:border-blue-400 hover:shadow-sm dark:border-gray-700 dark:bg-gray-900"
        >
          <p className="font-medium text-gray-900 dark:text-gray-100">{starter.label}</p>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{starter.prompt}</p>
        </button>
      ))}
    </div>
  );
}
