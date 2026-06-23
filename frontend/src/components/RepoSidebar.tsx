import { useState } from "react";
import type { Repository, RepoStatus } from "../api";

const STATUS_STYLES: Record<RepoStatus, string> = {
  pending: "bg-zinc-700 text-zinc-200",
  cloning: "bg-amber-500/20 text-amber-300",
  indexing: "bg-amber-500/20 text-amber-300",
  cancelling: "bg-rose-500/20 text-rose-300",
  ready: "bg-emerald-500/20 text-emerald-300",
  failed: "bg-rose-500/20 text-rose-300",
};

const WORKING_STATUSES: RepoStatus[] = [
  "pending",
  "cloning",
  "indexing",
  "cancelling",
];

function DivingIndicator() {
  return (
    <div className="mt-1.5">
      <div className="spark-lane">
        <span className="spark-wake" aria-hidden="true" />
        <span className="spark-fin" aria-hidden="true">
          <svg width="18" height="12" viewBox="0 0 18 12" fill="none">
            <path
              d="M2 11 C 7 10 9 6 10 1 C 12 5 14 8 16.5 11 Z"
              fill="currentColor"
            />
          </svg>
        </span>
      </div>
      <span className="mt-1 block text-[11px] text-emerald-300/80">
        Spark is diving into the repo…
      </span>
    </div>
  );
}

interface Props {
  repositories: Repository[];
  selectedId: number | null;
  busy: boolean;
  onSelect: (id: number) => void;
  onAdd: (url: string, branch: string) => void;
  onDelete: (id: number) => void;
  onCancel: (id: number) => void;
}

export default function RepoSidebar({
  repositories,
  selectedId,
  busy,
  onSelect,
  onAdd,
  onDelete,
  onCancel,
}: Props) {
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    onAdd(url.trim(), branch.trim());
    setUrl("");
    setBranch("");
  };

  return (
    <aside className="flex w-80 shrink-0 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 px-5 py-4">
        <h1 className="flex items-center gap-2 text-lg font-semibold text-zinc-100">
          <span className="text-emerald-400">▍</span>CodebaseQA
        </h1>
        <p className="mt-1 text-xs text-zinc-500">
          Index a repo, then dive in with Spark.
        </p>
      </div>

      <form onSubmit={submit} className="space-y-2 border-b border-zinc-800 p-4">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/owner/repo"
          className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-emerald-500"
        />
        <input
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="branch (optional)"
          className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-emerald-500"
        />
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-emerald-500 px-3 py-2 text-sm font-medium text-zinc-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Indexing…" : "Index repository"}
        </button>
      </form>

      <div className="flex-1 overflow-y-auto p-3">
        {repositories.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-zinc-600">
            No repositories yet.
          </p>
        )}
        <ul className="space-y-1">
          {repositories.map((repo) => (
            <li key={repo.id}>
              <button
                onClick={() => onSelect(repo.id)}
                className={`group w-full rounded-md px-3 py-2 text-left transition ${
                  selectedId === repo.id
                    ? "bg-zinc-800"
                    : "hover:bg-zinc-900"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-zinc-100">
                    {repo.name}
                  </span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${STATUS_STYLES[repo.status]}`}
                  >
                    {repo.status}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center justify-between">
                  <span className="truncate font-mono text-[11px] text-zinc-500">
                    {WORKING_STATUSES.includes(repo.status)
                      ? repo.chunk_count > 0
                        ? `${repo.chunk_count} chunks…`
                        : "starting…"
                      : `${repo.file_count} files · ${repo.chunk_count} chunks`}
                  </span>
                  {["pending", "cloning", "indexing"].includes(repo.status) ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onCancel(repo.id);
                      }}
                      className="text-[11px] text-zinc-500 hover:text-rose-400"
                    >
                      cancel
                    </button>
                  ) : repo.status === "cancelling" ? (
                    <span className="text-[11px] text-rose-400">cancelling…</span>
                  ) : (
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(repo.id);
                      }}
                      className="invisible text-[11px] text-zinc-600 hover:text-rose-400 group-hover:visible"
                    >
                      delete
                    </span>
                  )}
                </div>
                {WORKING_STATUSES.includes(repo.status) && <DivingIndicator />}
                {repo.status === "failed" && repo.error && (
                  <p className="mt-1 truncate text-[11px] text-rose-400">
                    {repo.error}
                  </p>
                )}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
