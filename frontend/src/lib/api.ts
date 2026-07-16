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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendChatMessage(
  message: string,
  language: string,
  history: HistoryMessage[] = [],
): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language, history }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed (${response.status})`);
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
