"""Clone a repository, chunk it, embed the chunks, and store them in pgvector.

Indexing runs in a background thread (`start_indexing`) so the HTTP request that
creates a Repository returns immediately and the UI can show live progress. The
work is cooperatively cancellable: a `cancel` request flips the row to
`CANCELLING`, and the embedding loop checks that flag between batches and bails
out, deleting the half-indexed repo.

For a production deploy you'd swap the thread for a real task queue (Celery / RQ
/ Django-Q); the shape here is already queue-friendly.
"""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from django.conf import settings
from django.db import connection
from git import GitCommandError, Repo

from ..models import CodeChunk, Repository
from . import embeddings
from .chunker import chunk_repository

# Chunks embedded + saved per batch. Smaller = more responsive cancellation and
# finer progress updates; larger = slightly less overhead.
INDEX_BATCH = 128


def _clone_path(repository: Repository) -> Path:
    return Path(settings.REPO_CLONE_DIR) / f"repo-{repository.pk}"


def _clone(repository: Repository) -> Path:
    target = _clone_path(repository)
    if target.exists():
        shutil.rmtree(target)
    clone_kwargs = {"depth": 1}
    if repository.branch:
        clone_kwargs["branch"] = repository.branch
    Repo.clone_from(repository.url, target, **clone_kwargs)
    return target


def _is_cancelled(repo_id: int) -> bool:
    status = (
        Repository.objects.filter(pk=repo_id)
        .values_list("status", flat=True)
        .first()
    )
    return status == Repository.Status.CANCELLING


def _abort_if_cancelled(repository: Repository) -> bool:
    """If cancellation was requested, delete the half-indexed repo and report it."""
    if _is_cancelled(repository.pk):
        repository.chunks.all().delete()
        repository.delete()
        return True
    return False


def index_repository(repository: Repository) -> Repository | None:
    """Full pipeline: clone -> chunk -> embed (batched) -> persist.

    Returns the Repository on success, or None if it was cancelled (in which
    case the row has been deleted).
    """
    clone_dir = _clone_path(repository)  # capture before any possible delete
    try:
        repository.status = Repository.Status.CLONING
        repository.error = ""
        repository.save(update_fields=["status", "error", "updated_at"])
        clone_dir = _clone(repository)
        if _abort_if_cancelled(repository):  # cancelled during clone
            return None

        repository.status = Repository.Status.INDEXING
        repository.chunk_count = 0
        repository.file_count = 0
        repository.save(update_fields=["status", "chunk_count", "file_count", "updated_at"])

        chunks = chunk_repository(clone_dir)
        if len(chunks) > settings.MAX_CHUNKS_PER_REPO:
            chunks = chunks[: settings.MAX_CHUNKS_PER_REPO]

        repository.chunks.all().delete()
        if _abort_if_cancelled(repository):  # cancelled during chunking
            return None

        created = 0
        for start in range(0, len(chunks), INDEX_BATCH):
            if _abort_if_cancelled(repository):
                return None

            batch = chunks[start : start + INDEX_BATCH]
            vectors = embeddings.embed_documents([c.content for c in batch])
            CodeChunk.objects.bulk_create(
                [
                    CodeChunk(
                        repository=repository,
                        file_path=c.file_path,
                        language=c.language,
                        start_line=c.start_line,
                        end_line=c.end_line,
                        content=c.content,
                        embedding=vector,
                    )
                    for c, vector in zip(batch, vectors)
                ]
            )
            created += len(batch)
            # Persist progress so the UI's chunk count climbs live.
            repository.chunk_count = created
            repository.save(update_fields=["chunk_count", "updated_at"])

        repository.chunk_count = created
        repository.file_count = len({c.file_path for c in chunks})
        repository.status = Repository.Status.READY
        repository.save(
            update_fields=["chunk_count", "file_count", "status", "updated_at"]
        )
        return repository
    except (GitCommandError, Exception) as exc:  # noqa: BLE001
        # A repo deleted mid-cancel can raise here; treat a vanished row as cancelled.
        if not Repository.objects.filter(pk=repository.pk).exists():
            return None
        repository.status = Repository.Status.FAILED
        repository.error = str(exc)
        repository.save(update_fields=["status", "error", "updated_at"])
        raise
    finally:
        if clone_dir and Path(clone_dir).exists():
            shutil.rmtree(clone_dir, ignore_errors=True)


def start_indexing(repo_id: int) -> None:
    """Run `index_repository` in a daemon thread with its own DB connection."""

    def run() -> None:
        try:
            repository = Repository.objects.get(pk=repo_id)
            index_repository(repository)
        except Repository.DoesNotExist:
            pass
        except Exception:  # noqa: BLE001 — status/error already persisted
            pass
        finally:
            connection.close()  # don't leak this thread's DB connection

    threading.Thread(target=run, daemon=True).start()
