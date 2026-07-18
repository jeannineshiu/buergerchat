// Follow-up suggestion chips under the newest answer — smaller siblings of
// the StarterPrompts pills. Left-aligned with the assistant bubble so they
// read as "you could ask next", not as another answer.
export function FollowUpChips({
  questions,
  onSelect,
}: {
  questions: string[];
  onSelect: (question: string) => void;
}) {
  if (questions.length === 0) return null;
  return (
    <div className="flex flex-wrap justify-start gap-2">
      {questions.map((question) => (
        <button
          key={question}
          onClick={() => onSelect(question)}
          className="rounded-full border border-blue-200 bg-blue-50/60 px-3 py-1.5 text-start text-[13px] font-medium leading-snug text-blue-700 shadow-sm transition hover:border-blue-300 hover:bg-blue-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-blue-500/30 dark:bg-blue-500/10 dark:text-blue-300 dark:hover:border-blue-500/60 dark:hover:bg-blue-500/20"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
