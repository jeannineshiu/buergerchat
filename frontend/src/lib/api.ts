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
