from rest_framework import serializers


class AskSerializer(serializers.Serializer):
    repository_id = serializers.IntegerField()
    question = serializers.CharField(max_length=4000)
    # Omit to use the server-configured RETRIEVAL_TOP_K.
    top_k = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=20, default=None
    )
