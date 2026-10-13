from datetime import date, datetime, time, timedelta
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import zoneinfo

logger = logging.getLogger(__name__)

DEFAULT_TIMEZONE = "Asia/Kolkata"
DEFAULT_WORK_START_HOUR = 9   # 09:00 AM
DEFAULT_WORK_END_HOUR = 18    # 06:00 PM


def get_timezone(tz_name: Optional[str] = None) -> zoneinfo.ZoneInfo:
    """Safely returns a ZoneInfo object, defaulting to Asia/Kolkata."""
    try:
        return zoneinfo.ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    except Exception:
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)


def resolve_date_from_text(
    text: Optional[str],
    tz_name: str = DEFAULT_TIMEZONE,
) -> Tuple[datetime.date, str]:
    """
    Resolves relative references like 'today', 'tomorrow', or explicit dates
    in the context of the user's local timezone.
    Returns (resolved_date, date_str_YYYY_MM_DD).
    """
    tz = get_timezone(tz_name)
    now_local = datetime.now(tz)
    today = now_local.date()

    if not text:
        return today + timedelta(days=1), (today + timedelta(days=1)).strftime("%Y-%m-%d")

    clean = text.lower().strip()
    if "today" in clean:
        resolved = today
    elif "tomorrow" in clean:
        resolved = today + timedelta(days=1)
    elif "yesterday" in clean:
        resolved = today - timedelta(days=1)
    else:
        # Check for explicit YYYY-MM-DD
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", clean)
        if match:
            try:
                resolved = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            except ValueError:
                resolved = today + timedelta(days=1)
        else:
            resolved = today + timedelta(days=1)

    return resolved, resolved.strftime("%Y-%m-%d")


def get_day_rfc3339_boundaries(
    target_date: datetime.date,
    tz_name: str = DEFAULT_TIMEZONE,
) -> Tuple[str, str]:
    """
    Computes RFC3339 string boundaries for 00:00:00 to 23:59:59 in the target timezone.
    e.g. '2026-10-14T00:00:00+05:30' and '2026-10-14T23:59:59+05:30'.
    """
    tz = get_timezone(tz_name)
    start_dt = datetime.combine(target_date, time(0, 0, 0), tzinfo=tz)
    end_dt = datetime.combine(target_date, time(23, 59, 59), tzinfo=tz)
    return start_dt.isoformat(), end_dt.isoformat()


def normalize_calendar_event(
    event: Dict[str, Any],
    tz_name: str = DEFAULT_TIMEZONE,
) -> Dict[str, Any]:
    """
    Normalizes a Google Calendar API event into a clean, uniform dictionary.
    Handles all-day events, dateTime objects, attendee lists, and summary defaults.
    """
    summary = event.get("summary") or event.get("title") or "Untitled Meeting"
    start_info = event.get("start", {})
    end_info = event.get("end", {})

    is_all_day = "date" in start_info and "dateTime" not in start_info
    start_raw = start_info.get("dateTime") or start_info.get("date") or ""
    end_raw = end_info.get("dateTime") or end_info.get("date") or ""

    attendees = []
    for att in event.get("attendees", []):
        if isinstance(att, dict):
            email = att.get("email") or att.get("displayName")
            if email:
                attendees.append(email)
        elif isinstance(att, str):
            attendees.append(att)

    return {
        "id": event.get("id"),
        "title": summary,
        "start_time": start_raw,
        "end_time": end_raw,
        "is_all_day": is_all_day,
        "timezone": tz_name,
        "attendees": attendees,
        "location": event.get("location"),
        "status": event.get("status", "confirmed"),
        "source": "google_calendar",
    }


def parse_event_time_to_minutes(
    time_str: str,
    target_date: datetime.date,
    tz_name: str = DEFAULT_TIMEZONE,
) -> Optional[int]:
    """
    Converts an ISO time string or YYYY-MM-DD date string to minutes from start of target_date.
    Returns minutes (e.g. 09:30 -> 570) or None if not applicable.
    """
    if not time_str:
        return None

    tz = get_timezone(tz_name)

    # All-day event date format: YYYY-MM-DD
    if len(time_str) == 10 and time_str.count("-") == 2:
        try:
            ev_date = datetime.strptime(time_str, "%Y-%m-%d").date()
            if ev_date == target_date:
                return 0
            elif ev_date > target_date:
                return 24 * 60
            else:
                return 0
        except ValueError:
            return None

    try:
        # Parse ISO datetime
        dt = datetime.fromisoformat(time_str)
        # Convert to target timezone
        dt_local = dt.astimezone(tz)
        if dt_local.date() < target_date:
            return 0
        elif dt_local.date() > target_date:
            return 24 * 60
        else:
            return dt_local.hour * 60 + dt_local.minute
    except Exception as exc:
        logger.debug("Failed to parse event time %s: %s", time_str, exc)
        return None


def calculate_free_time_analysis(
    raw_events: List[Dict[str, Any]],
    target_date: datetime.date,
    tz_name: str = DEFAULT_TIMEZONE,
    work_start_hour: int = DEFAULT_WORK_START_HOUR,
    work_end_hour: int = DEFAULT_WORK_END_HOUR,
) -> Dict[str, Any]:
    """
    Calculates meetings, merged busy blocks, and available free intervals within
    the defined working hours window. Correctly merges overlapping meetings to
    prevent double counting.
    """
    window_start_min = work_start_hour * 60
    window_end_min = work_end_hour * 60
    total_window_min = window_end_min - window_start_min

    normalized_meetings = []
    busy_intervals_raw: List[Tuple[int, int]] = []

    for ev in raw_events:
        norm = normalize_calendar_event(ev, tz_name)
        normalized_meetings.append(norm)

        # Calculate interval in minutes
        s_min = parse_event_time_to_minutes(norm["start_time"], target_date, tz_name)
        e_min = parse_event_time_to_minutes(norm["end_time"], target_date, tz_name)

        if s_min is not None and e_min is not None:
            # Clamp to working window
            clamped_s = max(window_start_min, min(window_end_min, s_min))
            clamped_e = max(window_start_min, min(window_end_min, e_min))
            if clamped_e > clamped_s:
                busy_intervals_raw.append((clamped_s, clamped_e))

    # Merge overlapping or adjacent intervals
    merged_busy: List[Tuple[int, int]] = []
    if busy_intervals_raw:
        busy_intervals_raw.sort(key=lambda x: x[0])
        curr_s, curr_e = busy_intervals_raw[0]
        for next_s, next_e in busy_intervals_raw[1:]:
            if next_s <= curr_e:
                curr_e = max(curr_e, next_e)
            else:
                merged_busy.append((curr_s, curr_e))
                curr_s, curr_e = next_s, next_e
        merged_busy.append((curr_s, curr_e))

    # Calculate free intervals
    free_intervals: List[Tuple[int, int]] = []
    prev_end = window_start_min
    for b_s, b_e in merged_busy:
        if b_s > prev_end:
            free_intervals.append((prev_end, b_s))
        prev_end = max(prev_end, b_e)
    if prev_end < window_end_min:
        free_intervals.append((prev_end, window_end_min))

    # Calculate durations
    total_busy_min = sum(e - s for s, e in merged_busy)
    total_free_min = sum(e - s for s, e in free_intervals)

    def _format_time_label(m: int) -> str:
        return f"{m // 60:02d}:{m % 60:02d}"

    def _format_duration(m: int) -> str:
        h = m // 60
        mins = m % 60
        if h > 0 and mins > 0:
            return f"{h}h {mins}m"
        elif h > 0:
            return f"{h}h"
        else:
            return f"{mins}m"

    formatted_busy_blocks = [
        f"{_format_time_label(s)} - {_format_time_label(e)} ({_format_duration(e - s)})"
        for s, e in merged_busy
    ]
    formatted_free_blocks = [
        f"{_format_time_label(s)} - {_format_time_label(e)} ({_format_duration(e - s)} free)"
        for s, e in free_intervals
    ]

    return {
        "requested_date": target_date.strftime("%Y-%m-%d"),
        "timezone": tz_name,
        "window_start": f"{work_start_hour:02d}:00",
        "window_end": f"{work_end_hour:02d}:00",
        "total_window_minutes": total_window_min,
        "meetings": normalized_meetings,
        "meetings_count": len(normalized_meetings),
        "busy_intervals": formatted_busy_blocks,
        "total_busy_minutes": total_busy_min,
        "total_busy_formatted": _format_duration(total_busy_min),
        "free_intervals": formatted_free_blocks,
        "total_free_minutes": total_free_min,
        "total_free_formatted": _format_duration(total_free_min),
        "status": "success",
        "error": None,
    }


def format_telegram_calendar_report(analysis: Dict[str, Any]) -> str:
    """
    Formats the structured calendar analysis into the exact Telegram report
    required by Section 4.
    """
    req_date = analysis.get("requested_date", "Unknown Date")
    tz_name = analysis.get("timezone", DEFAULT_TIMEZONE)
    meetings = analysis.get("meetings", [])
    free_intervals = analysis.get("free_intervals", [])
    total_free_str = analysis.get("total_free_formatted", "0m")
    w_start = analysis.get("window_start", "09:00")
    w_end = analysis.get("window_end", "18:00")
    status = analysis.get("status", "success")
    error = analysis.get("error")

    if status != "success" or error:
        return (
            f"📅 *LifeOS Calendar Report*\n"
            f"Date: `{req_date}`\n"
            f"Timezone: `{tz_name}`\n\n"
            f"⚠️ *Calendar Check Failed:*\n"
            f"{error or 'Unable to retrieve events from Google Calendar.'}\n\n"
            f"Data source: Connected Google Calendar\n"
            f"Status: Failed"
        )

    # Format Meetings list
    if meetings:
        lines = []
        for m in meetings:
            title = m.get("title", "Untitled Meeting")
            st = m.get("start_time", "")
            et = m.get("end_time", "")
            # Shorten time strings if ISO
            if "T" in st:
                st = st.split("T")[1][:5]
            if "T" in et:
                et = et.split("T")[1][:5]
            lines.append(f"• *{title}* ({st} - {et})")
        meetings_str = "\n".join(lines)
    else:
        meetings_str = "• No scheduled meetings found on this date."

    # Format Free Time
    if free_intervals:
        free_lines = [f"• {blk}" for blk in free_intervals]
        free_str = "\n".join(free_lines)
    else:
        free_str = "• No free intervals available within working hours."

    return (
        f"📅 *LifeOS Calendar Report*\n"
        f"Date: `{req_date}`\n"
        f"Timezone: `{tz_name}`\n\n"
        f"📌 *Meetings:*\n{meetings_str}\n\n"
        f"⏳ *Free Time ({w_start} - {w_end}):*\n{free_str}\n"
        f"*Total Free Time:* {total_free_str} within working hours\n\n"
        f"Data source: Connected Google Calendar\n"
        f"Status: Success & Verified"
    )
