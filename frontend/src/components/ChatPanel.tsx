import { useEffect, useRef, useState } from "react";
import {
  askStream,
  type AskPhase,
  type Repository,
  type Source,
} from "../api";

interface Turn {
  question: string;
  thinking: string;
  answer: string;
  sources: Source[];
  sourcesMessage: string;
  error?: string;
}

interface LiveTurn extends Turn {
  phase: AskPhase | null;
  statusMessage: string;
}

const SUGGESTIONS = [
  "How does authentication work in this project?",
  "Where is the entry point and how is the app wired together?",
  "Explain the data model.",
];

const PHASE_LABEL: Record<AskPhase, string> = {
  retrieving: "Diving into the code",
  thinking: "Spark is thinking",
  answering: "Writing answer",
};

const HOWTO_STEPS = [
  {
    title: "Add a repo",
    body: "Paste a GitHub URL in the sidebar and click Index repository.",
  },
  {
    title: "Spark dives in",
    body: "It clones and indexes the code into a searchable vector store — usually a minute or two.",
  },
  {
    title: "Ask anything",
    body: "Once it's ready, ask about the codebase in plain English.",
  },
  {
    title: "Get grounded answers",
    body: "Spark replies with citations to the exact files and lines.",
  },
];

function HowToGuide() {
  return (
    <div className="mx-auto mt-7 max-w-md text-left">
      <p className="mb-3 text-center text-[11px] uppercase tracking-wider text-zinc-600">
        How it works
      </p>
      <ol className="space-y-3">
        {HOWTO_STEPS.map((step, i) => (
          <li key={i} className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-xs font-medium text-emerald-300">
              {i + 1}
            </span>
            <div>
              <p className="text-sm text-zinc-200">{step.title}</p>
              <p className="text-xs leading-relaxed text-zinc-500">{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

interface Props {
  repository: Repository | null;
}

export default function ChatPanel({ repository }: Props) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [live, setLive] = useState<LiveTurn | null>(null);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const liveRef = useRef<LiveTurn | null>(null);

  const loading = live !== null;

  useEffect(() => {
    setTurns([]);
    setLive(null);
    liveRef.current = null;
    abortRef.current?.abort();
  }, [repository?.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns, live]);

  const send = async (question: string) => {
    if (!repository || !question.trim() || loading) return;
    setInput("");

    const controller = new AbortController();
    abortRef.current = controller;

    const initial: LiveTurn = {
      question,
      phase: "retrieving",
      statusMessage: "Searching the codebase…",
      thinking: "",
      answer: "",
      sources: [],
      sourcesMessage: "",
    };
    liveRef.current = initial;
    setLive(initial);

    // Single source of truth: mutate via the ref, then mirror into state.
    const update = (fn: (t: LiveTurn) => LiveTurn) => {
      if (!liveRef.current) return;
      liveRef.current = fn(liveRef.current);
      setLive(liveRef.current);
    };

    const finalize = () => {
      const current = liveRef.current;
      if (current) {
        const { phase: _p, statusMessage: _s, ...turn } = current;
        setTurns((prev) => [...prev, turn]);
      }
      liveRef.current = null;
      setLive(null);
    };

    await askStream(
      repository.id,
      question,
      {
        onStatus: (phase, message) =>
          update((t) => ({ ...t, phase, statusMessage: message })),
        onSources: (sources, message) =>
          update((t) => ({ ...t, sources, sourcesMessage: message })),
        onThinking: (delta) =>
          update((t) => ({ ...t, thinking: t.thinking + delta })),
        onDelta: (delta) => update((t) => ({ ...t, answer: t.answer + delta })),
        onError: (message) => update((t) => ({ ...t, error: message })),
        onDone: finalize,
      },
      controller.signal,
    );

    // If the stream ended without an explicit done (e.g. error), finalize.
    if (liveRef.current) finalize();
  };

  if (!repository) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="text-lg text-zinc-300">
            Welcome to{" "}
            <span className="font-medium text-emerald-400">CodebaseQA</span> 🦈
          </p>
          <p className="mt-1 text-sm text-zinc-500">
            Add a repository in the sidebar to get started.
          </p>
          <HowToGuide />
        </div>
      </div>
    );
  }

  const ready = repository.status === "ready";

  return (
    <div className="flex flex-1 flex-col bg-zinc-900">
      <header className="border-b border-zinc-800 px-6 py-4">
        <h2 className="font-mono text-sm text-zinc-300">{repository.name}</h2>
        <p className="text-xs text-zinc-600">{repository.url}</p>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto px-6 py-6">
        {turns.length === 0 && !live && (
          <div className="mx-auto max-w-2xl pt-10 text-center">
            <p className="text-zinc-400">
              Hi, I'm{" "}
              <span className="font-medium text-emerald-400">Spark</span> 🦈 —
              ask me anything about{" "}
              <span className="font-mono text-emerald-400">
                {repository.name}
              </span>
            </p>
            <div className="mt-5 flex flex-col items-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  disabled={!ready}
                  onClick={() => send(s)}
                  className="rounded-full border border-zinc-700 px-4 py-1.5 text-sm text-zinc-300 transition hover:border-emerald-500 hover:text-emerald-300 disabled:opacity-40"
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="mt-8 border-t border-zinc-800 pt-2">
              <HowToGuide />
            </div>
          </div>
        )}

        {turns.map((turn, i) => (
          <TurnView key={i} turn={turn} />
        ))}

        {live && <LiveTurnView turn={live} />}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="border-t border-zinc-800 p-4"
      >
        <div className="mx-auto flex max-w-2xl items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!ready || loading}
            placeholder={
              ready
                ? "Ask Spark about this codebase…"
                : `Repository is ${repository.status}…`
            }
            className="flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-4 py-2.5 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-emerald-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!ready || loading || !input.trim()}
            className="rounded-lg bg-emerald-500 px-4 py-2.5 text-sm font-medium text-zinc-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Ask
          </button>
        </div>
      </form>
    </div>
  );
}

function Bubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-2xl rounded-bl-sm bg-zinc-800/60 px-4 py-3">
      {children}
    </div>
  );
}

function Question({ text }: { text: string }) {
  return (
    <div className="ml-auto w-fit max-w-[85%] rounded-2xl rounded-br-sm bg-emerald-500/10 px-4 py-2 text-sm text-emerald-100">
      {text}
    </div>
  );
}

function ThinkingBlock({ text, open }: { text: string; open: boolean }) {
  if (!text) return null;
  return (
    <details open={open} className="mb-2 border-l-2 border-zinc-700 pl-3">
      <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
        Spark's reasoning
      </summary>
      <p className="mt-1 whitespace-pre-wrap text-xs italic leading-relaxed text-zinc-500">
        {text}
      </p>
    </details>
  );
}

function Sources({
  sources,
  message,
}: {
  sources: Source[];
  message: string;
}) {
  if (sources.length === 0) return null;
  return (
    <details className="mt-3 border-t border-zinc-700 pt-2">
      <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">
        {message || `${sources.length} sources`}
      </summary>
      <ul className="mt-2 space-y-1">
        {sources.map((s, j) => (
          <li key={j} className="font-mono text-[11px] text-zinc-400">
            {s.file_path}:{s.start_line}-{s.end_line}
          </li>
        ))}
      </ul>
    </details>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  return (
    <div className="mx-auto max-w-2xl space-y-3">
      <Question text={turn.question} />
      <Bubble>
        <ThinkingBlock text={turn.thinking} open={false} />
        {turn.error ? (
          <p className="text-sm text-rose-400">{turn.error}</p>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">
            {turn.answer}
          </p>
        )}
        <Sources sources={turn.sources} message={turn.sourcesMessage} />
      </Bubble>
    </div>
  );
}

function LiveTurnView({ turn }: { turn: LiveTurn }) {
  const showStatus = !turn.error && (turn.phase !== "answering" || !turn.answer);
  return (
    <div className="mx-auto max-w-2xl space-y-3">
      <Question text={turn.question} />
      <Bubble>
        {showStatus && (
          <div className="mb-2 flex items-center gap-2 text-sm text-zinc-400">
            <span className="flex gap-1">
              <Dot delay="0s" />
              <Dot delay="0.15s" />
              <Dot delay="0.3s" />
            </span>
            <span>
              {turn.phase ? PHASE_LABEL[turn.phase] : "Working"}
              {turn.sourcesMessage && turn.phase === "thinking"
                ? ` · ${turn.sourcesMessage}`
                : "…"}
            </span>
          </div>
        )}

        <ThinkingBlock text={turn.thinking} open={turn.phase === "thinking"} />

        {turn.error ? (
          <p className="text-sm text-rose-400">{turn.error}</p>
        ) : (
          turn.answer && (
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-200">
              {turn.answer}
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-emerald-400 align-middle" />
            </p>
          )
        )}

        <Sources sources={turn.sources} message={turn.sourcesMessage} />
      </Bubble>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-emerald-400"
      style={{ animationDelay: delay }}
    />
  );
}
