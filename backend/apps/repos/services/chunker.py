"""Walk a cloned repository and split source files into line-based chunks.

This is a deliberately simple, language-agnostic chunker: it splits each file
into overlapping windows of lines. It's a solid baseline for code RAG and easy
to later swap for an AST-aware splitter (e.g. tree-sitter) per language.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# File extensions worth indexing, mapped to a language label.
LANGUAGE_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".sql": "sql",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".vue": "vue",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
}

# Directories we never want to index.
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".mypy_cache",
    ".pytest_cache",
    "vendor",
    "target",
    ".next",
    ".cache",
    "coverage",
    ".idea",
    ".vscode",
}

MAX_FILE_BYTES = 1_000_000  # skip files larger than ~1 MB


@dataclass
class Chunk:
    file_path: str
    language: str
    start_line: int
    end_line: int
    content: str


def iter_source_files(root: Path):
    """Yield (absolute_path, relative_path) for indexable files under root."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            ext = Path(filename).suffix.lower()
            if ext not in LANGUAGE_BY_EXT:
                continue
            abs_path = Path(dirpath) / filename
            try:
                if abs_path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield abs_path, abs_path.relative_to(root)


def chunk_file(
    abs_path: Path,
    rel_path: Path,
    window: int = 60,
    overlap: int = 15,
) -> list[Chunk]:
    """Split a single file into overlapping line windows."""
    try:
        text = abs_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    lines = text.splitlines()
    if not lines:
        return []

    language = LANGUAGE_BY_EXT.get(abs_path.suffix.lower(), "")
    step = max(window - overlap, 1)
    chunks: list[Chunk] = []
    for start in range(0, len(lines), step):
        window_lines = lines[start : start + window]
        if not any(line.strip() for line in window_lines):
            continue
        chunks.append(
            Chunk(
                file_path=str(rel_path),
                language=language,
                start_line=start + 1,
                end_line=start + len(window_lines),
                content="\n".join(window_lines),
            )
        )
        if start + window >= len(lines):
            break
    return chunks


def chunk_repository(root: Path) -> list[Chunk]:
    """Produce all chunks for a cloned repository."""
    chunks: list[Chunk] = []
    for abs_path, rel_path in iter_source_files(root):
        chunks.extend(chunk_file(abs_path, rel_path))
    return chunks
