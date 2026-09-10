import { describe, expect, it, vi } from "vitest";
import { proxyToBackend } from "@/lib/proxy";

const BASE = "http://backend.internal:8080";

function upstream(status = 200, body = '{"ok":true}', headers: Record<string, string> = {}) {
  return vi.fn().mockResolvedValue(
    new Response(body, { status, headers: { "content-type": "application/json", ...headers } }),
  );
}

function post(body: string, headers: Record<string, string> = {}) {
  return new Request("https://frontend.example/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body,
  });
}

describe("proxyToBackend", () => {
  it("forwards a POST body to the backend path", async () => {
    const fetchMock = upstream(200, '{"answer":"a"}');
    const res = await proxyToBackend(post('{"message":"Frage"}'), "chat", BASE, fetchMock);

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ answer: "a" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/chat`);
    expect(init.method).toBe("POST");
    expect(init.body).toBe('{"message":"Frage"}');
    expect(init.headers["content-type"]).toBe("application/json");
  });

  it("passes the client's X-Forwarded-For on, so rate limits stay per user", async () => {
    const fetchMock = upstream();
    await proxyToBackend(
      post("{}", { "x-forwarded-for": "80.153.188.26, 10.0.0.1" }),
      "chat",
      BASE,
      fetchMock,
    );
    expect(fetchMock.mock.calls[0][1].headers["x-forwarded-for"]).toBe("80.153.188.26, 10.0.0.1");
  });

  it("does not forward cookies or other browser headers", async () => {
    const fetchMock = upstream();
    await proxyToBackend(post("{}", { cookie: "a=b", origin: "https://evil.example" }), "chat", BASE, fetchMock);
    expect(Object.keys(fetchMock.mock.calls[0][1].headers).sort()).toEqual(["content-type"]);
  });

  it("passes Cache-Control on, so the smoke test can bypass the answer cache", async () => {
    const fetchMock = upstream();
    await proxyToBackend(post("{}", { "cache-control": "no-cache" }), "chat", BASE, fetchMock);
    expect(fetchMock.mock.calls[0][1].headers["cache-control"]).toBe("no-cache");
  });

  it("passes backend error statuses through unchanged", async () => {
    const res = await proxyToBackend(
      post("{}"),
      "chat",
      BASE,
      upstream(429, '{"error":"rate limited"}', { "retry-after": "60" }),
    );
    expect(res.status).toBe(429);
    expect(res.headers.get("retry-after")).toBe("60");
  });

  it("proxies GET /health", async () => {
    const fetchMock = upstream(200, '{"status":"ok"}');
    const res = await proxyToBackend(
      new Request("https://frontend.example/api/health"),
      "health",
      `${BASE}/`,
      fetchMock,
    );
    expect(res.status).toBe(200);
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE}/health`);
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined();
  });

  it("refuses paths outside the public API", async () => {
    const fetchMock = upstream();
    for (const path of ["docs", "openapi.json", "", "chat/../docs"]) {
      const res = await proxyToBackend(post("{}"), path, BASE, fetchMock);
      expect(res.status, path).toBe(404);
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses the wrong method for a known path", async () => {
    const fetchMock = upstream();
    const res = await proxyToBackend(
      new Request("https://frontend.example/api/chat"),
      "chat",
      BASE,
      fetchMock,
    );
    expect(res.status).toBe(405);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("answers 502 when the backend is unreachable", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await proxyToBackend(post("{}"), "chat", BASE, fetchMock);
    expect(res.status).toBe(502);
  });

  it("answers 504 when the backend times out", async () => {
    const timeout = new DOMException("The operation was aborted due to timeout", "TimeoutError");
    const fetchMock = vi.fn().mockRejectedValue(timeout);
    vi.spyOn(console, "error").mockImplementation(() => {});
    const res = await proxyToBackend(post("{}"), "chat", BASE, fetchMock);
    expect(res.status).toBe(504);
  });
});
