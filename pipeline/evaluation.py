"""Early scoring and realism helpers for the job tool.

This file holds the lower-level judgment helpers that decide how hard a job
looks, how much it helps the security path, and whether a posting secretly
asks for more experience than its title suggests.
"""

import re


def compute_execution_score(job, track_name, resume_text, fit_result, *, ctx):
    """Score how hard the real day-to-day work looks for the current resume."""
    title = job["title_lc"]
    text = job["combined_lc"]
    resume_text = resume_text.lower()
    skill_profile = ctx.get_skill_profile(track_name)
    blue_team_engineering = ctx.is_cyber_track(track_name) and ctx.is_blue_team_cyber_title(title)
    cyber_analyst_style = ctx.is_cyber_track(track_name) and not re.search(r"\bengineer\b", title)

    score = 62
    notes = []
    risks = []

    def add(points, note=None, risk=None):
        nonlocal score
        score += points
        if note:
            notes.append(note)
        if risk:
            risks.append(risk)

    backed_terms = ctx.PROJECT_BACKED_TERMS.get(skill_profile, [])
    backed_overlap = ctx.count_matching_terms(text, [term for term in backed_terms if term in resume_text])
    if backed_overlap >= 3:
        add(16, "project-backed overlap")
    elif backed_overlap >= 1:
        add(8, "direct tool overlap")

    depth_terms = list(ctx.EXECUTION_DEPTH_TERMS.get(skill_profile, []))
    # Analyst-style cyber roles often use broad ownership or scale language
    # without actually demanding engineering-style execution depth. Keep those
    # terms as signals for real engineering paths, but do not let them
    # over-penalize analyst / MDR / IR titles in this codebase.
    if cyber_analyst_style:
        depth_terms = [
            term
            for term in depth_terms
            if term not in {"ownership", "leadership", "scalable", "large-scale"}
        ]
    depth_hits = ctx.count_matching_terms(text, depth_terms)
    if depth_hits >= 2:
        add(
            -8 if blue_team_engineering else -14,
            "execution depth expected",
            "Execution depth looks higher than current resume evidence",
        )
    elif depth_hits == 1:
        add(-7, "independent execution expected", "Likely less handholding than the post suggests")

    if ctx.is_cyber_track(track_name):
        if re.search(r"\bengineer\b", title):
            add(
                -12 if blue_team_engineering else -18,
                "engineering depth",
                "Engineering-style execution may be screened heavily",
            )
        if ctx.matches_any_pattern(
            text,
            [
                r"\b(go|java|c\+\+|rust)\b",
                r"\bdistributed systems?\b",
                r"\bbackend systems?\b",
                r"\bplatform engineering\b",
            ],
        ):
            add(
                -10 if blue_team_engineering else -16,
                "coding depth",
                "Coding depth likely exceeds current evidence",
            )
        if ctx.contains_any(text, ["alert triage", "siem", "sentinel", "splunk", "log analysis", "monitoring"]):
            add(8, "hands-on blue-team overlap")
        if (
            ctx.contains_any(text, ["software engineering", "distributed systems", "backend"])
            and re.search(r"\bengineer\b", title)
            and not re.search(r"\bsoc\b", title)
        ):
            add(-10, "code-heavy interview risk", "Interview may focus on deeper coding than the resume shows")

        if ctx.is_soc_track(track_name) and re.search(r"\bengineer\b", title):
            add(-8, "soc lane prefers analyst-style execution", "SOC lane is closer to analyst work than engineering loops")

    if ctx.is_it_track(track_name):
        if ctx.contains_any(text, ["troubleshooting", "ticketing", "windows", "technical support"]):
            add(10, "support workflow overlap")

    if fit_result["resume_result"]["missing_critical"]:
        add(
            -min(10, 5 * len(fit_result["resume_result"]["missing_critical"])),
            "critical gaps",
            "Missing core tools or workflows the role emphasizes",
        )

    return {
        "execution_score": max(0, min(score, 100)),
        "execution_notes": notes,
        "execution_risks": risks,
    }


def compute_trajectory_score(job, track_name, fit_result, *, ctx):
    """Score how much this role moves the user toward security work later."""
    text = job["combined_lc"]
    title = job["title_lc"]
    implicit_aggregator_it = ctx.is_implicit_aggregator_it_role(job)
    score = 45
    notes = []

    def add(points, note=None):
        nonlocal score
        score += points
        if note:
            notes.append(note)

    if ctx.contains_any(
        text,
        [
            "logs",
            "log analysis",
            "monitoring",
            "alerts",
            "triage",
            "incident",
            "response",
            "investigation",
            "ticket",
            "escalation",
            "troubleshoot",
            "troubleshooting",
        ],
    ):
        add(12, "logs, incidents, or troubleshooting exposure")

    if ctx.contains_any(
        text,
        [
            "siem",
            "splunk",
            "sentinel",
            "defender",
            "edr",
            "iam",
            "identity",
            "access",
            "google workspace",
            "okta",
            "slack",
            "jira",
            "zoom",
            "saas applications",
        ],
    ):
        add(12, "security or admin tooling exposure")

    if ctx.contains_any(
        text,
        [
            "systems",
            "infrastructure",
            "network",
            "application support",
            "technical support",
            "it operations",
            "service desk",
            "endpoint",
            "desktop support",
        ],
    ):
        add(10, "systems access and support depth")

    if ctx.contains_any(
        text,
        [
            "customer support",
            "customer happiness",
            "account management",
            "sales",
            "renewals",
            "upsell",
            "billing support",
        ],
    ):
        add(-20, "customer-facing without enough technical depth")

    if ctx.matches_any_pattern(
        title,
        [
            r"\bsoc analyst\b",
            r"\bnoc analyst\b",
            r"\bincident response\b",
            r"\bincident responder\b",
            r"\bsecurity operations analyst\b",
        ],
    ):
        add(18, "closest direct path to Tier A work")
    elif ctx.matches_any_pattern(
        title,
        [
            r"\btechnical support\b",
            r"\bapplication support\b",
            r"\bsystems support\b",
            r"\bservice desk\b",
            r"\bit operations?\b",
            r"\bsaas administrator\b",
            r"\bsupport engineer\b",
        ],
    ):
        add(14, "strong Tier B bridge path")
    elif ctx.matches_any_pattern(
        title,
        [
            r"\biam\b",
            r"\bidentity\b",
            r"\baccess\b",
            r"\bcyber advisor\b",
            r"\bcybersecurity advisor\b",
            r"\brisk analyst\b",
            r"\bapplication security analyst\b",
            r"\bproduct security analyst\b",
            r"\bcloud security analyst\b",
            r"\bvulnerability analyst\b",
        ],
    ):
        add(10, "selective Tier C bridge path")

    if ctx.is_soc_track(track_name) and "engineer" in title and not re.search(r"\bsoc engineer\b", title):
        add(-12, "engineer-heavy path is weaker than analyst path")

    if ctx.is_it_track(track_name) and ctx.matches_any_pattern(title, [r"\bcustomer support\b", r"\bproduct support\b"]):
        if implicit_aggregator_it:
            add(-3, "messy support framing is weaker than technical support but still viable")
        else:
            add(-12, "bridge value is weaker than technical support")

    if fit_result["skill_match_score"] >= 75:
        add(6, "your current evidence supports the move")
    elif fit_result["skill_match_score"] < 45:
        add(-6, "bridge exists but your evidence is still thin")

    return {
        "trajectory_score": max(0, min(score, 100)),
        "trajectory_notes": notes,
    }


def compute_target_signal(job, *, ctx):
    """Score how directly the job work lines up with security goals."""
    title = job["title_lc"]
    text = job["combined_lc"]
    tags = set(job.get("company_tags", []) or ())
    implicit_aggregator_it = ctx.is_implicit_aggregator_it_role(job)
    score = 0
    notes = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if "mssp" in tags:
        add(18, "mssp or mdr source")
    if "security" in tags:
        add(10, "security company")
    if "cloud" in tags or "saas" in tags:
        add(6, "cloud or saas environment")
    if {"msp", "it-services", "service-desk", "staffing"} & tags:
        add(6, "entry-friendly it service environment")
    elif {"enterprise", "insurance", "gov-adjacent", "healthcare"} & tags:
        add(4, "boring enterprise environment")

    if ctx.matches_any_pattern(
        title,
        [
            r"\bsoc analyst\b",
            r"\bsecurity operations analyst\b",
            r"\bsecurity operations? (?:specialist|associate)\b",
            r"\bnoc analyst\b",
            r"\bcyber fusion analyst\b",
            r"\bincident response\b",
            r"\bincident responder\b",
            r"\bmanaged detection (?:and|&) response\b",
            r"\bmdr\b",
            r"\bthreat operations? (?:analyst|specialist|associate)\b",
            r"\bthreat detection\b",
            r"\bthreat monitoring\b",
            r"\bsecurity monitoring\b",
        ],
    ):
        add(20, "direct soc-adjacent title")
    elif ctx.matches_any_pattern(
        title,
        [
            r"\btechnical support\b",
            r"\bapplication support\b",
            r"\bsystems support\b",
            r"\bsupport engineer\b",
            r"\bit operations?\b",
            r"\bsaas administrator\b",
        ],
    ):
        if {"security", "cloud", "saas"} & tags:
            add(16, "support role in a security or cloud environment")
        else:
            add(8, "generic bridge support role")
    elif ctx.matches_any_pattern(
        title,
        [
            r"\biam\b",
            r"\bidentity\b",
            r"\baccess\b",
            r"\bcyber advisor\b",
            r"\bcybersecurity advisor\b",
            r"\brisk analyst\b",
            r"\btrust(?: |-)and(?: |-)safety\b",
            r"\bfraud (?:analyst|operations?|investigations?)\b",
            r"\bapplication security analyst\b",
            r"\bproduct security analyst\b",
            r"\bcloud security analyst\b",
            r"\bvulnerability analyst\b",
        ],
    ):
        add(14, "adjacent cyber bridge")

    if ctx.contains_any(
        text,
        [
            "siem",
            "splunk",
            "sentinel",
            "alerts",
            "monitoring",
            "incident response",
            "investigation",
            "ticketing",
            "escalation",
        ],
    ):
        add(8, "ops and detection workflow exposure")

    if implicit_aggregator_it and ctx.matches_any_pattern(
        title,
        [r"\bcustomer support\b", r"\bcommunity(?: &| and)? support\b", r"\bsupport specialist\b"],
    ):
        add(4, "messy support title still looks like a plausible low-competition bridge")
    elif ctx.matches_any_pattern(title, [r"\bcustomer support\b", r"\bproduct support\b"]):
        add(-18, "customer support is weaker than technical operations")

    return {
        "target_signal_score": max(0, min(score, 100)),
        "target_signal_notes": notes,
    }


def extract_required_years(text, *, ctx):
    """Pull a realistic minimum years requirement out of the posting text.

    In this project, a range like "1-4 years" should count like a 1-year floor,
    because the lower end is the minimum ask that matters for entry screening.
    """
    found = []

    range_pattern = r"\b(\d+)\s*[-–]\s*(\d+)\+?\s+years?\b"
    for low, high in re.findall(range_pattern, text):
        found.append(min(int(low), int(high)))

    text_without_ranges = re.sub(range_pattern, " ", text)

    single_value_patterns = [
        r"\b(\d+)\+?\s+years?\b",
        r"\bat least\s+(\d+)\s+years?\b",
        r"\bminimum of\s+(\d+)\s+years?\b",
        r"\b(\d+)\s+years? of experience\b",
    ]

    ignore_context_terms = [
        "anniversary",
        "sabbatical",
        "pto",
        "paid time off",
        "vacation",
        "bonus",
        "benefits",
        "tenure",
    ]

    for pattern in single_value_patterns:
        for match in re.finditer(pattern, text_without_ranges):
            snippet = text_without_ranges[max(0, match.start() - 40) : min(len(text_without_ranges), match.end() + 60)]
            if any(term in snippet for term in ignore_context_terms):
                continue
            found.append(int(match.group(1)))

    realistic_requirements = [years for years in found if years <= 15]
    return max(realistic_requirements) if realistic_requirements else 0


def is_early_career(job, *, ctx):
    """Check whether the title or description clearly signals early-career hiring."""
    title = job["title_lc"]
    text = f"{job['title_lc']} {job['description_lc']}"

    title_terms = [
        "entry",
        "junior",
        "new grad",
        "intern",
        "associate",
        "technician",
        "apprentice",
        "cohort",
    ]
    text_terms = [
        "entry level",
        "early career",
        "recent graduate",
        "new graduate",
    ]

    return any(term in title for term in title_terms) or any(term in text for term in text_terms)


def detect_disguised_mid_level(job, *, ctx):
    """Flag postings that use junior titles but ask for mid-level ownership."""
    title = job["title_lc"]
    text = job["combined_lc"]
    years_required = ctx.extract_required_years(text)
    reasons = []

    if not re.search(r"\banalyst\b|\bassociate\b|\bjunior\b|\bentry\b|\bsoc\b", title):
        return False, reasons

    if years_required >= 3:
        reasons.append(f"{years_required}+ years behind entry-level title")

    if ctx.matches_any_pattern(
        text,
        [
            r"\barchitect\b",
            r"\bstrategy\b",
            r"\bdefine strategy\b",
            r"\blead initiatives?\b",
            r"\blead projects?\b",
            r"\blead cross-functional\b",
            r"\bdrive initiatives?\b",
            r"\bmentor(?:ing)?\b",
        ],
    ):
        reasons.append("mid-level ownership language")

    if re.search(r"\b(senior|lead|principal|staff)\b", title):
        reasons.append("seniority in title")

    return bool(reasons), reasons


def detect_missing_certs(job_text, resume_text, track_name, *, ctx):
    """List cert names that look required, not merely preferred.

    Many postings mention certs in a "nice to have" section. Earlier versions
    of this project treated any cert mention as a real gap, which pushed down
    analyst and bridge roles even when the posting only listed certs as a
    bonus. This helper now checks the wording around each cert mention so only
    requirement-like language counts as a missing cert penalty.
    """
    missing = []
    preferred_words = ("preferred", "bonus", "nice to have", "plus", "a plus")
    required_words = (
        "required",
        "must have",
        "must possess",
        "need",
        "needs",
        "required qualifications",
        "minimum qualifications",
        "minimum requirements",
    )

    for cert in ctx.TRACKS[track_name]["certs"]:
        if cert not in job_text or cert in resume_text:
            continue

        counts_as_required = False
        for match in re.finditer(re.escape(cert), job_text):
            start = max(0, match.start() - 120)
            end = min(len(job_text), match.end() + 120)
            window = job_text[start:end]

            if any(word in window for word in preferred_words):
                continue
            if any(word in window for word in required_words):
                counts_as_required = True
                break

        if counts_as_required:
            missing.append(cert)

    return missing
