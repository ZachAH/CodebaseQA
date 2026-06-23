import json

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.repos.models import Repository

from .serializers import AskSerializer
from .services import budget
from .services.rag import stream_answer
from .throttling import AskBurstThrottle, AskDayThrottle


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


class AskView(APIView):
    """Stream a grounded answer to a question about an indexed repository.

    Responds with `text/event-stream`. Each event is `data: {json}` where the
    JSON has a `type` of: status | sources | thinking | delta | error | done.
    """

    throttle_classes = [AskBurstThrottle, AskDayThrottle]

    def post(self, request):
        serializer = AskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        question = data["question"].strip()
        if not question:
            return Response(
                {"detail": "Please ask a question."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            repository = Repository.objects.get(pk=data["repository_id"])
        except Repository.DoesNotExist:
            return Response(
                {"detail": "Repository not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if repository.status != Repository.Status.READY:
            return Response(
                {"detail": f"Repository is not ready (status: {repository.status})."},
                status=status.HTTP_409_CONFLICT,
            )

        # Daily budget guard — refuse before spending anything.
        try:
            budget.check_budget()
        except budget.BudgetExceeded as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        def event_stream():
            try:
                for event in stream_answer(repository, question, data["top_k"]):
                    yield _sse(event)
            except RuntimeError as exc:
                # Missing API key or similar configuration error.
                yield _sse({"type": "error", "message": str(exc)})
            except Exception:  # noqa: BLE001
                yield _sse(
                    {
                        "type": "error",
                        "message": "Something went wrong while answering. Please try again.",
                    }
                )

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"  # disable proxy buffering (nginx)
        return response
