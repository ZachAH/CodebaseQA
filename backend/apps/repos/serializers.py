from rest_framework import serializers

from .models import Repository


class RepositorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Repository
        fields = [
            "id",
            "name",
            "url",
            "branch",
            "status",
            "error",
            "chunk_count",
            "file_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "name",
            "status",
            "error",
            "chunk_count",
            "file_count",
            "created_at",
            "updated_at",
        ]


class RepositoryCreateSerializer(serializers.Serializer):
    url = serializers.URLField()
    branch = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_url(self, value: str) -> str:
        if not value.endswith(".git") and "github.com" not in value:
            # Lenient: accept any git-cloneable URL, but nudge toward GitHub.
            pass
        return value
