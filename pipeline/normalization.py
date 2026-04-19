"""Normalization and freshness helpers for the job tool.

This file turns raw jobs from many sources into one consistent shape so later
filtering and ranking code can treat them the same way.
"""

import datetime
import re


def parse_timestamp(value, *, ctx):
    """Turn different timestamp formats into one UTC datetime object."""
    if value in (None, ""):
        return None

    if isinstance(value, (int, float)):
        timestamp = value / 1000 if value > 10**11 else value
        try:
            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        try:
            parsed = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        return parsed.astimezone(datetime.timezone.utc)

    return None


def format_runtime(seconds, *, ctx):
    """Turn raw seconds into a short human-readable runtime string."""
    total_seconds = max(0, int(round(seconds)))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def format_days_old(days_old, *, ctx):
    """Turn posting age into a short label like 2d or 12h."""
    if days_old is None:
        return "unknown"
    if days_old < 1:
        hours = max(1, int(round(days_old * 24)))
        return f"{hours}h"
    return f"{int(round(days_old))}d"


def get_freshness_priority_score(job, *, ctx):
    """Give very new jobs a stronger apply-now boost."""
    days_old = job.get("freshness_days_old")
    if days_old is None:
        return 15
    if days_old <= 1:
        return 120
    if days_old <= 2:
        return 110
    if days_old <= 3:
        return 100
    if days_old <= 7:
        return 75
    if days_old <= 14:
        return 45
    if days_old <= 30:
        return 15
    return 0


def compute_freshness(posted_at, updated_at, *, ctx):
    """Estimate how old the posting is and convert that into a score."""
    posted_dt = ctx.parse_timestamp(posted_at)
    updated_dt = ctx.parse_timestamp(updated_at)
    freshness_dt = posted_dt or updated_dt

    if freshness_dt is None:
        return {
            "freshness_score": 50,
            "freshness_label": "unknown",
            "freshness_notes": ["posting age unknown"],
            "freshness_days_old": None,
            "posted_at_iso": "",
            "updated_at_iso": updated_dt.isoformat() if updated_dt else "",
        }

    age_days = max(0.0, (ctx.NOW_UTC - freshness_dt).total_seconds() / 86400)
    notes = []

    if age_days <= 1:
        score = 100
        label = "last 24h"
        notes.append("posted in last 24h")
    elif age_days <= 3:
        score = 92
        label = "last 3 days"
        notes.append("posted in last 3 days")
    elif age_days <= 7:
        score = 80
        label = "last week"
        notes.append("posted within last week")
    elif age_days <= 14:
        score = 66
        label = "1-2 weeks"
        notes.append("posted 1-2 weeks ago")
    elif age_days <= 21:
        score = 48
        label = "2-3 weeks"
        notes.append("posted 2-3 weeks ago")
    elif age_days <= 30:
        score = 30
        label = "3-4 weeks"
        notes.append("posted 3-4 weeks ago")
    elif age_days <= 45:
        score = 18
        label = "1+ month"
        notes.append("posting is over a month old")
    elif age_days <= 60:
        score = 10
        label = "aging"
        notes.append("posting is 1-2 months old")
    elif age_days <= 90:
        score = 4
        label = "very stale"
        notes.append("posting is over 2 months old")
    else:
        score = 0
        label = "stale"
        notes.append("posting is likely archival or low-yield now")

    if updated_dt and posted_dt and updated_dt > posted_dt:
        delta_days = (updated_dt - posted_dt).total_seconds() / 86400
        updated_age_days = max(0.0, (ctx.NOW_UTC - updated_dt).total_seconds() / 86400)
        if delta_days >= 7:
            notes.append("posting was refreshed after original publish date")

        # Some ATS boards keep long-lived openings active by updating the job
        # record without changing the original publish date. We still should
        # not pretend those roles are brand new, but we also should not crush
        # them like abandoned listings when the board refreshed them recently.
        if age_days >= 60 and delta_days >= 30:
            if updated_age_days <= 3:
                score = max(score, 54)
                label = "recently refreshed"
                notes.append("old posting was updated very recently")
            elif updated_age_days <= 14:
                score = max(score, 42)
                notes.append("old posting was refreshed in the last two weeks")
            elif updated_age_days <= 30:
                score = max(score, 30)
                notes.append("old posting was refreshed in the last month")

    return {
        "freshness_score": score,
        "freshness_label": label,
        "freshness_notes": notes,
        "freshness_days_old": round(age_days, 2),
        "posted_at_iso": freshness_dt.isoformat(),
        "updated_at_iso": updated_dt.isoformat() if updated_dt else "",
    }


def normalize(job, *, ctx):
    """Clean one raw job and add the shared fields used by the rest of the pipeline."""

    def infer_location_from_description(description_text, current_location):
        current_clean = (current_location or "").strip()
        current_lc = current_clean.lower()
        if current_clean and current_lc not in {"in-office", "office", "onsite", "on-site"}:
            return current_clean

        patterns = [
            r"Available Locations?:\s*([A-Z][^\n\.]{2,120})",
            r"Available location:\s*([A-Z][^\n\.]{2,120})",
            r"This role requires you to be able to come into our ([A-Z][A-Za-z .'-]+,\s*[A-Z]{2,}|[A-Z][A-Za-z .'-]+,\s*[A-Za-z ]+) office",
        ]
        for pattern in patterns:
            match = re.search(pattern, description_text, re.IGNORECASE)
            if not match:
                continue
            value = re.sub(r"\s+", " ", match.group(1)).strip(" .|")
            value = re.split(
                r"\bAbout\b|\bThis role\b|\bWhat would\b|\bResponsibilities\b",
                value,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" .|,:;")
            if value:
                return value
        return current_clean

    inferred_primary_location = infer_location_from_description(
        job.get("description", ""),
        job.get("location", ""),
    )
    location_parts = [job.get("location", "")]
    if inferred_primary_location:
        location_parts = [inferred_primary_location]
    location_parts.extend(job.get("secondary_locations", []))

    combined_location = " | ".join(part for part in location_parts if part)
    if job.get("is_remote") and "remote" not in combined_location.lower():
        combined_location = f"{combined_location} | Remote" if combined_location else "Remote"

    title = job.get("title", "")
    description = job.get("description", "")
    company = job.get("company", "")

    normalized = dict(job)
    normalized["title"] = title.strip()
    normalized["description"] = description.strip()
    normalized["company"] = company.strip()
    normalized["location"] = combined_location
    normalized["title_lc"] = title.lower()
    normalized["location_lc"] = combined_location.lower()
    normalized["description_lc"] = description.lower()
    normalized["combined_lc"] = f"{title} {combined_location} {description}".lower()
    source = job.get("source", "")
    if source in {"greenhouse", "lever", "ashby"}:
        normalized["source_type"] = "structured"
    elif source.startswith("extended:"):
        normalized["source_type"] = "extended"
    elif source.startswith("aggregator:"):
        normalized["source_type"] = "aggregator"
    else:
        normalized["source_type"] = "other"
    freshness = ctx.compute_freshness(job.get("posted_at"), job.get("updated_at"))
    normalized.update(freshness)
    return normalized


def dedupe_jobs(jobs, *, ctx):
    """Drop exact duplicate jobs so later ranking does not waste work."""
    deduped = []
    seen = set()

    for job in jobs:
        key = job.get("url") or (
            job.get("company", "").lower(),
            job.get("title", "").lower(),
            job.get("location", "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(job)

    return deduped
