import { LANGUAGES } from "@/lib/constants";

export function LanguageSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (language: string) => void;
}) {
  return (
    <label className="flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white py-1.5 pe-2 ps-3 shadow-sm transition focus-within:border-blue-400 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:border-zinc-600">
      <svg
        className="h-4 w-4 shrink-0 text-zinc-400"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M7 2.75A.75.75 0 0 1 7.75 2h4.5a.75.75 0 0 1 0 1.5h-1.5v1h4.5a.75.75 0 0 1 0 1.5h-1.033c-.443 2.1-1.334 3.94-2.514 5.428.767.68 1.633 1.245 2.57 1.67a.75.75 0 1 1-.62 1.366 12.3 12.3 0 0 1-2.985-1.963c-.885.79-1.865 1.46-2.913 1.985a.75.75 0 0 1-.67-1.342 10.8 10.8 0 0 0 2.5-1.72C8.35 10.19 7.67 8.9 7.24 7.5H6.75a.75.75 0 0 1 0-1.5h3.5v-1h-2.5A.75.75 0 0 1 7 2.75Zm1.83 4.75c.36 1.04.89 2.01 1.57 2.86.68-.85 1.21-1.82 1.57-2.86H8.83Zm5.42 4.75a.75.75 0 0 1 .69.457l3 7a.75.75 0 1 1-1.38.586L15.939 19h-3.378l-.621 1.543a.75.75 0 1 1-1.38-.586l3-7a.75.75 0 0 1 .69-.457Zm-1.085 5.25h2.17l-1.085-2.532L13.165 17.5Z"
          clipRule="evenodd"
        />
      </svg>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-transparent text-sm font-medium text-zinc-700 focus:outline-none dark:text-zinc-200"
        aria-label="Antwortsprache"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.label}
          </option>
        ))}
      </select>
    </label>
  );
}
