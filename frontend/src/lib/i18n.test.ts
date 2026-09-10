import { describe, expect, it } from "vitest";
import { LANGUAGES } from "@/lib/constants";
import { ChatError } from "@/lib/api";
import { errorText, getStrings, RTL_LANGUAGES, UI_STRINGS } from "@/lib/i18n";

// TypeScript guarantees each locale object has every field; what it cannot
// check is the cross-file invariant between the language selector and the
// string table — that's what these tests pin down.

describe("i18n string table", () => {
  it("covers every language in the selector", () => {
    for (const lang of LANGUAGES) {
      expect(UI_STRINGS[lang.code], `missing strings for ${lang.code}`).toBeDefined();
    }
  });

  it("has no orphan locales missing from the selector", () => {
    const codes = new Set<string>(LANGUAGES.map((l) => l.code));
    for (const key of Object.keys(UI_STRINGS)) {
      expect(codes.has(key), `locale ${key} not selectable`).toBe(true);
    }
  });

  it("every locale ships the same starter prompts in MVP-priority order", () => {
    // No "find the authority" starter — that's never a first question;
    // the welcome subtitle advertises the PLZ lookup instead.
    for (const [code, strings] of Object.entries(UI_STRINGS)) {
      expect(strings.starters.map((s) => s.topic), code).toEqual([
        "buergergeld",
        "kindergeld",
        "familie-und-kinder",
        "rente",
        "wohngeld",
        "steuern",
        "aufenthalt",
      ]);
    }
  });

  it("keeps official German terms in German in every locale", () => {
    for (const [code, strings] of Object.entries(UI_STRINGS)) {
      for (const term of ["Bürgergeld", "Kindergeld", "Rente", "Wohngeld", "Steuer-ID"]) {
        expect(strings.welcomeSubtitle, `${code} subtitle`).toContain(term);
      }
      expect(strings.starters[1].prompt, code).toContain("Kindergeld");
      // Non-German locales must gloss the German term: "Kindergeld（兒童金）".
      if (code !== "de") {
        for (const [i, starter] of strings.starters.entries()) {
          for (const term of ["Bürgergeld", "Kindergeld", "Elterngeld", "Rente", "Wohngeld", "Steuer-ID"]) {
            if (starter.label.includes(term)) {
              expect(starter.label, `${code} starters[${i}]`).toMatch(/[(（]/);
            }
          }
        }
      }
    }
  });

  it("no locale has empty strings", () => {
    for (const [code, strings] of Object.entries(UI_STRINGS)) {
      for (const [key, value] of Object.entries(strings)) {
        if (typeof value === "string") {
          expect(value.trim().length, `${code}.${key}`).toBeGreaterThan(0);
        }
      }
    }
  });

  it("RTL set only contains selectable languages", () => {
    const codes = new Set<string>(LANGUAGES.map((l) => l.code));
    for (const code of RTL_LANGUAGES) {
      expect(codes.has(code), code).toBe(true);
    }
    expect(RTL_LANGUAGES.has("ar")).toBe(true);
    expect(RTL_LANGUAGES.has("fa")).toBe(true);
  });

  it("falls back to German for unknown codes", () => {
    expect(getStrings("xx")).toBe(UI_STRINGS.de);
    expect(getStrings("zh-Hant")).toBe(UI_STRINGS["zh-Hant"]);
  });
});

describe("errorText", () => {
  const de = UI_STRINGS.de;

  it("picks the message matching the failure kind", () => {
    expect(errorText(de, new ChatError("network"))).toBe(de.errorNetwork);
    expect(errorText(de, new ChatError("rateLimit", 429))).toBe(de.errorRateLimit);
    expect(errorText(de, new ChatError("server", 502))).toBe(de.errorServer);
    expect(errorText(de, new ChatError("dailyLimit", 503))).toBe(de.errorDailyLimit);
    expect(errorText(de, new ChatError("other", 422))).toBe(de.errorMessage);
  });

  it("falls back to the generic message for anything else", () => {
    expect(errorText(de, new SyntaxError("bad JSON"))).toBe(de.errorMessage);
  });

  it("gives each failure kind its own text in every locale", () => {
    for (const [code, s] of Object.entries(UI_STRINGS)) {
      const texts = [
        s.errorMessage,
        s.errorNetwork,
        s.errorRateLimit,
        s.errorServer,
        s.errorDailyLimit,
      ];
      expect(new Set(texts).size, code).toBe(5);
    }
  });
});
