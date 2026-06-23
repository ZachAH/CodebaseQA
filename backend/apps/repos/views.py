from urllib.parse import urlparse

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import Repository
from .serializers import RepositoryCreateSerializer, RepositorySerializer
from .services.ingest import start_indexing


class IndexBurstThrottle(AnonRateThrottle):
    scope = "index_burst"


# Statuses where indexing is in flight.
WORKING_STATUSES = {
    Repository.Status.PENDING,
    Repository.Status.CLONING,
    Repository.Status.INDEXING,
    Repository.Status.CANCELLING,
}


def _derive_name(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    name = path.rsplit("/", 1)[-1] if path else url
    return name[:-4] if name.endswith(".git") else name


class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    http_method_names = ["get", "post", "delete"]

    def get_throttles(self):
        # Throttle the expensive write paths; leave reads/cancel unthrottled.
        if self.action in {"create", "reindex"}:
            return [IndexBurstThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        create_serializer = RepositoryCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)
        url = create_serializer.validated_data["url"]
        branch = create_serializer.validated_data.get("branch", "")

        repository, created = Repository.objects.get_or_create(
            url=url,
            defaults={"name": _derive_name(url), "branch": branch},
        )

        # If it's already indexing, just return it — don't start a second run.
        if not created and repository.status in WORKING_STATUSES:
            return Response(RepositorySerializer(repository).data, status=status.HTTP_200_OK)

        if not created:
            # Re-add of a finished/failed repo → reset and re-index.
            repository.branch = branch
            repository.status = Repository.Status.PENDING
            repository.error = ""
            repository.save(update_fields=["branch", "status", "error", "updated_at"])

        # Index in the background; the row already exists with status "pending".
        start_indexing(repository.pk)

        return Response(
            RepositorySerializer(repository).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def reindex(self, request, pk=None):
        repository = self.get_object()
        repository.status = Repository.Status.PENDING
        repository.error = ""
        repository.save(update_fields=["status", "error", "updated_at"])
        start_indexing(repository.pk)
        return Response(RepositorySerializer(repository).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Request cancellation of an in-flight index. The worker deletes the
        repo once it notices the flag, so the row disappears shortly after."""
        repository = self.get_object()
        if repository.status in {
            Repository.Status.PENDING,
            Repository.Status.CLONING,
            Repository.Status.INDEXING,
        }:
            repository.status = Repository.Status.CANCELLING
            repository.save(update_fields=["status", "updated_at"])
        return Response(RepositorySerializer(repository).data)
