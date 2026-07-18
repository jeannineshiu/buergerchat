import { describe, expect, it } from "vitest";
import { FOLLOW_UPS, getFollowUps } from "@/lib/followups";
import { UI_STRINGS } from "@/lib/i18n";

// The third question of every topic must reach the backend's
// authority-intent keywords (backend/router.py AUTHORITY_KEYWORDS) so a
// click starts the Behörden-Finder flow in any language.
const AUTHORITY_TRIGGERS = [
  "jobcenter",
  "familienkasse",
  "elterngeldstelle",
  "agentur für arbeit",
  "rentenversicherung",
  "wohngeldstelle",
  "finanzamt",
  "ausländerbehörde",
];

describe("follow-up suggestions", () => {
  it("covers every locale in the string table", () => {
    for (const code of Object.keys(UI_STRINGS)) {
      expect(FOLLOW_UPS[code], `missing follow-ups for ${code}`).toBeDefined();
    }
  });

  it("every locale covers the same topics with three questions each", () => {
    const topics = Object.keys(FOLLOW_UPS.de).sort();
    for (const [code, map] of Object.entries(FOLLOW_UPS)) {
      expect(Object.keys(map).sort(), code).toEqual(topics);
      for (const [topic, questions] of Object.entries(map)) {
        expect(questions.length, `${code}.${topic}`).toBe(3);
        for (const q of questions) {
          expect(q.trim().length, `${code}.${topic}`).toBeGreaterThan(0);
        }
      }
    }
  });

  it("the authority question embeds a German intent keyword in every locale", () => {
    for (const [code, map] of Object.entries(FOLLOW_UPS)) {
      for (const [topic, questions] of Object.entries(map)) {
        const authorityQuestion = questions[2].toLowerCase();
        expect(
          AUTHORITY_TRIGGERS.some((t) => authorityQuestion.includes(t)),
          `${code}.${topic}: "${questions[2]}"`,
        ).toBe(true);
      }
    }
  });

  it("glosses German terms outside the German locale", () => {
    for (const [code, map] of Object.entries(FOLLOW_UPS)) {
      if (code === "de") continue;
      for (const [topic, questions] of Object.entries(map)) {
        for (const q of questions) {
          if (/(?:geld|stelle|kasse|amt|behörde|Steuer-ID|Rente|Einbürgerung)/i.test(q)) {
            expect(q, `${code}.${topic}`).toMatch(/[(（]/);
          }
        }
      }
    }
  });

  it("returns empty for unknown topics and falls back to German for unknown locales", () => {
    expect(getFollowUps("zh-Hant", "allgemein")).toEqual([]);
    expect(getFollowUps("xx", "kindergeld")).toEqual(FOLLOW_UPS.de.kindergeld);
  });
});
