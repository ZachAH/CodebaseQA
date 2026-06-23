from django.contrib import admin

from .models import CodeChunk, Repository


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "status", "chunk_count", "file_count", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "url")


@admin.register(CodeChunk)
class CodeChunkAdmin(admin.ModelAdmin):
    list_display = ("file_path", "language", "start_line", "end_line", "repository")
    list_filter = ("language", "repository")
    search_fields = ("file_path",)
