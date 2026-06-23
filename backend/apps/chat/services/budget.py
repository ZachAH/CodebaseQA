"""Best-effort daily spend guard for Claude usage.

Tracks token usage per UTC day in the database and refuses new requests once
either the daily token total or the estimated dollar spend is reached. This is
an application-level safety net — set a hard spend limit in the Anthropic
Console as the real backstop.
"""
from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db.models import F

from ..models import DailyUsage


class BudgetExceeded(Exception):
    """Raised when the daily token or cost budget has been reached."""


def estimated_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens / 1_000_000 * settings.MODEL_INPUT_COST_PER_MTOK
        + output_tokens / 1_000_000 * settings.MODEL_OUTPUT_COST_PER_MTOK
    )


def today_usage() -> DailyUsage:
    usage, _ = DailyUsage.objects.get_or_create(date=date.today())
    return usage


def check_budget() -> None:
    """Raise BudgetExceeded if today's usage is at or over either limit."""
    usage = today_usage()
    total_tokens = usage.input_tokens + usage.output_tokens
    if total_tokens >= settings.DAILY_TOKEN_BUDGET:
        raise BudgetExceeded(
            f"Daily token budget reached ({settings.DAILY_TOKEN_BUDGET:,} tokens). "
            "It resets at 00:00 UTC."
        )
    if estimated_cost_usd(usage.input_tokens, usage.output_tokens) >= settings.DAILY_COST_BUDGET_USD:
        raise BudgetExceeded(
            f"Daily cost budget reached (~${settings.DAILY_COST_BUDGET_USD:.2f}). "
            "It resets at 00:00 UTC."
        )


def record_usage(input_tokens: int, output_tokens: int) -> None:
    """Atomically add a request's token usage to today's running total."""
    today_usage()  # ensure the row exists
    DailyUsage.objects.filter(date=date.today()).update(
        input_tokens=F("input_tokens") + input_tokens,
        output_tokens=F("output_tokens") + output_tokens,
        request_count=F("request_count") + 1,
    )
