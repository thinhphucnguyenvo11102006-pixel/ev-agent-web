"""
E.V. Reminder — Reminder management with SQLite backend.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import re

logger = logging.getLogger("ev.tools.reminder")

# Will be set by orchestrator
_structured_memory = None


def set_memory(structured_mem):
    """Set the structured memory reference."""
    global _structured_memory
    _structured_memory = structured_mem


def _parse_time(time_str: str) -> datetime:
    """Parse time string to datetime. Supports ISO format and natural language."""
    # Try ISO format first
    try:
        return datetime.fromisoformat(time_str)
    except (ValueError, TypeError):
        pass

    now = datetime.now()
    time_lower = time_str.lower().strip()

    # "in X minutes/hours/days"
    match = re.match(r"in\s+(\d+)\s+(minute|hour|day|second)s?", time_lower)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit == "second":
            return now + timedelta(seconds=amount)
        elif unit == "minute":
            return now + timedelta(minutes=amount)
        elif unit == "hour":
            return now + timedelta(hours=amount)
        elif unit == "day":
            return now + timedelta(days=amount)

    # "tomorrow at HH:MM"
    match = re.match(r"tomorrow\s+at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?", time_lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # "at HH:MM" (today)
    match = re.match(r"at\s+(\d{1,2}):(\d{2})\s*(am|pm)?", time_lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now:
            target += timedelta(days=1)
        return target

    # Default: 1 hour from now
    logger.warning(f"Could not parse time '{time_str}', defaulting to 1 hour from now")
    return now + timedelta(hours=1)


def set_reminder(title: str, due_time: str, description: str = "") -> str:
    """Set a new reminder."""
    if not _structured_memory:
        return "Error: Memory system not initialized."

    try:
        parsed_time = _parse_time(due_time)
        reminder_id = _structured_memory.add_reminder(title, parsed_time, description)
        
        time_str = parsed_time.strftime("%Y-%m-%d %H:%M")
        return f"✅ Reminder set: '{title}' at {time_str} (ID: {reminder_id})"
    except Exception as e:
        return f"Error setting reminder: {e}"


def get_reminders(status: str = "upcoming") -> str:
    """Get reminders by status."""
    if not _structured_memory:
        return "Error: Memory system not initialized."

    try:
        if status == "pending":
            reminders = _structured_memory.get_pending_reminders()
        else:
            reminders = _structured_memory.get_upcoming_reminders()

        if not reminders:
            return "No reminders found."

        lines = ["📋 Reminders:\n"]
        for r in reminders:
            status_icon = "✅" if r.get("is_completed") else "⏰"
            lines.append(
                f"{status_icon} [{r['id']}] {r['title']} — {r['due_time']}"
            )
            if r.get("description"):
                lines.append(f"   {r['description']}")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error getting reminders: {e}"
