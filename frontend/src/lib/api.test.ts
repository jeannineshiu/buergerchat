import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ChatError,
  sendChatMessage,
  sendMessageFeedback,
  sendSessionFeedback,
} from "@/lib/api";

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

  it("calls the same-origin proxy, never a cross-site backend URL", async () => {
    const fetchMock = mockFetch(200, { answer: "a", sources: [], topic: "t" });
    await sendChatMessage("Frage", "de");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/chat");
  });

  it("throws on non-ok responses", async () => {
    mockFetch(503);
    await expect(sendChatMessage("Frage", "de")).rejects.toThrow("503");
  });

  it.each([
    [429, "rateLimit"],
    [500, "server"],
    [502, "server"],
    [503, "server"],
    [504, "server"],
    [422, "other"],
  ] as const)("classifies HTTP %i as %s", async (status, kind) => {
    mockFetch(status);
    await expect(sendChatMessage("Frage", "de")).rejects.toMatchObject({ kind, status });
  });

  it("classifies a fetch that never got a response as a network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("NetworkError")));
    const err = await sendChatMessage("Frage", "de").catch((e) => e);
    expect(err).toBeInstanceOf(ChatError);
    expect(err.kind).toBe("network");
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
