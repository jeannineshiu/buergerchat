const LANGUAGE_KEY = "buergerchat-language";

// Browsers can refuse site storage outright: Firefox with cookies blocked
// (globally or for this site) throws SecurityError on any localStorage
// access, and with dom.storage.enabled=false localStorage is null. Unguarded,
// that throw inside a useEffect took down the whole app ("This page couldn't
// load") — remembering the language is a convenience, never worth a crash.

export function loadLanguage(): string | null {
  try {
    return window.localStorage.getItem(LANGUAGE_KEY);
  } catch {
    return null;
  }
}

export function saveLanguage(code: string): void {
  try {
    window.localStorage.setItem(LANGUAGE_KEY, code);
  } catch {
    // Storage unavailable: the choice just won't survive a reload.
  }
}
