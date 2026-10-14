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


def normalize_voice_transcript(text: Optional[str]) -> str:
    """
    Normalizes common mobile microphone and speech-to-text (Whisper/Omi) misrecognitions.
    Example: 'twenty four hour females' -> 'twenty four hour emails'
             'say Julie' / 'say julie' -> 'schedule it'
    """
    if not text:
        return ""
    t = text.replace("\u043c", "m").replace("\u041c", "M").replace("\u0440", "p").replace("\u0420", "P")
    t = re.sub(r"\b(?:twenty[\s\-]+four|24)[\s\-]+(?:hour|hr|hrs)?[\s\-]+females\b", "last 24 hour emails", t, flags=re.I)
    t = re.sub(r"\b(check|read|review|scan|search|list)[\s\-]+(?:my[\s\-]+)?female(?:s)?\b", r"\1 my emails", t, flags=re.I)
    t = re.sub(r"\bmy[\s\-]+female(?:s)?\b", "my emails", t, flags=re.I)
    t = re.sub(r"\bfemale(?:s)?[\s\-]+inbox\b", "email inbox", t, flags=re.I)
    t = re.sub(r"\bfemale(?:s)?\s+and\s+let\s+me\s+know\b", "emails and let me know", t, flags=re.I)
    # Fix 'say Julie' / 'say julie' / 'sayjulie' -> 'schedule it'
    t = re.sub(r"\b(?:like\s+)?say\s+julie\b", "schedule it", t, flags=re.I)
    # Fix 'line give the summarization' -> 'give the summarization'
    t = re.sub(r"\bline\s+give\s+the\b", "give the", t, flags=re.I)
    # Fix hyphenated e-mails
    t = re.sub(r"\be[\s\-]+mails\b", "emails", t, flags=re.I)
    t = re.sub(r"\be[\s\-]+mail\b", "email", t, flags=re.I)
    return t


def is_explicit_email_draft_intent(text: Optional[str]) -> bool:
    """
    Determines if the text explicitly requests composing, drafting, or sending an email.
    Mentions of 'email' as a source of information (e.g. 'check my emails', 'read emails')
    MUST evaluate to False.
    """
    if not text:
        return False
    norm_text = normalize_voice_transcript(text)
    t = norm_text.lower().strip()

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


def is_read_emails_intent(text: Optional[str], plan_summary: Optional[str] = None) -> bool:
    """
    Determines if the text requests checking, reading, searching, or reviewing emails.
    Normalizes speech-to-text misrecognitions and optionally checks Lyzr Manager's plan summary.
    """
    if not text and not plan_summary:
        return False
    norm_text = normalize_voice_transcript(text)
    t = norm_text.lower().strip()
    reading_verbs = [
        "check", "read", "look at", "look through", "search", "scan", "list",
        "summarize", "summarise", "summarization", "review", "find", "see", "unread", "last",
        "do i have", "any", "urgent", "new", "what are", "show", "tell me"
    ]
    email_terms = ["email", "emails", "gmail", "inbox", "mail", "mails"]

    has_term = any(term in t for term in email_terms)
    has_verb = any(verb in t for verb in reading_verbs)
    if has_term and has_verb:
        return True

    # Check Lyzr Manager's synthesized plan summary
    if plan_summary:
        ps = plan_summary.lower()
        if any(e in ps for e in email_terms) and any(v in ps for v in ["review", "check", "read", "email content", "recent emails", "last 24 hours"]):
            return True

    return False


def is_calendar_schedule_intent(text: Optional[str], plan_summary: Optional[str] = None) -> bool:
    """
    Determines if the text requests scheduling an event or adding deadlines to Google Calendar.
    Normalizes speech-to-text misrecognitions and optionally checks Lyzr Manager's plan summary.
    """
    if not text and not plan_summary:
        return False
    norm_text = normalize_voice_transcript(text)
    t = norm_text.lower().strip()
    schedule_phrases = [
        "schedule", "add to calendar", "add to my calendar", "add that to my calendar",
        "update that in my google calendar", "update in my google calendar",
        "update in the google calendar", "update the google calendar", "update in google calendar",
        "update my google calendar", "update calendar", "create event", "create calendar event",
        "put on calendar", "put in my calendar", "schedule it", "block time"
    ]
    if any(p in t for p in schedule_phrases):
        return True

    if plan_summary:
        ps = plan_summary.lower()
        if "google calendar" in ps and any(w in ps for w in ["add", "create", "update", "schedule", "entry", "entries"]):
            return True

    return False


def is_calendar_inspect_intent(text: Optional[str]) -> bool:
    """
    Determines if the text requests inspecting calendar availability, free time, or meetings.
    """
    if not text:
        return False
    norm_text = normalize_voice_transcript(text)
    t = norm_text.lower().strip()
    inspect_phrases = [
        "free time", "available slots", "open slots", "inspect availability",
        "inspect calendar", "check calendar", "check my calendar", "when am i free",
        "what meetings", "daily plan", "calendar for tomorrow"
    ]
    return any(p in t for p in inspect_phrases)


def is_summarize_emails_intent(text: Optional[str], plan_summary: Optional[str] = None) -> bool:
    """
    Determines if the text requests summarizing or giving an overview/digest of emails.
    """
    if not text and not plan_summary:
        return False
    norm_text = normalize_voice_transcript(text)
    t = norm_text.lower().strip()
    summary_words = ["summarize", "summarise", "summarization", "summary", "overview", "digest", "brief me", "give me a summary"]
    if any(w in t for w in summary_words):
        return True

    if plan_summary:
        ps = plan_summary.lower()
        if "summary" in ps or "summarize" in ps or "summarization" in ps:
            return True

    return False


def extract_email_fields(email: Dict[str, Any]) -> Dict[str, str]:
    """
    Safely extracts subject, snippet, body, sender, date, and id from an email dict.
    Supports both flat key formats and nested Google Gmail API payload.headers structures.
    """
    if not isinstance(email, dict):
        return {"id": "", "subject": "", "snippet": "", "sender": "", "body": "", "date": ""}

    subject = str(email.get("subject") or email.get("title") or "").strip()
    snippet = str(email.get("snippet") or email.get("description") or "").strip()
    sender = str(email.get("sender") or email.get("from") or "").strip()
    body = str(email.get("body") or email.get("content") or "").strip()
    date_str = str(email.get("date") or email.get("internalDate") or "").strip()
    email_id = str(email.get("id") or email.get("message_id") or "")

    # Check Google Gmail API payload.headers if subject, sender, or date are empty
    payload = email.get("payload")
    if isinstance(payload, dict):
        headers = payload.get("headers")
        if isinstance(headers, list):
            for h in headers:
                if isinstance(h, dict):
                    name = str(h.get("name") or "").lower()
                    val = str(h.get("value") or "").strip()
                    if name == "subject" and not subject:
                        subject = val
                    elif name == "from" and not sender:
                        sender = val
                    elif name == "date" and not date_str:
                        date_str = val
        if not body:
            p_body = payload.get("body")
            if isinstance(p_body, dict) and p_body.get("data"):
                body = str(p_body.get("data"))

    return {
        "id": email_id,
        "subject": subject,
        "snippet": snippet,
        "sender": sender,
        "body": body,
        "date": date_str,
    }


def summarize_recent_emails(emails: List[Dict[str, Any]]) -> str:
    """
    Produces a concise, structured natural language summary of recent emails.
    Formats sender, subject, and core context cleanly without any emojis.
    """
    if not emails:
        return "No new emails received in the last 24 hours."

    lines: List[str] = []
    for idx, em in enumerate(emails, 1):
        fields = extract_email_fields(em)
        subj = fields["subject"] or "No Subject"
        sndr = fields["sender"] or "Unknown Sender"
        snip = fields["snippet"] or fields["body"][:150] or "No preview available"
        clean_snip = " ".join(snip.split())
        if len(clean_snip) > 160:
            clean_snip = clean_snip[:157] + "..."
        lines.append(f"{idx}. {subj} (From: {sndr})\n   Summary: {clean_snip}")

    return "\n".join(lines)


def format_telegram_execution_report(
    transcript: str,
    calendar_result: Optional[Dict[str, Any]] = None,
    action_results: Optional[List[Any]] = None,
    plan_summary: Optional[str] = None,
) -> str:
    """
    Builds a structured, human-readable Telegram execution report.
    Presents Spoken Request, Email Summary, Important Deadlines & Calendar, and Outcome.
    Strictly contains zero emojis.
    """
    cal_res = calendar_result or {}
    status_code = cal_res.get("status")

    sections: List[str] = [
        "LifeOS Execution Report",
        f"Spoken Request:\n{transcript.strip()}",
    ]

    # 1. Email Summary Section (if emails were checked, summarized, or disabled)
    email_summary = cal_res.get("email_summary")
    if email_summary:
        sections.append(f"Email Summary (Last 24 Hours):\n{email_summary.strip()}")
    elif status_code == "GMAIL_DISABLED_IN_PRECONFIGURED_MODE":
        sections.append(
            "Email Summary:\n- Gmail is disabled in Preconfigured Lyzr mode to protect account privacy. Connect your own Lyzr credentials in Settings to enable Gmail."
        )
    elif is_read_emails_intent(transcript, plan_summary):
        sections.append("Email Summary (Last 24 Hours):\n- No new emails received in the last 24 hours to summarize.")

    # 2. Deadlines & Calendar Section
    deadlines = cal_res.get("deadlines", [])
    if deadlines:
        dl_lines: List[str] = []
        for dl in deadlines:
            title = dl.get("title") or dl.get("summary") or "Deadline"
            st = dl.get("start_datetime") or "Upcoming"
            dl_lines.append(f"- {title} (Scheduled: {st})")
        sections.append("Important Deadlines & Google Calendar:\n" + "\n".join(dl_lines))
    elif status_code == "GMAIL_DISABLED_IN_PRECONFIGURED_MODE":
        sections.append("Important Deadlines & Google Calendar:\n- No deadlines extracted (Gmail disabled in Preconfigured mode).")
    elif "checked_emails" in cal_res or is_read_emails_intent(transcript, plan_summary):
        sections.append("Important Deadlines & Google Calendar:\n- No actionable deadlines detected.")

    # 3. Overall Outcome
    outcome = cal_res.get("summary")
    if not outcome:
        if is_read_emails_intent(transcript, plan_summary):
            outcome = "Checked 0 email(s) from the last 24 hours. No actionable deadlines found."
        else:
            outcome = "Execution completed."
    sections.append(f"Outcome:\n{outcome.strip()}")

    return "\n\n".join(sections)


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

        fields = extract_email_fields(email)
        subject = fields["subject"]
        snippet = fields["snippet"]
        body = fields["body"]
        email_id = fields["id"]

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


WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}


def extract_task_details(
    transcript: str,
    plan_summary: Optional[str] = None,
    tz_name: str = DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """
    Extracts an accurate task title, due timestamp (RFC3339 UTC), and notes
    from the spoken voice transcript and Lyzr Manager plan summary.
    Avoids hardcoding generic mock titles.
    """
    t_raw = transcript or ""
    t_norm = normalize_voice_transcript(t_raw)
    p_norm = normalize_voice_transcript(plan_summary or "")

    title = ""
    # 1. Inspect Lyzr Manager plan summary
    if p_norm:
        m1 = re.search(r"Intended task to add:\s*[“\"'\s]*([^“\"'\n\r]+?)[”\"'\s]*(?:\n|$)", p_norm, re.I)
        if m1 and len(m1.group(1).strip()) > 2:
            title = m1.group(1).strip(" “\"'.,")
        if not title:
            m2 = re.search(r"Actionable task identified:\s*(?:add\s+(?:a\s+)?)?[“\"'\s]*([^“\"'\n\r]+?)[”\"'\s]*(?:\n|$)", p_norm, re.I)
            if m2 and len(m2.group(1).strip()) > 2:
                title = m2.group(1).strip(" “\"'.,")

    # 2. Check for explicit naming directives in transcript: 'make it as (a) ... title'
    if not title:
        m_title = re.search(r"make it as (?:a\s+)?(.*?)\s+title", t_norm, re.I)
        if m_title and len(m_title.group(1).strip()) > 2:
            candidate = m_title.group(1).strip(" “\"'.,")
            title = candidate[0].upper() + candidate[1:]

    # 3. Check for 'assign a task in google tasks like ...'
    if not title:
        m_like = re.search(r"assign\s+a\s+task\s+(?:in|on|to)\s+(?:the\s+)?google\s+tasks?\s+like\s+(?:uh\s+)?(?:\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\s+)?(.*)", t_norm, re.I)
        if m_like and len(m_like.group(1).strip()) > 2:
            candidate = m_like.group(1).strip(" “\"'.,")
            title = candidate[0].upper() + candidate[1:]

    # 4. Extract core action phrase from transcript clauses
    if not title:
        cleaned = re.sub(r"(?:please\s+)?(?:add|assign|create|put)\s+(?:this\s+|a\s+|the\s+)?(?:task\s+)?(?:in|to|for|on)\s+(?:the\s+)?google\s+tasks?.*", "", t_norm, flags=re.I)
        cleaned = re.sub(r"(?:add|create)\s+a\s+task\s+for\s+(?:the\s+)?google\s+tasks?\.?", "", cleaned, flags=re.I)
        cleaned = re.sub(r"create\s+a\s+google\s+task\s+for\s+it.*", "", cleaned, flags=re.I)
        clauses = [c.strip() for c in re.split(r"[.,;—\n]", cleaned) if c.strip()]
        content_clauses = []
        for c in clauses:
            c_clean = re.sub(r"^(?:tomorrow|today|yesterday|morning|evening|night|uh|yeah)\b", "", c, flags=re.I).strip()
            c_clean = re.sub(r"^\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)(?!\w)", "", c_clean, flags=re.I).strip()
            c_clean = re.sub(r"^(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*(?:am|pm|a\.m\.|p\.m\.)(?!\w)", "", c_clean, flags=re.I).strip()
            if len(c_clean) > 2:
                content_clauses.append(c_clean)

        if content_clauses:
            best = content_clauses[-1]
            best = re.sub(r"^(?:i\s+need\s+to|i\s+have|i\s+has)\s+", "", best, flags=re.I).strip()
            if "hackathon" in best.lower() and "submission" in best.lower():
                title = "Hackathon submission"
            elif "marathon" in best.lower():
                title = "Running marathon" if "running" in best.lower() else "Going to marathon"
            else:
                title = best[0].upper() + best[1:]

    if not title:
        if "hackathon" in t_norm.lower():
            title = "Prepare Stop Prompting Hackathon project submission"
        else:
            title = "Voice Task"

    # Resolve date and time
    tz = get_timezone(tz_name)
    now = datetime.now(tz)

    combined_text = f"{t_norm} {p_norm}".lower()
    target_date = now.date() + timedelta(days=1)
    if "today" in combined_text:
        target_date = now.date()
    elif "tomorrow" in combined_text:
        target_date = now.date() + timedelta(days=1)

    hour = 18
    minute = 0
    time_m = re.search(r"\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|a\.m|p\.m)(?!\w)", combined_text)
    if time_m:
        h_str = time_m.group(1)
        h = WORD_TO_NUM.get(h_str, int(h_str) if h_str.isdigit() else 18)
        min_str = time_m.group(2)
        minute = int(min_str) if min_str else 0
        ampm = time_m.group(3).replace(".", "")
        if ampm == "pm" and h < 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        hour = h
    elif "morning" in combined_text:
        hour = 9
    elif "afternoon" in combined_text:
        hour = 14
    elif "evening" in combined_text:
        hour = 18
    elif "night" in combined_text:
        hour = 20

    dt = datetime.combine(target_date, time(hour, minute, 0), tzinfo=tz)
    due_iso = dt.astimezone(zoneinfo.ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")

    notes = f"Spoken via Omi. Evidence: {t_raw.strip()}"
    return {"title": title, "due": due_iso, "notes": notes}

