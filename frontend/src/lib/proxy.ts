// Same-origin proxy from the browser to the FastAPI backend.
//
// The browser used to call the backend's public domain directly. Railway
// app domains sit under a public suffix (up.railway.app), so that was a
// cross-site request with a CORS preflight, and privacy extensions or
// company web filters could drop it before it reached Railway. Users only
// saw "the request failed". With this proxy the browser only ever talks to
// the page's own origin.

// Only the backend's public API. Anything else (/docs, /openapi.json) stays
// unreachable through the frontend.
const ALLOWED: Record<string, "GET" | "POST"> = {
  chat: "POST",
  "feedback/message": "POST",
  "feedback/session": "POST",
  health: "GET",
};

// /chat runs retrieval, an optional LLM rerank and the answer completion:
// typically 12–25 s. This only has to catch a hung upstream.
export const UPSTREAM_TIMEOUT_MS = 120_000;

export function backendUrl(): string {
  // Read at request time, not build time, so one image works in every
  // environment. In production this is the Railway private-network address.
  return process.env.BACKEND_URL ?? "http://localhost:8000";
}

function jsonError(status: number, error: string): Response {
  return Response.json({ error }, { status });
}

export async function proxyToBackend(
  request: Request,
  path: string,
  base: string = backendUrl(),
  fetchImpl: typeof fetch = fetch,
): Promise<Response> {
  const method = ALLOWED[path];
  if (!method) return jsonError(404, "Not found");
  if (request.method !== method) return jsonError(405, "Method not allowed");

  const headers: Record<string, string> = {};
  const contentType = request.headers.get("content-type");
  if (contentType) headers["content-type"] = contentType;
  // The backend rate-limits per client IP, taken from the first
  // X-Forwarded-For hop. Without passing it on, every user would share the
  // frontend server's IP and a single 10/min bucket.
  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers["x-forwarded-for"] = forwardedFor;

  let upstream: Response;
  try {
    upstream = await fetchImpl(`${base.replace(/\/+$/, "")}/${path}`, {
      method,
      headers,
      body: method === "POST" ? await request.text() : undefined,
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "TimeoutError";
    console.error(`[proxy] /${path} upstream ${timedOut ? "timed out" : "unreachable"}:`, err);
    return timedOut
      ? jsonError(504, "Backend timed out")
      : jsonError(502, "Backend unreachable");
  }

  const responseHeaders: Record<string, string> = {};
  for (const name of ["content-type", "retry-after"]) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders[name] = value;
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}
