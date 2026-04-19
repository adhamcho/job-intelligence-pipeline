"""Title and gate rules for the job tool.

This file decides what kind of role a title looks like and whether a cyber role
is realistic enough to keep. It is the rulebook for SOC, cyber-analyst, and IT
bridge title decisions.
"""

import re


def has_cyber_anchor(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsecurity\b",
            r"\bsoc\b",
            r"\bcyber(?:security)?\b",
            r"\bincident response\b",
            r"\bthreat\b",
            r"\bdetection\b",
            r"\bsecurity operations?\b",
            r"\bdefensive security\b",
            r"\bgrc\b",
            r"\biam\b",
        ],
    )


def is_cyber_analyst_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsoc analyst\b",
            r"\bnoc analyst\b",
            r"\bnetwork operations? analyst\b",
            r"\bsecurity operations analyst\b",
            r"\bsecurity analyst\b",
            r"\bcyber(?:security)? analyst\b",
            r"\bcyber advisor\b",
            r"\bcybersecurity advisor\b",
            r"\bassociate cybersecurity advisor\b",
            r"\bdata protection analyst\b",
            r"\biam analyst\b",
            r"\bidentity analyst\b",
            r"\baccess (?:control|management|administration)? ?analyst\b",
            r"\brisk analyst\b",
            r"\bincident response analyst\b",
            r"\bincident responder\b",
            r"\bmonitoring analyst\b",
            r"\bdetection (?:and|&) response analyst\b",
            r"\bthreat (?:intel(?:ligence)?|detection|response)? ?analyst\b",
            r"\bapplication security analyst\b",
            r"\bproduct security analyst\b",
            r"\bcloud security analyst\b",
        ],
    )


def is_cyber_investigator_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsecurity investigations? analyst\b",
            r"\bthreat investigator\b",
            r"\bsecurity investigator\b",
            r"\bcyber(?:security)? investigator\b",
        ],
    )


def is_engineering_heavy_cyber_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsoftware engineer\b",
            r"\bsecurity engineer\b",
            r"\bapplication security engineer\b",
            r"\bproduct security engineer\b",
            r"\binfrastructure security engineer\b",
            r"\bcloud security engineer\b",
            r"\bsecurity software engineer\b",
        ],
    )


def is_specialized_security_engineering_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bapplication security\b",
            r"\bproduct security\b",
            r"\binfrastructure security\b",
            r"\bcloud security\b",
            r"\bbrowser security\b",
            r"\bblockchain security\b",
            r"\bsecurity partnerships\b",
            r"\boffensive security\b",
            r"\bpenetration(?: |-)?testing\b",
            r"\bred team\b",
        ],
    )


def is_blue_team_cyber_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsoc\b",
            r"\bsecurity operations?\b",
            r"\bincident response\b",
            r"\bdetection\b",
            r"\bresponse\b",
            r"\bthreat detection\b",
            r"\bthreat hunting\b",
            r"\bsecurity monitoring\b",
        ],
    )


def is_soc_focused_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsoc\b",
            r"\bsecurity operations?\b",
            r"\bincident response\b",
            r"\bdetection\b",
            r"\bresponse\b",
            r"\bthreat (?:detection|hunting|response)\b",
            r"\bmonitoring\b",
        ],
    )


def has_excluded_cyber_title_terms(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsales\b",
            r"\bcurriculum\b",
            r"\brecruit(?:er|ing)\b",
            r"\bproduct manager\b",
            r"\bprogram manager\b",
            r"\bmarketing\b",
            r"\bcustomer success\b",
            r"\baccount executive\b",
            r"\bsolutions consultant\b",
            r"\btechnical writer\b",
            r"\bgrc\b",
            r"\bcompliance\b",
            r"\baudit\b",
            r"\brisk\b",
        ],
    )


def is_target_soc_role_title(title, *, ctx):
    if not has_cyber_anchor(title, ctx=ctx):
        return False
    if has_excluded_cyber_title_terms(title, ctx=ctx):
        return False
    if is_specialized_security_engineering_title(title, ctx=ctx):
        return False
    if re.search(r"\bsoc analyst\b", title) or re.search(r"\bsecurity operations analyst\b", title):
        return True
    if is_engineering_heavy_cyber_title(title, ctx=ctx):
        return is_soc_focused_title(title, ctx=ctx)
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsoc\b",
            r"\bmdr\b",
            r"\bmanaged detection (?:and|&) response\b",
            r"\bnoc analyst\b",
            r"\bnetwork operations? analyst\b",
            r"\bsecurity operations?\b",
            r"\bsecurity operations? (?:specialist|associate)\b",
            r"\bthreat operations? (?:analyst|specialist|associate)\b",
            r"\bsecurity monitoring\b",
            r"\bresponse\b",
            r"\bdetection\b",
            r"\bincident response\b",
            r"\bincident responder\b",
            r"\bthreat detection\b",
            r"\bthreat hunting\b",
            r"\bthreat monitoring\b",
            r"\bmonitoring\b",
        ],
    )


def is_target_cyber_analyst_role_title(title, *, ctx):
    if not has_cyber_anchor(title, ctx=ctx):
        return False
    if ctx.matches_any_pattern(
        title,
        [
            r"\bcyber(?:security)? analyst\b",
            r"\bapplication security analyst\b",
            r"\bproduct security analyst\b",
            r"\bcloud security analyst\b",
            r"\bcyber advisor\b",
            r"\bcybersecurity advisor\b",
        ],
    ):
        return True
    if has_excluded_cyber_title_terms(title, ctx=ctx):
        return False
    if is_specialized_security_engineering_title(title, ctx=ctx):
        return False
    if is_cyber_analyst_title(title, ctx=ctx) or is_cyber_investigator_title(title, ctx=ctx):
        return True
    if is_engineering_heavy_cyber_title(title, ctx=ctx):
        return is_blue_team_cyber_title(title, ctx=ctx)
    return ctx.matches_any_pattern(
        title,
        [
            r"\bsecurity analyst\b",
            r"\bcyber(?:security)? analyst\b",
            r"\bsecurity operations? (?:specialist|associate)\b",
            r"\bthreat operations? (?:analyst|specialist|associate)\b",
            r"\bthreat analyst\b",
            r"\bfraud (?:analyst|operations?|investigations?)\b",
            r"\bvulnerability analyst\b",
            r"\bincident response\b",
            r"\bdetection\b",
            r"\bresponse\b",
            r"\bsecurity specialist\b",
            r"\bcybersecurity advisor\b",
            r"\bcyber advisor\b",
            r"\bsecurity operations?\b",
            r"\bsecurity monitoring\b",
            r"\bidentity\b",
            r"\biam\b",
            r"\baccess administration\b",
            r"\baccess management\b",
            r"\baccess analyst\b",
            r"\bidentity analyst\b",
            r"\brisk analyst\b",
            r"\btrust(?: |-)and(?: |-)safety\b",
            r"\btrust(?: |-)and(?: |-)safety analyst\b",
            r"\btrust(?: |-)and(?: |-)safety specialist\b",
            r"\bassociate\b",
        ],
    )


def is_target_it_role_title(title, *, ctx):
    if ctx.matches_any_pattern(
        title,
        [
            r"\bmarketing\b",
            r"\bsales\b",
            r"\bsoftware engineer\b",
            r"\bmachine learning\b",
            r"\bproduct manager\b",
            r"\bforward deployed engineer\b",
            r"\bdeveloper\b",
            r"\bsolutions engineer\b",
            r"\bcustomer support\b",
        ],
    ):
        return False
    return ctx.matches_any_pattern(
        title,
        [
            r"\bit support\b",
            r"\bhelp ?desk\b",
            r"\bservice ?desk\b",
            r"\bdesktop support\b",
            r"\btechnical support\b",
            r"\bsupport engineer\b",
            r"\bapplication support engineer\b",
            r"\bsystems support\b",
            r"\bsystems support analyst\b",
            r"\binternal it\b",
            r"\bend user support\b",
            r"\bapplication support\b",
            r"\bit operations?\b",
            r"\bit operations analyst\b",
            r"\btechnical operations\b",
            r"\bit administrator\b",
            r"\bsystems administrator\b",
            r"\bsystems admin\b",
            r"\bit specialist\b",
            r"\bit analyst\b",
            r"\bsupport specialist\b",
            r"\bsupport analyst\b",
            r"\bit support technician\b",
            r"\btechnician\b",
            r"\bsaas administrator\b",
            r"\bapplication specialist\b",
        ],
    )


def is_implicit_aggregator_it_role(job, *, ctx):
    if str(job.get("source_type") or "") != "aggregator":
        return False
    if not ctx.is_us_location(job):
        return False

    title = job.get("title_lc") or ""
    description = job.get("description_lc") or ""

    if ctx.matches_any_pattern(
        title,
        [
            r"\bcustomer support specialist\b",
            r"\bcustomer(?: &| and)? technical support analyst\b",
            r"\bcustomer experience engineer\b",
            r"\bcustomer advocate\b",
            r"\btechnical support representative\b",
            r"\bcommunity(?: &| and)? support specialist\b",
            r"\bsupport specialist\b",
            r"\bsupport analyst\b",
            r"\bplatform support\b",
            r"\bproduct support analyst\b",
            r"\btechnical operations(?: assistant)?\b",
            r"\boperations specialist\b",
            r"\boperations assistant\b",
            r"\bfield support technician\b",
            r"\bit/?av support coordinator\b",
            r"\bexperience specialist\b",
        ],
    ):
        return True

    if "support" in title and ctx.contains_any(
        description,
        [
            "technical",
            "troubleshooting",
            "ticket",
            "saas",
            "product",
            "platform",
            "incident",
            "escalation",
            "systems",
        ],
    ):
        return True

    return False


def has_aggregator_support_title(title, *, ctx):
    return ctx.matches_any_pattern(
        title or "",
        [
            r"\btechnical support\b",
            r"\bsupport engineer\b",
            r"\bsupport specialist\b",
            r"\bsupport analyst\b",
            r"\bplatform support\b",
            r"\bproduct support\b",
            r"\bwordpress support\b",
            r"\bhelp ?desk\b",
            r"\bservice ?desk\b",
            r"\bapplication support\b",
            r"\bsystems support\b",
        ],
    )


def get_path_tier_label(job, track_name, *, ctx):
    title = job["title_lc"]
    if ctx.is_soc_track(track_name):
        if ctx.matches_any_pattern(
            title,
            [
                r"\bsoc analyst\b",
                r"\bnoc analyst\b",
                r"\bsecurity operations analyst\b",
                r"\bincident response analyst\b",
                r"\bincident responder\b",
                r"\bmonitoring analyst\b",
                r"\bdetection (?:and|&) response analyst\b",
            ],
        ):
            return "Tier A"
        return "Tier A (Adjacency)"
    if ctx.is_it_track(track_name):
        return "Tier B"
    return "Tier C"


def has_disqualifying_cyber_seniority(title, *, ctx):
    return bool(re.search(r"\b(manager|director|head|vp|principal|staff|lead|senior|sr\.?)\b", title))


def fails_entry_level_cyber_gate(job, resume_text, track_name="", *, ctx):
    title = job["title_lc"]
    text = job["combined_lc"]
    resume_text = resume_text.lower()
    years_required = ctx.extract_required_years(text)

    if ctx.is_cyber_analyst_track(track_name):
        if ctx.matches_any_pattern(
            title,
            [
                r"\bcyber(?:security)? analyst\b",
                r"\bcyber advisor\b",
                r"\bcybersecurity advisor\b",
                r"\bassociate cybersecurity advisor\b",
                r"\bsoc analyst\b",
                r"\bsoc siem analyst\b",
                r"\bsecurity operations analyst\b",
                r"\biam analyst\b",
                r"\bidentity analyst\b",
                r"\baccess (?:control|management|administration)? ?analyst\b",
            ],
        ):
            if years_required <= 2 and not re.search(r"\b(manager|director|head|vp|principal|staff|lead|senior|sr\.?)\b", title):
                return False

    if has_disqualifying_cyber_seniority(title, ctx=ctx):
        return True
    if years_required >= 4:
        return True
    if "clearance" in text and "clearance" not in resume_text:
        return True
    return False


def has_junior_title_signal(title, *, ctx):
    return ctx.matches_any_pattern(
        title,
        [
            r"\bentry(?:[- ]level)?\b",
            r"\bjunior\b",
            r"\bjr\.?\b",
            r"\bnew grad\b",
            r"\bintern\b",
            r"\bapprentice\b",
            r"\bassociate\b",
        ],
    )


def compute_title_fit_score(job, track_name, *, ctx):
    title = job["title_lc"]
    implicit_aggregator_it = is_implicit_aggregator_it_role(job, ctx=ctx)
    score = 0
    reasons = []
    junior_title = has_junior_title_signal(title, ctx=ctx)

    def add(condition, points, label):
        nonlocal score
        if condition:
            score += points
            reasons.append(label)

    if ctx.is_soc_track(track_name):
        has_security_anchor = has_cyber_anchor(title, ctx=ctx)

        if re.search(r"\bsoc analyst\b", title):
            add(True, 62, "soc analyst title")
        if re.search(r"\bnoc analyst\b", title):
            add(True, 54, "noc analyst title")
        if re.search(r"\bnetwork operations? analyst\b", title):
            add(True, 46, "network operations analyst")
        if re.search(r"\bsecurity operations analyst\b", title):
            add(True, 58, "security operations analyst")
        if ctx.matches_any_pattern(
            title,
            [
                r"\bincident response analyst\b",
                r"\bincident responder\b",
                r"\bmonitoring analyst\b",
                r"\bdetection (?:and|&) response analyst\b",
                r"\bthreat (?:intel(?:ligence)?|detection|response)? ?analyst\b",
                r"\bthreat operations? (?:analyst|specialist|associate)\b",
                r"\bmanaged detection (?:and|&) response(?: analyst)?\b",
                r"\bmdr analyst\b",
                r"\bsecurity operations? (?:specialist|associate)\b",
            ],
        ):
            add(True, 52, "response analyst title")
        if re.search(r"\bsoc engineer\b", title):
            add(True, 28, "soc engineer title")
        if is_soc_focused_title(title, ctx=ctx) and re.search(r"\bengineer\b", title):
            add(True, 18, "blue-team engineer title")

        if re.search(r"\bsecurity\b", title):
            add(True, 18, "security title")
        if re.search(r"\bsoc\b", title):
            add(True, 36, "soc title")
        if re.search(r"\bcyber(?:security)?\b", title):
            add(True, 18, "cyber title")
        if re.search(r"\bincident response\b", title):
            add(True, 22, "incident response title")
        if re.search(r"\bthreat\b", title):
            add(True, 14, "threat title")
        if re.search(r"\bdetection\b", title):
            add(True, 20, "detection title")
        if ctx.matches_any_pattern(
            title,
            [
                r"\bapplication security\b",
                r"\bproduct security\b",
                r"\bcloud security\b",
                r"\binfrastructure security\b",
                r"\boffensive security\b",
                r"\bdetection\b",
            ],
        ):
            add(True, 8, "security specialty")

        if has_security_anchor:
            add(re.search(r"\banalyst\b", title), 24, "analyst title")
            add(re.search(r"\bengineer\b", title) and is_soc_focused_title(title, ctx=ctx), 8, "engineer title")

        if junior_title and has_security_anchor:
            add(True, 24, "junior title")

        if ctx.matches_any_pattern(title, [r"\bsecurity analyst\b", r"\bcyber(?:security)? analyst\b"]):
            add(True, 12, "analyst adjacency")

    if ctx.is_cyber_analyst_track(track_name):
        has_security_anchor = has_cyber_anchor(title, ctx=ctx)

        if ctx.matches_any_pattern(title, [r"\bsecurity analyst\b", r"\bcyber(?:security)? analyst\b"]):
            add(True, 62, "security analyst title")
        if ctx.matches_any_pattern(title, [r"\bcyber advisor\b", r"\bcybersecurity advisor\b", r"\bassociate cybersecurity advisor\b"]):
            add(True, 38, "cyber advisor bridge")
        if ctx.matches_any_pattern(title, [r"\biam analyst\b", r"\bidentity analyst\b", r"\baccess (?:control|management|administration)? ?analyst\b"]):
            add(True, 44, "identity or access analyst")
        if re.search(r"\brisk analyst\b", title):
            add(True, 32, "risk analyst bridge")
        if re.search(r"\bthreat (?:intel(?:ligence)?|detection|response)? ?analyst\b", title):
            add(True, 54, "threat analyst title")
        if ctx.matches_any_pattern(
            title,
            [
                r"\bthreat operations? (?:analyst|specialist|associate)\b",
                r"\bsecurity operations? (?:specialist|associate)\b",
            ],
        ):
            add(True, 38, "security operations bridge")
        if ctx.matches_any_pattern(
            title,
            [
                r"\btrust(?: |-)and(?: |-)safety analyst\b",
                r"\btrust(?: |-)and(?: |-)safety specialist\b",
                r"\bfraud (?:analyst|operations?|investigations?)\b",
            ],
        ):
            add(True, 34, "trust, fraud, or investigations bridge")
        if re.search(r"\bvulnerability analyst\b", title):
            add(True, 50, "vulnerability analyst title")
        if is_cyber_investigator_title(title, ctx=ctx):
            add(True, 42, "investigations title")
        if re.search(r"\bincident response analyst\b", title):
            add(True, 46, "incident response analyst")
        if re.search(r"\bsecurity operations analyst\b", title):
            add(True, 40, "security operations analyst")

        if re.search(r"\bsecurity\b", title):
            add(True, 18, "security title")
        if re.search(r"\bcyber(?:security)?\b", title):
            add(True, 18, "cyber title")
        if re.search(r"\bthreat\b", title):
            add(True, 16, "threat title")
        if re.search(r"\bvulnerability\b", title):
            add(True, 14, "vulnerability title")
        if re.search(r"\bincident response\b", title):
            add(True, 20, "incident response title")

        if has_security_anchor:
            add(re.search(r"\banalyst\b", title), 24, "analyst title")
            add(is_cyber_investigator_title(title, ctx=ctx), 10, "investigator title")

        if junior_title and has_security_anchor:
            add(True, 18, "junior title")

        if re.search(r"\bsoc engineer\b", title):
            add(True, 10, "soc bridge title")
        elif is_blue_team_cyber_title(title, ctx=ctx) and re.search(r"\bengineer\b", title):
            add(True, 6, "blue-team engineer adjacency")

    if ctx.is_it_track(track_name):
        add(re.search(r"\bit support\b", title), 45, "it support title")
        add(re.search(r"\bhelp ?desk\b", title), 45, "help desk title")
        add(re.search(r"\bservice ?desk\b", title), 45, "service desk title")
        add(re.search(r"\bdesktop support\b", title), 45, "desktop support title")
        add(re.search(r"\btechnical support\b", title), 45, "technical support title")
        add(re.search(r"\bsupport engineer\b", title), 38, "support engineer title")
        add(re.search(r"\bapplication support engineer\b", title), 40, "application support engineer title")
        add(re.search(r"\bsystems support\b", title), 38, "systems support title")
        add(re.search(r"\bsystems support analyst\b", title), 38, "systems support analyst")
        add(re.search(r"\binternal it\b", title), 42, "internal it title")
        add(re.search(r"\bend user support\b", title), 35, "end user support title")
        add(re.search(r"\bapplication support\b", title), 35, "application support title")
        add(re.search(r"\bit operations?\b", title), 34, "it operations title")
        add(re.search(r"\bit operations analyst\b", title), 34, "it operations analyst")
        add(re.search(r"\btechnical operations\b", title), 28, "technical operations title")
        add(re.search(r"\bsystems administrator\b", title), 30, "systems administrator title")
        add(re.search(r"\bsystems admin\b", title), 30, "systems admin title")
        add(re.search(r"\bsaas administrator\b", title), 28, "saas administrator title")
        add(re.search(r"\bdesktop technician\b", title), 30, "desktop technician title")
        add(re.search(r"\bfield support\b", title), 25, "field support title")
        add(re.search(r"\btechnician\b", title), 24, "technician title")
        add(re.search(r"\bsupport specialist\b", title), 22, "support specialist title")
        add(re.search(r"\bsupport analyst\b", title), 24, "support analyst title")
        add(re.search(r"\bit specialist\b", title), 28, "it specialist title")
        add(re.search(r"\bit analyst\b", title), 24, "it analyst title")
        add(re.search(r"\bapplication specialist\b", title), 24, "application specialist title")
        add(
            re.search(r"\bproduct support\b", title) and not re.search(r"\bengineer\b", title),
            -18,
            "product support title",
        )
        add(
            re.search(r"\bproduct support engineer\b", title),
            26,
            "product support engineer title",
        )
        if implicit_aggregator_it:
            add(re.search(r"\bcustomer support\b", title), -4, "messy customer support title")
            add(re.search(r"\bcustomer(?: &| and)? technical support analyst\b", title), 18, "customer technical support analyst")
            add(re.search(r"\bcommunity(?: &| and)? support specialist\b", title), 12, "community support specialist bridge")
            add(re.search(r"\boperations specialist\b", title), 14, "operations specialist bridge")
        else:
            add(re.search(r"\bcustomer support\b", title), -20, "customer support title")

    return min(score, 100), reasons
