export type RepoStatus =
  | "pending"
  | "cloning"
  | "indexing"
  | "cancelling"
  | "ready"
  | "failed";

export interface Repository {
  id: number;
  name: string;
  url: string;
  branch: string;
  status: RepoStatus;
  error: string;
  chunk_count: number;
  file_count: number;
  created_at: string;
  updated_at: string;
}

export interface Source {
  file_path: string;
  language: string;
  start_line: number;
  end_line: number;
  content: string;
  distance: number;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

const BASE = "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function listRepositories(): Promise<Repository[]> {
  return handle(await fetch(`${BASE}/repositories/`));
}

export async function createRepository(
  url: string,
  branch: string,
): Promise<Repository> {
  return handle(
    await fetch(`${BASE}/repositories/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, branch }),
    }),
  );
}

export async function deleteRepository(id: number): Promise<void> {
  const res = await fetch(`${BASE}/repositories/${id}/`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete repository (${res.status})`);
}

export async function cancelIndexing(id: number): Promise<void> {
  const res = await fetch(`${BASE}/repositories/${id}/cancel/`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to cancel indexing (${res.status})`);
}

export type AskPhase = "retrieving" | "thinking" | "answering";

export interface StreamHandlers {
  onStatus?: (phase: AskPhase, message: string) => void;
  onSources?: (sources: Source[], message: string) => void;
  onThinking?: (textDelta: string) => void;
  onDelta?: (textDelta: string) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
}

interface StreamEvent {
  type: "status" | "sources" | "thinking" | "delta" | "error" | "done";
  phase?: AskPhase;
  message?: string;
  sources?: Source[];
  text?: string;
}

/** POST a question and consume the SSE stream, dispatching to handlers. */
export async function askStream(
  repositoryId: number,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/ask/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository_id: repositoryId, question }),
    signal,
  });

  // Errors (validation, budget, throttle) come back as a normal JSON response.
  if (!res.ok || !res.body) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep default */
    }
    handlers.onError?.(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (event: StreamEvent) => {
    switch (event.type) {
      case "status":
        handlers.onStatus?.(event.phase!, event.message ?? "");
        break;
      case "sources":
        handlers.onSources?.(event.sources ?? [], event.message ?? "");
        break;
      case "thinking":
        handlers.onThinking?.(event.text ?? "");
        break;
      case "delta":
        handlers.onDelta?.(event.text ?? "");
        break;
      case "error":
        handlers.onError?.(event.message ?? "Something went wrong.");
        break;
      case "done":
        handlers.onDone?.();
        break;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) >= 0) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data:"));
      if (!dataLine) continue;
      try {
        dispatch(JSON.parse(dataLine.slice(5).trim()) as StreamEvent);
      } catch {
        /* ignore malformed frame */
      }
    }
  }
}
