export interface Source {
  title: string;
  url: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  topic: string;
}

export interface HistoryMessage {
  role: "user" | "assistant";
  content: string;
}

// Same-origin: app/api/[...path]/route.ts forwards to the backend.
const API_URL = "/api";

// Why a request failed, so the UI can say something more useful than
// "it failed". Picked from the status code; "network" means no response at
// all (offline, or the connection dropped).
export type ChatErrorKind = "network" | "rateLimit" | "server" | "other";

export class ChatError extends Error {
  constructor(
    readonly kind: ChatErrorKind,
    readonly status?: number,
  ) {
    super(`Chat request failed (${status ?? kind})`);
    this.name = "ChatError";
  }
}

function kindForStatus(status: number): ChatErrorKind {
  if (status === 429) return "rateLimit";
  if (status >= 500) return "server"; // incl. the proxy's 502/504 and 503 while the index is missing
  return "other";
}

export async function sendChatMessage(
  message: string,
  language: string,
  history: HistoryMessage[] = [],
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, language, history }),
    });
  } catch {
    throw new ChatError("network");
  }

  if (!response.ok) {
    throw new ChatError(kindForStatus(response.status), response.status);
  }

  return response.json();
}

export interface MessageFeedback {
  message_id: string;
  session_id: string;
  rating: "up" | "down";
  comment?: string;
  topic?: string;
}

export interface SessionFeedback {
  session_id: string;
  rating: number; // 1-5
  comment?: string;
}

async function postFeedback(path: string, body: MessageFeedback | SessionFeedback) {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Feedback request failed (${response.status})`);
  }
}

export const sendMessageFeedback = (body: MessageFeedback) =>
  postFeedback("/feedback/message", body);

export const sendSessionFeedback = (body: SessionFeedback) =>
  postFeedback("/feedback/session", body);
