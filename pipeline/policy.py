"""Shared policy rules for the job tool.

This file holds the common yes/no rules that many scoring functions depend on,
like location checks, source realism checks, and company profile helpers.
"""

import re


def is_new_york_location(job, *, ctx):
    location = (job.get("location_lc") or job.get("location") or "").lower()
    if any(term in location for term in ctx.NY_LOCATION_TERMS):
        return True
    if re.search(r",\s*ny\b", job.get("location", ""), re.IGNORECASE):
        return True
    return False


def has_explicit_us_remote_signal(job, *, ctx):
    location = (job.get("location_lc") or job.get("location") or "").lower()
    title = (job.get("title_lc") or job.get("title") or "").lower()
    description = (job.get("description_lc") or job.get("description") or "").lower()
    combined = " ".join(part for part in [location, title, description] if part)

    explicit_terms = [
        "anywhere in the u.s.",
        "anywhere in the us",
        "remote us",
        "remote - usa",
        "remote usa",
        "remote - us",
        "u.s.-based",
        "us-based",
        "usa-based",
        "within the united states",
        "within the us",
        "must be based in the us",
        "must be located in the us",
        "must reside in the us",
        "must live in the us",
        "u.s. candidates only",
        "us candidates only",
        "u.s. only",
        "us only",
        "eligible to work in the us",
        "authorized to work in the us",
        "united states only",
    ]

    return any(term in combined for term in explicit_terms)


def is_us_location(job, *, ctx):
    location = (job.get("location_lc") or job.get("location") or "").lower()
    description = (job.get("description_lc") or job.get("description") or "").lower()
    if any(term in location for term in ctx.NON_TARGET_REMOTE_TERMS):
        return False
    if any(
        term in location
        for term in [
            "portugal",
            "lisbon",
            "europe",
            "emea",
            "uk",
            "united kingdom",
            "canada",
            "australia",
            "india",
            "singapore",
            "tokyo",
            "brazil",
            "serbia",
            "korea",
        ]
    ):
        return False
    if is_new_york_location(job, ctx=ctx):
        return True
    if any(term in location for term in ctx.US_WIDE_LOCATION_TERMS):
        return True
    if has_explicit_us_remote_signal(job, ctx=ctx):
        return True
    if job.get("is_remote") or any(term in location for term in ctx.REMOTE_LOCATION_TERMS):
        if "us" in location or "usa" in location or "united states" in location:
            return True
        if str(job.get("source_type") or "") == "aggregator" and ctx.contains_any(
            description,
            [
                "united states",
                "u.s.",
                "u.s.-based",
                "usa-based",
                "must be based in the us",
                "must be located in the us",
                "eligible to work in the us",
                "u.s. customers",
                "u.s. market",
                "for americans",
            ],
        ):
            return True
    if re.search(r",\s*[A-Z]{2}\b", job.get("location", "")):
        return True
    if re.search(
        r"\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming)\b",
        location,
    ):
        return True
    return False


def is_target_location(job, *, ctx):
    location = job["location_lc"]
    normalized_location = location.strip().lower()
    mode = ctx.LOCATION_MODE

    if is_new_york_location(job, ctx=ctx):
        return True
    if mode == "east_coast" and any(term in location for term in ctx.EAST_COAST_LOCATION_TERMS):
        return True
    if normalized_location in ctx.US_WIDE_LOCATION_TERMS:
        return True

    is_remote = job.get("is_remote") or any(term in location for term in ctx.REMOTE_LOCATION_TERMS)
    if not is_remote:
        return False
    if any(term in location for term in ctx.NON_TARGET_REMOTE_TERMS):
        return False

    if mode == "us_remote":
        return is_us_location(job, ctx=ctx)
    return is_us_location(job, ctx=ctx)


def is_geo_ambiguous_us_region(job, *, ctx):
    location = (job.get("location_lc") or job.get("location") or "").lower()
    return any(
        term in location
        for term in (
            "north america",
            "americas",
            "us or canada",
            "u.s. or canada",
            "united states or canada",
        )
    )


def is_priority_queue_location(job, *, ctx):
    location = (job.get("location_lc") or job.get("location") or "").lower()
    if is_new_york_location(job, ctx=ctx):
        return True
    if job.get("is_remote") or any(term in location for term in ctx.REMOTE_LOCATION_TERMS):
        return is_us_location(job, ctx=ctx)
    return False


def is_physical_security(text, *, ctx):
    text = text.lower()
    return ctx.matches_any_pattern(
        text,
        [
            r"\bcctv\b",
            r"\balarm monitoring\b",
            r"\bphysical security\b",
            r"\bloss prevention\b(?!\s*\()",
            r"\bloss prevention officer\b",
            r"\basset protection\b",
        ],
    )


def get_company_difficulty(company_id, *, ctx):
    company_id = ctx.normalize_company_id(company_id)
    difficulty = ctx.COMPANY_METADATA_BY_ID.get(company_id, {}).get("difficulty", "standard")

    if difficulty == "lottery":
        return {"tier": "high", "penalty": 16}
    if difficulty == "stretch":
        return {"tier": "medium", "penalty": 9}
    return {"tier": "standard", "penalty": 3}


def get_role_difficulty_modifier(job, track_name, *, ctx):
    title = job["title_lc"]
    text = job["combined_lc"]

    if ctx.is_it_track(track_name):
        if ctx.matches_any_pattern(title, [r"\bhelp ?desk\b", r"\bit support\b", r"\bdesktop support\b", r"\bservice ?desk\b"]):
            return {"label": "entry-accessible", "penalty_delta": -2}
        if ctx.matches_any_pattern(title, [r"\bsaas administrator\b", r"\bit operations?\b", r"\bsystems?(?: administrator| admin)?\b"]):
            return {"label": "bridge-role", "penalty_delta": 3}

    if ctx.is_soc_track(track_name):
        if re.search(r"\bsoc analyst\b", title):
            return {"label": "target-soc", "penalty_delta": -3}
        if re.search(r"\bsoc engineer\b", title):
            return {"label": "soc-engineer", "penalty_delta": 4}

    if ctx.is_cyber_track(track_name) and ctx.matches_any_pattern(
        text,
        [
            r"\bdistributed systems?\b",
            r"\bsoftware engineering\b",
            r"\bbackend\b",
            r"\bplatform engineering\b",
            r"\bfrom scratch\b",
        ],
    ):
        return {"label": "engineering-heavy", "penalty_delta": 6}

    return {"label": "standard-role", "penalty_delta": 0}


def detect_junior_plus(job, *, ctx):
    text = job["combined_lc"]
    signals = []

    if ctx.matches_any_pattern(text, [r"\bpoint of escalation\b", r"\bescalation point\b"]):
        signals.append("escalation responsibility")
    if ctx.matches_any_pattern(text, [r"\bon[- ]call\b", r"\bafter hours\b", r"\bweekends?\b"]):
        signals.append("on-call expectations")
    if ctx.matches_any_pattern(text, [r"\bindependently\b"]):
        signals.append("independent ownership")
    if ctx.matches_any_pattern(text, [r"\bfast[- ]paced\b", r"\bhigh[- ]growth\b", r"\bhyper[- ]growth\b"]):
        signals.append("high-growth expectations")

    return bool(signals), signals


def detect_competition_magnetism(job, track_name, company_difficulty, *, ctx):
    text = job["combined_lc"]
    location = job["location_lc"]
    score = 0
    reasons = []

    if company_difficulty in {"stretch", "lottery"}:
        score += 2
        reasons.append("brand magnet")
    if is_new_york_location(job, ctx=ctx):
        score += 1
        reasons.append("new york pool")
    if job.get("is_remote") or any(term in location for term in ctx.REMOTE_LOCATION_TERMS):
        score += 1
        reasons.append("remote volume")
    if ctx.is_it_track(track_name) and ctx.matches_any_pattern(job["title_lc"], [r"\bsaas administrator\b", r"\bit operations?\b"]):
        score += 1
        reasons.append("attractive bridge role")

    salary_patterns = [
        r"\$\s?1[0-9]{2}[,k]",
        r"\$100,?000",
        r"\$110,?000",
        r"\$120,?000",
        r"\$130,?000",
    ]
    if ctx.matches_any_pattern(text, salary_patterns):
        score += 1
        reasons.append("high salary band")

    if score >= 4:
        label = "high"
    elif score >= 2:
        label = "medium"
    else:
        label = "low"

    return {"label": label, "score": score, "reasons": reasons}


def get_company_target_profile(company_id="", company_group_hint="", metadata_hint=None, *, ctx):
    company_id = ctx.normalize_company_id(company_id)
    metadata = ctx.COMPANY_METADATA_BY_ID.get(company_id, {})
    metadata_hint = metadata_hint or {}
    tags = set(metadata.get("tags", ()) or metadata_hint.get("company_tags", ()) or ())
    difficulty = metadata.get("difficulty") or metadata_hint.get("company_difficulty") or "standard"
    hiring_pattern = metadata.get("hiring_pattern") or metadata_hint.get("company_hiring_pattern") or "standard"
    industry = metadata.get("industry") or metadata_hint.get("company_industry") or "tech"
    group = (
        company_group_hint
        or metadata.get("group")
        or metadata_hint.get("company_group")
        or "standard"
    ).strip().lower()

    acceptance_bonus = 0
    roi_multiplier = 1.0

    if "mssp" in tags:
        acceptance_bonus += 10
        roi_multiplier *= 1.14
    elif industry == "security":
        acceptance_bonus += 5
        roi_multiplier *= 1.08

    if "nyc-friendly" in tags:
        acceptance_bonus += 2
        roi_multiplier *= 1.02
    if "remote-friendly" in tags:
        acceptance_bonus += 2
        roi_multiplier *= 1.02
    if {"msp", "it-services", "service-desk", "staffing"} & tags:
        acceptance_bonus += 4
        roi_multiplier *= 1.05
    elif {"enterprise", "insurance", "gov-adjacent", "healthcare"} & tags:
        acceptance_bonus += 3
        roi_multiplier *= 1.04
    if {"prestige", "brand-magnet", "consumer"} & tags:
        acceptance_bonus -= 3
        roi_multiplier *= 0.96

    if hiring_pattern == "hire-heavy":
        acceptance_bonus += 6
        roi_multiplier *= 1.08
    elif hiring_pattern == "steady":
        acceptance_bonus += 2
        roi_multiplier *= 1.03
    elif hiring_pattern == "selective":
        acceptance_bonus -= 4
        roi_multiplier *= 0.94

    if difficulty == "lottery":
        acceptance_bonus -= 10
        roi_multiplier *= 0.78
    elif difficulty == "stretch":
        acceptance_bonus -= 4
        roi_multiplier *= 0.92
    elif difficulty == "realistic":
        acceptance_bonus += 2
        roi_multiplier *= 1.03

    profile = {
        "group": group,
        "tags": sorted(tags),
        "difficulty": difficulty,
        "hiring_pattern": hiring_pattern,
        "industry": industry,
        "acceptance_bonus": acceptance_bonus,
        "roi_multiplier": roi_multiplier,
    }

    effectiveness = ctx.get_company_effectiveness_profile(company_id)
    profile["acceptance_bonus"] += effectiveness["acceptance_bonus"]
    profile["roi_multiplier"] *= effectiveness["roi_multiplier"]
    profile["effectiveness_score"] = effectiveness["score"]
    profile["effectiveness_label"] = effectiveness["label"]
    return profile


def detect_hidden_requirement_signals(text, *, ctx):
    matches = []
    total_penalty = 0

    for label, patterns, penalty in ctx.HIDDEN_REQUIREMENT_SIGNALS:
        if ctx.matches_any_pattern(text, patterns):
            matches.append(label)
            total_penalty += penalty

    return matches, min(12, total_penalty)
