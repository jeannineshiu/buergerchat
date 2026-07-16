// Mirrors backend/rag.py LANGUAGE_NAMES.
export const LANGUAGES = [
  { code: "de", label: "Deutsch" },
  { code: "en", label: "English" },
  { code: "tr", label: "Türkçe" },
  { code: "ar", label: "العربية" },
  { code: "uk", label: "Українська" },
  { code: "ru", label: "Русский" },
  { code: "pl", label: "Polski" },
] as const;

export interface StarterPrompt {
  topic: string;
  label: string;
  prompt: string;
}

// The three MVP themes from the product positioning: Bürgergeld/Grundsicherung,
// Kindergeld, and finding the right Behörde.
export const STARTER_PROMPTS: StarterPrompt[] = [
  {
    topic: "buergergeld",
    label: "Bürgergeld / Grundsicherung",
    prompt: "Habe ich Anspruch auf Bürgergeld (Grundsicherung) und wie beantrage ich es?",
  },
  {
    topic: "kindergeld",
    label: "Kindergeld",
    prompt: "Wer bekommt Kindergeld und wie beantrage ich es?",
  },
  {
    topic: "behoerde",
    label: "Die richtige Behörde finden",
    prompt: "Welches Amt ist für mein Anliegen zuständig?",
  },
];
