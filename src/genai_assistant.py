"""
GenAI-assisted operations assistant.

Turns structured security events and transaction data into a clear,
natural-language daily briefing — the kind of summary a non-technical
manager could read in 30 seconds instead of scanning a raw event log.

Design principle (same as the eBOM/mBOM project): the LLM only ever
summarizes data it's given — it never invents numbers or event details.
All facts come from the structured SecurityEvent/Transaction objects;
the LLM's only job is turning facts into readable language. If no API
key is configured, the function still returns a complete, useful
report using a deterministic template — the pipeline never hard-depends
on the external API being available.
"""

import json
import os

try:
    import requests
except ImportError:
    requests = None

from models import SecurityEvent, Transaction


def _call_claude(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or requests is None:
        return None
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["content"]
        return "".join(block.get("text", "") for block in content)
    except Exception as e:
        return f"[LLM summarization unavailable: {e}]"


def summarize_security_events(events: list[SecurityEvent]) -> str:
    if not events:
        return "No security events detected. All transactions within normal parameters."

    events_json = json.dumps([
        {"severity": e.severity, "type": e.event_type, "message": e.message}
        for e in events
    ], indent=2)

    prompt = (
        "You are an operations assistant summarizing security/governance "
        "events for a daily briefing to a non-technical manager. Write a "
        "clear 3-5 sentence summary, grouped by severity, using ONLY the "
        "data below. Do not invent any numbers or details not present.\n\n"
        f"Security events (JSON):\n{events_json}"
    )

    llm_summary = _call_claude(prompt)
    if llm_summary:
        return llm_summary

    # Deterministic fallback — no LLM dependency required
    high = [e for e in events if e.severity == "HIGH"]
    medium = [e for e in events if e.severity == "MEDIUM"]
    low = [e for e in events if e.severity == "LOW"]

    lines = [f"Daily security summary: {len(events)} total event(s)."]
    if high:
        lines.append(f"HIGH severity ({len(high)}): " + "; ".join(e.message for e in high))
    if medium:
        lines.append(f"MEDIUM severity ({len(medium)}): " + "; ".join(e.message for e in medium))
    if low:
        lines.append(f"LOW severity ({len(low)}): " + "; ".join(e.message for e in low))
    return "\n".join(lines)


def daily_ops_briefing(transactions: list[Transaction], events: list[SecurityEvent]) -> str:
    total_amount = sum(t.amount for t in transactions)
    by_source: dict[str, int] = {}
    for t in transactions:
        by_source[t.source.value] = by_source.get(t.source.value, 0) + 1

    source_breakdown = ", ".join(f"{k}: {v}" for k, v in by_source.items())

    report = [
        "=== Daily Operations Briefing ===",
        f"Total transactions processed: {len(transactions)}",
        f"Total transaction value: {total_amount:,.0f} JPY",
        f"By source: {source_breakdown}",
        "",
        "Security Summary:",
        summarize_security_events(events),
    ]
    return "\n".join(report)