import re


# Track skill lists.
# These are the words and weights used to measure how closely a job lines up
# with the cyber resume or the IT support resume.
TRACK_SKILLS = {
    "cyber": [
        ("soc", 6),
        ("soc analyst", 7),
        ("security analyst", 6),
        ("cybersecurity analyst", 6),
        ("security operations", 6),
        ("siem", 6),
        ("splunk", 6),
        ("sentinel", 6),
        ("microsoft sentinel", 6),
        ("alert triage", 6),
        ("alerts", 4),
        ("monitoring", 5),
        ("incident response", 6),
        ("incident handling", 5),
        ("investigation", 6),
        ("forensics", 5),
        ("log analysis", 5),
        ("kql", 5),
        ("edr", 5),
        ("xdr", 5),
        ("defender", 5),
        ("microsoft defender", 5),
        ("endpoint", 4),
        ("threat", 4),
        ("threat detection", 5),
        ("threat hunting", 4),
        ("vulnerability", 3),
        ("iam", 2),
        ("okta", 2),
        ("linux", 2),
        ("windows", 2),
        ("wireshark", 4),
        ("packet analysis", 4),
        ("ticketing", 3),
        ("case management", 3),
        ("python", 1),
        ("network", 3),
        ("cloud", 1),
        ("aws", 1),
        ("azure", 2),
        ("gcp", 1),
        ("detection", 5),
        ("response", 5),
    ],
    "it_support": [
        ("it support", 5),
        ("help desk", 5),
        ("service desk", 5),
        ("desktop support", 5),
        ("technical support", 5),
        ("ticketing", 5),
        ("active directory", 5),
        ("windows", 4),
        ("macos", 4),
        ("troubleshooting", 5),
        ("office 365", 4),
        ("okta", 3),
        ("jamf", 3),
        ("intune", 3),
        ("hardware", 4),
        ("network", 3),
        ("vpn", 3),
        ("customer support", 2),
        ("saas", 2),
        ("remote support", 4),
    ],
}

CRITICAL_WEIGHT = 4


# Text cleaning and basic overlap scoring.
# This file is the simple resume-vs-job matcher that later scoring code in
# `main.py` uses as one input.
def normalize_text(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def soften_obvious_support_gaps(track_name, job_text, missing, missing_critical):
    """Downgrade a few support-only gaps when the title already proves the lane.

    Some support postings use thin descriptions and never repeat phrases like
    `technical support` or `ticketing` even though the title clearly says the
    role is help desk, support, or IT operations work. In this project, those
    postings were getting punished twice:
    - once because the title already carries the lane
    - again because the description did not repeat the same support wording

    This helper keeps the missing terms visible for honesty, but stops those
    two phrases from counting as critical blockers when the role is obviously
    a support bridge from the title itself.
    """
    if track_name != "it_support":
        return missing_critical

    obvious_support_title = re.search(
        r"\b(help ?desk|service ?desk|desktop support|it support|technical support|support engineer|support specialist|support analyst|systems support|application support|it operations?|technician)\b",
        job_text,
    )
    if not obvious_support_title:
        return missing_critical

    # When the title already proves this is a support/help-desk lane, these
    # phrases should not count as "critical misses" just because the resume
    # uses adjacent wording instead of the exact same title phrase.
    softened_terms = {
        "technical support",
        "ticketing",
        "help desk",
        "service desk",
        "desktop support",
        "it support",
    }
    return [term for term in missing_critical if term not in softened_terms]


def soften_obvious_cyber_analyst_gaps(track_name, job_text, missing, missing_critical):
    """Downgrade a few tool-only gaps for analyst-style cyber bridge roles.

    Some cyber bridge postings are clearly analyst or advisor work, but they
    still mention one defensive tool family like EDR. In this project, that
    single tool mention was being treated as a hard blocker even when the rest
    of the posting already showed a strong analyst / IR / monitoring path.

    This helper keeps the missing term visible in `missing`, but stops a small
    tool-only set from counting as critical when the title and description
    already make the role look like an analyst-style bridge rather than a deep
    security-engineering path.
    """
    if track_name != "cyber":
        return missing_critical

    obvious_analyst_title = re.search(
        r"\b(security analyst|cyber(?:security)? analyst|cyber advisor|cybersecurity advisor|security operations analyst|incident response analyst|threat analyst|soc analyst)\b",
        job_text,
    )
    if not obvious_analyst_title:
        return missing_critical

    analyst_signal_count = sum(
        1
        for term in [
            "incident response",
            "investigation",
            "monitoring",
            "vulnerability",
            "threat",
            "security operations",
            "siem",
            "sentinel",
            "splunk",
            "network",
        ]
        if term in job_text
    )
    if analyst_signal_count < 3:
        return missing_critical

    softened_terms = {
        "edr",
        "xdr",
        "defender",
        "microsoft defender",
    }

    # Some analyst postings repeat the lane itself as a skill, for example
    # `security operations` inside a `Security Operations Analyst` role. In
    # this project, that was counting like a missing hard skill even though it
    # mostly describes the function of the team, not a specific tool gap.
    softened_terms.add("security operations")

    # DFIR / IR analyst roles often mention `threat hunting` as one item in a
    # larger investigation workflow. For analyst-style bridge roles, that term
    # should not count as a critical blocker when the posting already shows
    # strong incident-response or forensic work elsewhere.
    if re.search(r"\b(incident response|forensics|dfir)\b", job_text):
        softened_terms.add("threat hunting")

    return [term for term in missing_critical if term not in softened_terms]


def score_job(resume_text, job_text, track_name):
    resume_text = normalize_text(resume_text)
    job_text = normalize_text(job_text)

    skills = TRACK_SKILLS[track_name]
    relevant_weight = 0
    matched_weight = 0
    matched = []
    missing = []
    matched_critical = []
    missing_critical = []

    # This only scores terms that the job posting actually asks for.
    # That makes `relevant_weight` the weight of this job's requirements, and
    # `matched_weight` the part your resume already covers.
    for term, weight in skills:
        if term not in job_text:
            continue

        relevant_weight += weight

        if term in resume_text:
            matched.append(term)
            matched_weight += weight
            if weight >= CRITICAL_WEIGHT:
                matched_critical.append(term)
        else:
            missing.append(term)
            if weight >= CRITICAL_WEIGHT:
                missing_critical.append(term)

    # This keeps thin support postings from being treated like they lack core
    # support workflow evidence when the title already clearly says they are
    # support or IT bridge roles.
    missing_critical = soften_obvious_support_gaps(track_name, job_text, missing, missing_critical)

    # This keeps analyst-style cyber bridge roles from getting crushed by one
    # tool-family gap when the rest of the posting already points to analyst,
    # monitoring, or incident-response work.
    missing_critical = soften_obvious_cyber_analyst_gaps(track_name, job_text, missing, missing_critical)

    # This turns the weighted overlap into one percentage the rest of the project uses.
    # If the posting contains none of the tracked terms, the score stays at 0.
    match_percent = int(round((matched_weight / relevant_weight) * 100)) if relevant_weight else 0

    if match_percent >= 75:
        decision = "APPLY"
        meaning = "Strong resume overlap for this track."
    elif match_percent >= 50:
        decision = "MAYBE"
        meaning = "Moderate resume overlap for this track."
    else:
        decision = "SKIP"
        meaning = "Weak resume overlap for this track."

    return {
        "matched": matched,
        "missing": missing,
        "matched_critical": matched_critical,
        "missing_critical": missing_critical,
        "matched_weight": matched_weight,
        "relevant_weight": relevant_weight,
        "match_percent": match_percent,
        "decision": decision,
        "meaning": meaning,
    }
