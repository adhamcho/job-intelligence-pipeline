"""Small shared helpers for the job tool.

This file keeps the tiny track and text helpers in one place so `main.py`
does not have to carry lots of small utility functions.
"""

import re


def is_cyber_track(track_name, *, ctx):
    return track_name in {"soc_analyst", "cyber_analyst"}


def is_soc_track(track_name, *, ctx):
    return track_name == "soc_analyst"


def is_cyber_analyst_track(track_name, *, ctx):
    return track_name == "cyber_analyst"


def is_it_track(track_name, *, ctx):
    return track_name == "it_bridge"


def get_resume_for_track(resumes, track_name, *, ctx):
    return resumes[ctx.TRACKS[track_name]["resume_key"]]


def get_skill_profile(track_name, *, ctx):
    return ctx.TRACKS[track_name]["skill_profile"]


def contains_any(text, terms, *, ctx):
    return any(term in text for term in terms)


def matches_any_pattern(text, patterns, *, ctx):
    return any(re.search(pattern, text) for pattern in patterns)


def count_matching_terms(text, terms, *, ctx):
    return sum(1 for term in terms if term in text)


def is_internship_like(job, *, ctx):
    text = f"{job['title_lc']} {job['description_lc']}"
    return matches_any_pattern(
        text,
        [
            r"\bintern(?:ship)?\b",
            r"\bnew grad(?:uate)?\b",
            r"\brecent graduate\b",
            r"\buniversity graduate\b",
            r"\bco[- ]?op\b",
            r"\bapprentice\b",
            r"\bfellowship\b",
        ],
        ctx=ctx,
    )


def is_internship_target_location(job, *, ctx):
    location = job["location_lc"]
    if not location or location == "in-office":
        return True
    return ctx.is_us_location(job)
