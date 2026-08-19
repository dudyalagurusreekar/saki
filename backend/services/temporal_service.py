"""
Saki Temporal Intelligence Service
Provides real-time clock awareness, time-of-day classification,
past/present/future temporal reference detection, and context-aware
greetings for natural conversation.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field


# -------------------------
# IST Timezone (UTC+5:30)
# -------------------------
IST = timezone(timedelta(hours=5, minutes=30))


# -------------------------
# Time-of-Day Periods
# -------------------------
TIME_PERIODS = {
    "dawn":       (4, 6),     # 4:00 AM – 5:59 AM
    "morning":    (6, 12),    # 6:00 AM – 11:59 AM
    "afternoon":  (12, 17),   # 12:00 PM – 4:59 PM
    "evening":    (17, 21),   # 5:00 PM – 8:59 PM
    "night":      (21, 24),   # 9:00 PM – 11:59 PM
    "late_night": (0, 4),     # 12:00 AM – 3:59 AM
}

PERIOD_EMOJIS = {
    "dawn":       "🌅",
    "morning":    "🌤️",
    "afternoon":  "☀️",
    "evening":    "🌆",
    "night":      "🌙",
    "late_night": "🌑",
}


# -------------------------
# Temporal Reference Patterns
# -------------------------
PAST_PATTERNS = [
    r"\b(yesterday|last\s+(?:week|month|year|night|time|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(ago|previously|earlier|before|back\s+(?:in|when|then))\b",
    r"\b(used\s+to|was\s+there|had\s+been|went|did|happened|occurred|remember\s+when)\b",
    r"\b(in\s+(?:19|20)\d{2})\b",  # "in 2019", "in 2024"
    r"\b(past|former|previous|old|ancient|historical)\b",
]

FUTURE_PATTERNS = [
    r"\b(tomorrow|next\s+(?:week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b",
    r"\b(upcoming|soon|later|afterwards|in\s+the\s+future|going\s+to)\b",
    r"\b(will\s+(?:be|have|do|go|come|happen)|plan(?:ning|s)?|schedule|forecast)\b",
    r"\b(in\s+(?:\d+)\s+(?:days?|weeks?|months?|years?|hours?|minutes?))\b",
    r"\b(deadline|due\s+(?:date|by)|by\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next))\b",
]

PRESENT_PATTERNS = [
    r"\b(today|now|right\s+now|currently|at\s+the\s+moment|this\s+(?:moment|instant))\b",
    r"\b(this\s+(?:week|month|year|morning|afternoon|evening|night))\b",
    r"\b(what\s+time|current\s+time|what\s+day|what\s+date)\b",
    r"\b(ongoing|happening|in\s+progress|live|real[\s-]?time)\b",
]


# -------------------------
# Data Models
# -------------------------
class TemporalContext(BaseModel):
    """Complete temporal snapshot for a given moment."""
    datetime_iso: str = Field(description="ISO-8601 datetime string with timezone")
    time_12h: str = Field(description="Human-readable 12-hour time e.g. '11:51 PM'")
    time_24h: str = Field(description="24-hour time e.g. '23:51'")
    date_display: str = Field(description="Full date e.g. 'Monday, August 18, 2026'")
    date_short: str = Field(description="Short date e.g. 'Aug 18, 2026'")
    day_of_week: str = Field(description="Day name e.g. 'Monday'")
    time_of_day: str = Field(description="dawn, morning, afternoon, evening, night, late_night")
    time_emoji: str = Field(description="Emoji for the time period")
    is_weekend: bool = Field(description="Whether it's Saturday or Sunday")
    day_type: str = Field(description="'weekday' or 'weekend'")
    month_name: str = Field(description="Full month name e.g. 'August'")
    year: int = Field(description="Current year")
    greeting: str = Field(description="Context-aware greeting suggestion")
    human_description: str = Field(description="Natural language time description")
    timezone_name: str = Field(default="IST", description="Timezone abbreviation")


class TemporalReference(BaseModel):
    """Classification of a temporal reference found in user text."""
    tense: str = Field(description="'past', 'present', or 'future'")
    confidence: float = Field(description="0.0 to 1.0")
    matched_phrase: str = Field(default="", description="The phrase that triggered the classification")
    description: str = Field(default="", description="Human-readable explanation")


# -------------------------
# Temporal Service
# -------------------------
class TemporalService:
    """
    Provides real-time temporal intelligence for Saki.
    All methods use the system clock with IST timezone.
    """

    @staticmethod
    def now() -> datetime:
        """Get current datetime in IST."""
        return datetime.now(IST)

    @staticmethod
    def get_time_of_day(hour: Optional[int] = None) -> str:
        """Classify the current hour into a time-of-day period."""
        if hour is None:
            hour = TemporalService.now().hour

        if 0 <= hour < 4:
            return "late_night"
        elif 4 <= hour < 6:
            return "dawn"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    @staticmethod
    def get_greeting(time_of_day: Optional[str] = None, hour: Optional[int] = None) -> str:
        """Generate a context-aware greeting based on time of day."""
        if time_of_day is None:
            time_of_day = TemporalService.get_time_of_day(hour)

        greetings = {
            "dawn":       "You're up early! Good dawn 🌅",
            "morning":    "Good morning! ☀️",
            "afternoon":  "Good afternoon! 🌤️",
            "evening":    "Good evening! 🌆",
            "night":      "Hey, good night! 🌙",
            "late_night": "Hey, still up? 🌑",
        }
        return greetings.get(time_of_day, "Hey there!")

    @staticmethod
    def get_human_description(dt: Optional[datetime] = None) -> str:
        """Create a natural language description of the current time."""
        if dt is None:
            dt = TemporalService.now()

        hour = dt.hour
        day_name = dt.strftime("%A")
        time_of_day = TemporalService.get_time_of_day(hour)

        # Build natural description
        if time_of_day == "late_night":
            return f"It's late {day_name} night, past midnight"
        elif time_of_day == "dawn":
            return f"It's early {day_name} dawn"
        elif time_of_day == "morning":
            if hour < 9:
                return f"It's early {day_name} morning"
            else:
                return f"It's {day_name} morning"
        elif time_of_day == "afternoon":
            if hour < 14:
                return f"It's {day_name} early afternoon"
            else:
                return f"It's {day_name} afternoon"
        elif time_of_day == "evening":
            return f"It's {day_name} evening"
        else:  # night
            return f"It's {day_name} night"

    @staticmethod
    def get_temporal_context(dt: Optional[datetime] = None) -> TemporalContext:
        """Build a complete temporal context snapshot."""
        if dt is None:
            dt = TemporalService.now()

        time_of_day = TemporalService.get_time_of_day(dt.hour)
        is_weekend = dt.weekday() >= 5  # Saturday=5, Sunday=6

        return TemporalContext(
            datetime_iso=dt.isoformat(),
            time_12h=dt.strftime("%I:%M %p").lstrip("0"),
            time_24h=dt.strftime("%H:%M"),
            date_display=dt.strftime("%A, %B %d, %Y"),
            date_short=dt.strftime("%b %d, %Y"),
            day_of_week=dt.strftime("%A"),
            time_of_day=time_of_day,
            time_emoji=PERIOD_EMOJIS.get(time_of_day, "🕐"),
            is_weekend=is_weekend,
            day_type="weekend" if is_weekend else "weekday",
            month_name=dt.strftime("%B"),
            year=dt.year,
            greeting=TemporalService.get_greeting(time_of_day),
            human_description=TemporalService.get_human_description(dt),
            timezone_name="IST",
        )

    @staticmethod
    def classify_temporal_reference(text: str) -> TemporalReference:
        """
        Analyze user text to determine if they're referring to past, present, or future.
        Returns the most confident classification.
        """
        text_lower = text.lower().strip()

        # Score each tense
        past_score = 0.0
        past_match = ""
        for pattern in PAST_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                past_score += 0.3
                if not past_match:
                    past_match = match.group(0)

        future_score = 0.0
        future_match = ""
        for pattern in FUTURE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                future_score += 0.3
                if not future_match:
                    future_match = match.group(0)

        present_score = 0.0
        present_match = ""
        for pattern in PRESENT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                present_score += 0.3
                if not present_match:
                    present_match = match.group(0)

        # Cap scores at 1.0
        past_score = min(past_score, 1.0)
        future_score = min(future_score, 1.0)
        present_score = min(present_score, 1.0)

        # Determine dominant tense
        if past_score >= future_score and past_score >= present_score and past_score > 0:
            return TemporalReference(
                tense="past",
                confidence=past_score,
                matched_phrase=past_match,
                description=f"User is referring to something in the past ('{past_match}')"
            )
        elif future_score >= past_score and future_score >= present_score and future_score > 0:
            return TemporalReference(
                tense="future",
                confidence=future_score,
                matched_phrase=future_match,
                description=f"User is referring to something in the future ('{future_match}')"
            )
        elif present_score > 0:
            return TemporalReference(
                tense="present",
                confidence=present_score,
                matched_phrase=present_match,
                description=f"User is referring to something happening now ('{present_match}')"
            )
        else:
            return TemporalReference(
                tense="present",
                confidence=0.5,
                matched_phrase="",
                description="No explicit temporal reference; defaulting to present"
            )

    @staticmethod
    def get_relative_time(target: datetime, reference: Optional[datetime] = None) -> str:
        """
        Describe how far a target datetime is from a reference point in human-friendly terms.
        E.g., '2 hours ago', 'in 3 days', 'just now'.
        """
        if reference is None:
            reference = TemporalService.now()

        delta = target - reference
        total_seconds = delta.total_seconds()
        abs_seconds = abs(total_seconds)

        if abs_seconds < 60:
            return "just now"
        elif abs_seconds < 3600:
            minutes = int(abs_seconds / 60)
            unit = "minute" if minutes == 1 else "minutes"
            return f"{minutes} {unit} ago" if total_seconds < 0 else f"in {minutes} {unit}"
        elif abs_seconds < 86400:
            hours = int(abs_seconds / 3600)
            unit = "hour" if hours == 1 else "hours"
            return f"{hours} {unit} ago" if total_seconds < 0 else f"in {hours} {unit}"
        elif abs_seconds < 2592000:  # ~30 days
            days = int(abs_seconds / 86400)
            unit = "day" if days == 1 else "days"
            return f"{days} {unit} ago" if total_seconds < 0 else f"in {days} {unit}"
        elif abs_seconds < 31536000:  # ~365 days
            months = int(abs_seconds / 2592000)
            unit = "month" if months == 1 else "months"
            return f"{months} {unit} ago" if total_seconds < 0 else f"in {months} {unit}"
        else:
            years = int(abs_seconds / 31536000)
            unit = "year" if years == 1 else "years"
            return f"{years} {unit} ago" if total_seconds < 0 else f"in {years} {unit}"

    @staticmethod
    def build_temporal_prompt_block(dt: Optional[datetime] = None) -> str:
        """
        Build a comprehensive temporal context block for inclusion in the LLM system prompt.
        This replaces the old basic date-only anchor.
        """
        ctx = TemporalService.get_temporal_context(dt)

        block = (
            f"\n[Runtime Temporal Context]\n"
            f"Current Date & Time: {ctx.date_display}, {ctx.time_12h} {ctx.timezone_name}\n"
            f"Time of Day: {ctx.time_emoji} {ctx.time_of_day.replace('_', ' ').title()}\n"
            f"Day Type: {ctx.day_type.title()}\n"
            f"Description: {ctx.human_description}\n"
            f"Year: {ctx.year}\n"
            f"\n"
            f"Temporal Awareness Rules:\n"
            f"- You know the exact current time. Reference it naturally when relevant.\n"
            f"- If the user says 'good morning' but it's night, gently acknowledge the actual time.\n"
            f"- Adjust energy to time: be calmer late at night, more energetic in the morning.\n"
            f"- Never claim the current year is 2023 or that {ctx.year} is in the future.\n"
            f"- When the user refers to past events, future plans, or current happenings, reason about time correctly.\n"
        )

        return block

    @staticmethod
    def get_tone_adjustments(time_of_day: Optional[str] = None) -> Dict[str, float]:
        """
        Return tone adjustment deltas based on time of day.
        These are additive adjustments to the base social energy values.
        """
        if time_of_day is None:
            time_of_day = TemporalService.get_time_of_day()

        adjustments = {
            "dawn":       {"energy": -0.05, "warmth": 0.10, "playfulness": -0.05, "seriousness": 0.0},
            "morning":    {"energy": 0.10,  "warmth": 0.05, "playfulness": 0.05,  "seriousness": 0.0},
            "afternoon":  {"energy": 0.0,   "warmth": 0.0,  "playfulness": 0.0,   "seriousness": 0.0},
            "evening":    {"energy": -0.05, "warmth": 0.05, "playfulness": 0.0,   "seriousness": 0.0},
            "night":      {"energy": -0.10, "warmth": 0.10, "playfulness": -0.05, "seriousness": -0.05},
            "late_night": {"energy": -0.15, "warmth": 0.15, "playfulness": -0.10, "seriousness": -0.10},
        }

        return adjustments.get(time_of_day, {"energy": 0.0, "warmth": 0.0, "playfulness": 0.0, "seriousness": 0.0})

    @staticmethod
    def get_api_response() -> Dict[str, Any]:
        """Build the response payload for the /api/time endpoint."""
        ctx = TemporalService.get_temporal_context()
        return {
            "datetime": ctx.datetime_iso,
            "time_12h": ctx.time_12h,
            "time_24h": ctx.time_24h,
            "date_display": ctx.date_display,
            "date_short": ctx.date_short,
            "day_of_week": ctx.day_of_week,
            "time_of_day": ctx.time_of_day,
            "time_emoji": ctx.time_emoji,
            "is_weekend": ctx.is_weekend,
            "day_type": ctx.day_type,
            "greeting": ctx.greeting,
            "human_description": ctx.human_description,
            "timezone": ctx.timezone_name,
        }
