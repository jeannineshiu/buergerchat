import { afterEach, describe, expect, it, vi } from "vitest";
import { sendChatMessage, sendMessageFeedback, sendSessionFeedback } from "@/lib/api";

function mockFetch(status = 200, body: unknown = {}) {
  const fn = vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("sendChatMessage", () => {
  it("posts message, language and history to /chat", async () => {
    const fetchMock = mockFetch(200, { answer: "a", sources: [], topic: "allgemein" });
    const history = [{ role: "user" as const, content: "hi" }];
    const result = await sendChatMessage("Frage", "zh-Hant", history);

    expect(result.answer).toBe("a");
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/chat$/);
    expect(JSON.parse(init.body)).toEqual({
      message: "Frage",
      language: "zh-Hant",
      history,
    });
  });

  it("defaults to empty history", async () => {
    const fetchMock = mockFetch(200, { answer: "a", sources: [], topic: "t" });
    await sendChatMessage("Frage", "de");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).history).toEqual([]);
  });

  it("throws on non-ok responses", async () => {
    mockFetch(503);
    await expect(sendChatMessage("Frage", "de")).rejects.toThrow("503");
  });
});

describe("feedback", () => {
  it("posts message feedback to /feedback/message", async () => {
    const fetchMock = mockFetch(201);
    await sendMessageFeedback({
      message_id: "m1",
      session_id: "s1",
      rating: "down",
      comment: "zu lang",
      topic: "kindergeld",
    });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/feedback\/message$/);
    expect(JSON.parse(init.body).rating).toBe("down");
  });

  it("posts session feedback to /feedback/session", async () => {
    const fetchMock = mockFetch(201);
    await sendSessionFeedback({ session_id: "s1", rating: 4 });
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/feedback\/session$/);
  });

  it("throws on failure so callers can decide to swallow", async () => {
    mockFetch(429);
    await expect(sendSessionFeedback({ session_id: "s", rating: 1 })).rejects.toThrow("429");
  });
});
