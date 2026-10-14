"""
Service module for natural language intent classification of email & calendar operations,
and deadline extraction from email content.
"""
from datetime import date, datetime, time, timedelta
import logging
import re
from typing import Any, Dict, List, Optional
import zoneinfo

from app.utils.calendar_utils import DEFAULT_TIMEZONE, get_timezone, resolve_date_from_text

logger = logging.getLogger(__name__)


def is_explicit_email_draft_intent(text: Optional[str]) -> bool:
    """
    Determines if the text explicitly requests composing, drafting, or sending an email.
    Mentions of 'email' as a source of information (e.g. 'check my emails', 'read emails')
    MUST evaluate to False.
    """
    if not text:
        return False
    t = text.lower().strip()

    # Reading/checking keywords
    reading_verbs = [
        "check", "read", "look at", "look through", "search", "scan", "list",
        "summarize", "summarise", "review", "find", "see", "any email", "unread"
    ]
    email_terms = ["email", "emails", "gmail", "inbox", "mail", "mails"]
    has_reading = any(v in t for v in reading_verbs) and any(e in t for e in email_terms)

    # Explicit drafting / sending patterns
    explicit_draft_patterns = [
        r"\bdraft\b.*?\b(?:email|mail|message|reply)\b",
        r"\b(?:compose|write|send)\b.*?\b(?:an?\s+)?(?:email|mail|message)\b",
        r"\bprepare\b.*?\b(?:an?\s+)?(?:email\s+)?draft\b",
        r"\bcreate\b.*?\b(?:an?\s+)?(?:email\s+)?draft\b",
        r"\bemail\s+(?:the\s+team\s+at\s+|to\s+)?[\w\.-]+@[\w\.-]+\.\w+",
        r"\bemail\s+(?:the\s+team|my\s+teammate|teammate|colleague|client|manager)\b",
        r"\bsend\s+(?:an?\s+)?email\s+to\b",
        r"\bwrite\s+(?:an?\s+)?email\s+to\b",
        r"\breply\s+to\s+(?:the\s+)?email\b",
    ]
    has_explicit_draft = any(re.search(pat, t) for pat in explicit_draft_patterns)

    # If the user only requested checking/reading and did NOT explicitly ask to compose/draft:
    if has_reading and not has_explicit_draft:
        return False

    return has_explicit_draft


def is_read_emails_intent(text: Optional[str]) -> bool:
    """
    Determines if the text requests checking, reading, searching, or reviewing emails.
    """
    if not text:
        return False
    t = text.lower().strip()
    reading_verbs = [
        "check", "read", "look at", "look through", "search", "scan", "list",
        "summarize", "summarise", "review", "find", "see", "unread", "last",
        "do i have", "any", "urgent", "new", "what are", "show", "tell me"
    ]
    email_terms = ["email", "emails", "gmail", "inbox", "mail", "mails"]

    has_term = any(term in t for term in email_terms)
    has_verb = any(verb in t for verb in reading_verbs)
    return has_term and has_verb


def is_calendar_schedule_intent(text: Optional[str]) -> bool:
    """
    Determines if the text requests scheduling an event or adding deadlines to Google Calendar.
    """
    if not text:
        return False
    t = text.lower().strip()
    schedule_phrases = [
        "schedule", "add to calendar", "add to my calendar", "add that to my calendar",
        "update that in my google calendar", "update in my google calendar",
        "update my google calendar", "update calendar", "create event", "create calendar event",
        "put on calendar", "put in my calendar", "schedule it", "block time"
    ]
    return any(p in t for p in schedule_phrases)


def is_calendar_inspect_intent(text: Optional[str]) -> bool:
    """
    Determines if the text requests inspecting calendar availability, free time, or meetings.
    """
    if not text:
        return False
    t = text.lower().strip()
    inspect_phrases = [
        "free time", "available slots", "open slots", "inspect availability",
        "inspect calendar", "check calendar", "check my calendar", "when am i free",
        "what meetings", "daily plan", "calendar for tomorrow"
    ]
    return any(p in t for p in inspect_phrases)


def extract_deadlines_from_emails(
    emails: List[Dict[str, Any]],
    tz_name: str = DEFAULT_TIMEZONE,
) -> List[Dict[str, Any]]:
    """
    Analyzes a list of emails, identifies genuine deadline commitments,
    and returns structured calendar event specifications.
    Returns an empty list if no genuine deadlines are found.
    """
    if not emails:
        return []

    tz = get_timezone(tz_name)
    now_local = datetime.now(tz)
    deadlines: List[Dict[str, Any]] = []
    seen_keys = set()

    deadline_keywords = [
        "deadline", "due by", "due on", "due date", "submit by",
        "submission deadline", "final submission", "important deadline",
        "due tomorrow", "due today", "complete by"
    ]

    for email in emails:
        if not isinstance(email, dict):
            continue

        subject = (email.get("subject") or email.get("title") or "").strip()
        snippet = (email.get("snippet") or email.get("description") or "").strip()
        body = (email.get("body") or email.get("content") or "").strip()
        email_id = email.get("id") or email.get("message_id") or ""

        combined = f"{subject}\n{snippet}\n{body}".strip()
        combined_lower = combined.lower()

        # Check if email contains any deadline indicators
        if not any(k in combined_lower for k in deadline_keywords):
            continue

        # Extract context around the deadline
        matched_dt: Optional[datetime] = None
        matched_phrase = ""

        # Pattern 1: Explicit ISO/date formats e.g. 2026-10-15 or 2026-10-15T18:00:00
        date_iso_match = re.search(r"\b(\d{4}-\d{2}-\d{2})(?:[T ](\d{1,2}:\d{2}(?::\d{2})?))?\b", combined)
        if date_iso_match:
            d_str = date_iso_match.group(1)
            t_str = date_iso_match.group(2) or "18:00"
            try:
                base_d = datetime.strptime(d_str, "%Y-%m-%d").date()
                hour_part, min_part = [int(p) for p in t_str.split(":")[:2]]
                matched_dt = datetime.combine(base_d, time(hour_part, min_part), tzinfo=tz)
                matched_phrase = date_iso_match.group(0)
            except Exception:
                pass

        # Pattern 2: "tomorrow" / "today" references
        if not matched_dt:
            if "tomorrow" in combined_lower:
                target_d = now_local.date() + timedelta(days=1)
                # Check for explicit time e.g. 5:00 PM, 5pm, 17:00, 6pm
                time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", combined_lower)
                if time_match:
                    hr = int(time_match.group(1))
                    mn = int(time_match.group(2) or 0)
                    meridiem = time_match.group(3)
                    if meridiem == "pm" and hr < 12:
                        hr += 12
                    elif meridiem == "am" and hr == 12:
                        hr = 0
                    matched_dt = datetime.combine(target_d, time(hr, mn), tzinfo=tz)
                else:
                    matched_dt = datetime.combine(target_d, time(18, 0), tzinfo=tz)
                matched_phrase = "tomorrow"
            elif "today" in combined_lower:
                target_d = now_local.date()
                matched_dt = datetime.combine(target_d, time(18, 0), tzinfo=tz)
                matched_phrase = "today"

        # Fallback if deadline keyword matched but date was ambiguous: default to tomorrow 18:00
        if not matched_dt:
            target_d = now_local.date() + timedelta(days=1)
            matched_dt = datetime.combine(target_d, time(18, 0), tzinfo=tz)
            matched_phrase = "upcoming deadline"

        clean_subject = subject.replace("Fwd:", "").replace("Re:", "").strip()
        summary_title = f"Deadline: {clean_subject}" if clean_subject else "Deadline from Email"
        iso_start = matched_dt.isoformat()

        dedup_key = f"{summary_title.lower()}:{iso_start}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        description = (
            f"Extracted from email: '{subject}'\n"
            f"Context: {snippet[:200] if snippet else body[:200]}\n"
            f"Detected Deadline: {matched_phrase} ({iso_start})\n"
            f"Auto-scheduled by LifeOS Operator."
        )

        deadlines.append({
            "title": summary_title,
            "summary": summary_title,
            "start_datetime": iso_start,
            "description": description,
            "source_email_id": email_id,
            "source_subject": subject,
            "source_snippet": snippet,
        })

    return deadlines
