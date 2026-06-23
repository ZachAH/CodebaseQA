import { useCallback, useEffect, useState } from "react";
import {
  cancelIndexing,
  createRepository,
  deleteRepository,
  listRepositories,
  type Repository,
} from "./api";
import RepoSidebar from "./components/RepoSidebar";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const repos = await listRepositories();
      setRepositories(repos);
      setSelectedId((current) =>
        current ?? (repos.length ? repos[0].id : null),
      );
    } catch {
      /* backend not up yet — ignore */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while anything is still indexing so status chips update live.
  useEffect(() => {
    const inFlight = repositories.some((r) =>
      ["pending", "cloning", "indexing", "cancelling"].includes(r.status),
    );
    if (!inFlight) return;
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [repositories, refresh]);

  const handleAdd = async (url: string, branch: string) => {
    setBusy(true);
    try {
      const repo = await createRepository(url, branch);
      setSelectedId(repo.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to add repository");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteRepository(id);
    if (selectedId === id) setSelectedId(null);
    await refresh();
  };

  const handleCancel = async (id: number) => {
    try {
      await cancelIndexing(id);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to cancel");
    }
    await refresh();
  };

  const selected =
    repositories.find((r) => r.id === selectedId) ?? null;

  return (
    <div className="flex h-screen bg-zinc-900 text-zinc-100">
      <RepoSidebar
        repositories={repositories}
        selectedId={selectedId}
        busy={busy}
        onSelect={setSelectedId}
        onAdd={handleAdd}
        onDelete={handleDelete}
        onCancel={handleCancel}
      />
      <ChatPanel repository={selected} />
    </div>
  );
}
