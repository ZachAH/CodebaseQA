from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField


class Repository(models.Model):
    """A codebase that has been (or is being) indexed."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CLONING = "cloning", "Cloning"
        INDEXING = "indexing", "Indexing"
        CANCELLING = "cancelling", "Cancelling"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)
    branch = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    error = models.TextField(blank=True, default="")
    chunk_count = models.PositiveIntegerField(default=0)
    file_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "repositories"

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class CodeChunk(models.Model):
    """A chunk of code with its embedding vector for similarity search."""

    repository = models.ForeignKey(
        Repository, related_name="chunks", on_delete=models.CASCADE
    )
    file_path = models.CharField(max_length=1024)
    language = models.CharField(max_length=64, blank=True, default="")
    start_line = models.PositiveIntegerField(default=1)
    end_line = models.PositiveIntegerField(default=1)
    content = models.TextField()
    embedding = VectorField(dimensions=settings.EMBED_DIM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["repository", "file_path"]),
            HnswIndex(
                name="codechunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:
        return f"{self.file_path}:{self.start_line}-{self.end_line}"
