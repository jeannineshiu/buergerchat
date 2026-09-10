import { afterEach, describe, expect, it, vi } from "vitest";
import { loadLanguage, saveLanguage } from "@/lib/storage";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubLocalStorage(localStorage: unknown) {
  vi.stubGlobal("window", { localStorage });
}

describe("language storage", () => {
  it("round-trips the language through localStorage", () => {
    const store = new Map<string, string>();
    stubLocalStorage({
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => store.set(k, v),
    });
    expect(loadLanguage()).toBeNull();
    saveLanguage("zh-Hant");
    expect(loadLanguage()).toBe("zh-Hant");
  });

  it("survives Firefox's SecurityError when cookies are blocked", () => {
    const deny = () => {
      throw new DOMException("The operation is insecure.", "SecurityError");
    };
    stubLocalStorage({ getItem: deny, setItem: deny });
    expect(loadLanguage()).toBeNull();
    expect(() => saveLanguage("de")).not.toThrow();
  });

  it("survives localStorage being null (dom.storage.enabled=false)", () => {
    stubLocalStorage(null);
    expect(loadLanguage()).toBeNull();
    expect(() => saveLanguage("de")).not.toThrow();
  });
});
