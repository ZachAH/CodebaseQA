from django.db import models


class DailyUsage(models.Model):
    """Accumulated Claude token usage per UTC day, for the budget guard."""

    date = models.DateField(unique=True)
    input_tokens = models.BigIntegerField(default=0)
    output_tokens = models.BigIntegerField(default=0)
    request_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.date}: {self.input_tokens + self.output_tokens} tokens"
