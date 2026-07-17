import { describe, expect, it } from "vitest";
import { LANGUAGES } from "@/lib/constants";
import { getStrings, RTL_LANGUAGES, UI_STRINGS } from "@/lib/i18n";

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

  it("every locale ships the three starter prompts", () => {
    for (const [code, strings] of Object.entries(UI_STRINGS)) {
      expect(strings.starters.map((s) => s.topic), code).toEqual([
        "buergergeld",
        "kindergeld",
        "behoerde",
      ]);
    }
  });

  it("keeps official German terms in German in every locale", () => {
    for (const [code, strings] of Object.entries(UI_STRINGS)) {
      expect(strings.welcomeSubtitle, code).toContain("Bürgergeld");
      expect(strings.starters[1].prompt, code).toContain("Kindergeld");
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
