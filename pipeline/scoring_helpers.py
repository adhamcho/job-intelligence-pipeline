"""Later-stage scoring helpers for the job tool.

This file holds the scoring functions that combine earlier signals into
practical output scores like entry viability, response likelihood, ROI,
and the final decision label.
"""

import re


def compute_entry_viability_score(
    job,
    track_name,
    fit_result,
    acceptance_result,
    execution_result,
    trajectory_result,
    target_signal_result,
    narrative_result,
    stepping_stone_label,
    *,
    ctx,
):
    tags = set(acceptance_result.get("company_tags", []) or ())
    title = job.get("title_lc") or ""
    implicit_aggregator_it = ctx.is_implicit_aggregator_it_role(job)
    score = int(
        round(
            (acceptance_result["acceptance_score"] * 0.38)
            + (trajectory_result["trajectory_score"] * 0.22)
            + (target_signal_result["target_signal_score"] * 0.14)
            + (fit_result["fit_score"] * 0.10)
            + (execution_result["execution_score"] * 0.08)
            + (narrative_result["narrative_score"] * 0.08)
        )
    )
    notes = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if stepping_stone_label == "Closest to SOC":
        add(10, "closest available path into security operations")
    elif stepping_stone_label == "Adjacent analyst bridge":
        add(8, "adjacent analyst bridge with believable path in")
    elif stepping_stone_label == "Entry via support":
        add(8, "support role that can realistically get you inside")
    elif stepping_stone_label == "IT bridge":
        add(5, "solid bridge role even if the title is not glamorous")

    if {"mssp", "it-services", "msp", "service-desk", "staffing"} & tags:
        add(8, "boring but entry-friendly hiring ecosystem")
    elif {"enterprise", "insurance", "gov-adjacent", "healthcare"} & tags:
        add(5, "boring-enterprise ecosystem is often more viable than prestige tech")

    if {"prestige", "brand-magnet", "consumer"} & tags:
        add(-6, "prestige or consumer brand signal hurts practical entry odds")

    if ctx.is_priority_queue_location(job):
        add(8, "preferred location or remote match")
    elif ctx.is_us_location(job):
        add(2, "us-based even if not in the ideal geography")

    target_signal = target_signal_result["target_signal_score"]
    if target_signal >= 30:
        add(8, "role has direct security or operations signal beyond pure viability")
    elif target_signal >= 18:
        add(4, "role has some direct ops or security signal")
    elif target_signal <= 8:
        add(-10, "role is viable but the direct security signal is still weak")

    years_required = acceptance_result.get("years_required", 0)
    if years_required == 0:
        add(4, "no explicit years barrier")
    elif years_required <= 2:
        add(2, "years requirement still fits an early-career shot")
    elif years_required >= 3:
        add(-12, "years requirement pushes this away from true entry viability")
    elif years_required >= 2:
        add(-6, "years requirement adds friction")

    if acceptance_result.get("disguised_mid_level"):
        add(-14, "looks entry-level but reads mid-level")
    elif acceptance_result.get("junior_plus"):
        add(-6, "junior-plus ownership expectations")

    if re.search(r"\b(senior|sr\.?|lead|manager|director|principal|staff)\b", title):
        add(-18, "title itself signals this is not really an entry move")
    if re.search(r"\b(customer support|customer service|call center|representative)\b", title):
        if implicit_aggregator_it:
            add(3, "messy support framing can be a low-competition way in on aggregator jobs")
        else:
            add(-10, "generic customer-support framing is weaker than technical operations")
    if re.search(r"\b(help\s*desk|service\s*desk|technical support|support specialist|desktop support)\b", title):
        add(4, "hands-on support title usually gives better entry reps than vague analyst fluff")

    magnetism = acceptance_result.get("competition_magnetism")
    if magnetism == "high":
        add(-8, "brand or funnel magnetism raises the bar")
    elif magnetism == "medium":
        add(-3, "some competition pressure")

    if acceptance_result.get("difficulty_tier") == "high":
        add(-6, "high-difficulty company funnel")
    elif acceptance_result.get("difficulty_tier") == "medium":
        add(-2, "moderate company difficulty")

    if acceptance_result.get("company_effectiveness_label") == "strong":
        add(4, "source has produced good results before")
    elif acceptance_result.get("company_effectiveness_label") == "poor":
        add(-4, "source has been mostly noise for you")

    if track_name == "it_bridge" and trajectory_result["trajectory_score"] >= 70:
        add(4, "strong bridge-to-security trajectory")
    if ctx.is_cyber_track(track_name) and trajectory_result["trajectory_score"] >= 82:
        add(4, "role already touches core security workflows")

    if acceptance_result["acceptance_score"] <= 40:
        add(-10, "attainability is too weak for a clean entry play")
    if execution_result["execution_score"] <= 45:
        add(-8, "execution risk makes this a weak practical entry move")

    return {
        "entry_viability_score": max(0, min(score, 100)),
        "entry_viability_notes": notes,
    }


def get_stepping_stone_label(job, track_name, *, ctx):
    """Give a short plain-English label for how this role helps the path in."""
    title = job.get("title_lc") or ""

    if ctx.is_soc_track(track_name):
        return "Closest to SOC"

    if ctx.is_cyber_analyst_track(track_name):
        if ctx.matches_any_pattern(
            title,
            [
                r"\biam analyst\b",
                r"\bidentity\b",
                r"\baccess\b",
                r"\brisk analyst\b",
                r"\btrust\b",
                r"\bfraud\b",
                r"\binvestigations?\b",
            ],
        ):
            return "Adjacent analyst bridge"
        return "Closest to SOC"

    if ctx.matches_any_pattern(
        title,
        [
            r"\btechnical support\b",
            r"\bhelp ?desk\b",
            r"\bservice ?desk\b",
            r"\bdesktop support\b",
            r"\bsupport engineer\b",
            r"\bapplication support\b",
        ],
    ):
        return "Entry via support"

    return "IT bridge"


def compute_response_likelihood_score(
    job,
    acceptance_result,
    execution_result,
    narrative_result,
    target_signal_result,
    entry_viability_result,
    *,
    ctx,
):
    tags = set(acceptance_result.get("company_tags", []) or ())
    title = job.get("title_lc") or ""
    implicit_aggregator_it = ctx.is_implicit_aggregator_it_role(job)
    score = int(
        round(
            (acceptance_result["acceptance_score"] * 0.42)
            + (entry_viability_result["entry_viability_score"] * 0.24)
            + (narrative_result["narrative_score"] * 0.10)
            + (job.get("freshness_score", 50) * 0.08)
            + (execution_result["execution_score"] * 0.08)
            + (target_signal_result["target_signal_score"] * 0.08)
        )
    )
    notes = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if ctx.UGLY_ENTRY_TAGS & tags:
        add(10, "boring or local ecosystem usually responds better than prestige funnels")
    if ctx.PRESTIGE_HEAVY_TAGS & tags:
        add(-10, "prestige-heavy brand lowers practical response odds")

    source_type = str(job.get("source_type") or "")
    if source_type == "extended":
        add(5, "extended source often means less polished but more realistic hiring funnel")
    elif source_type == "aggregator":
        add(2, "aggregator surfaced a real opening outside the prestige ATS bubble")
        freshness_priority = ctx.get_freshness_priority_score(job)
        if freshness_priority >= 100:
            add(10, "aggregator freshness window boosts weird early opportunities")
        elif freshness_priority >= 75:
            add(6, "fresh aggregator role is worth acting on earlier")

    if ctx.is_priority_queue_location(job):
        add(8, "preferred geography improves practical response odds")
    elif ctx.is_us_location(job):
        add(3, "us-based role is still in play")

    if ctx.is_new_york_location(job):
        add(10, "local new york signal helps materially")

    years_required = acceptance_result.get("years_required", 0)
    if years_required == 0:
        add(4, "no explicit years barrier")
    elif years_required <= 2:
        add(2, "still plausibly early-career")
    else:
        add(-10, "experience requirement hurts practical response odds")

    competition = acceptance_result.get("competition_magnetism")
    if competition == "high":
        add(-8, "high applicant magnetism lowers callback odds")
    elif competition == "medium":
        add(-3, "some applicant pressure")

    if acceptance_result.get("difficulty_tier") == "high":
        add(-6, "hard company funnel")
    elif acceptance_result.get("difficulty_tier") == "medium":
        add(-2, "moderate company funnel")

    if acceptance_result.get("disguised_mid_level"):
        add(-12, "posting looks entry-level but likely will not respond like one")
    elif acceptance_result.get("junior_plus"):
        add(-5, "ownership expectations raise screening pressure")

    if re.search(r"\b(senior|sr\.?|lead|manager|director|principal|staff)\b", title):
        add(-16, "title signals the hiring team is not really looking for your level")

    if re.search(r"\b(customer support|customer service|call center)\b", title):
        if implicit_aggregator_it:
            add(6, "messy support framing often means lower competition and faster response odds")
        else:
            add(-8, "generic support can be hireable but is less aligned with your real target")
    elif re.search(r"\b(help\s*desk|service\s*desk|technical support|desktop support|support specialist)\b", title):
        add(4, "hands-on support titles often convert better than vague analyst titles")

    if job.get("freshness_score", 50) >= 78:
        add(4, "fresh posting improves odds of being seen")
    elif job.get("freshness_score", 50) <= 38:
        add(-6, "stale posting lowers response odds")

    if target_signal_result["target_signal_score"] >= 28:
        add(4, "still has meaningful technical or security signal")
    elif target_signal_result["target_signal_score"] <= 8:
        add(-10, "signal is viable but still weakly tied to your target lane")

    if "operator" in title and target_signal_result["target_signal_score"] <= 12:
        add(-6, "generic operator framing is easier to land but weaker for your target path")

    return {
        "response_likelihood_score": max(0, min(score, 100)),
        "response_likelihood_notes": notes,
    }


def compute_narrative_fit(job, track_name, *, ctx):
    """Score how easy this role will be to explain as a smart next move."""
    title = job.get("title_lc") or ""
    text = job.get("combined_lc") or ""
    tags = set(job.get("company_tags", []) or ())
    score = 55
    notes = []
    risks = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if ctx.is_soc_track(track_name):
        if ctx.matches_any_pattern(title, [r"\bsoc\b", r"\bsecurity operations\b", r"\bincident response\b", r"\bdetection\b"]):
            add(20, "title is easy to explain as direct security operations work")
        elif re.search(r"\bnoc analyst\b", title):
            add(12, "noc work is still easy to frame as monitoring and escalation experience")
    elif ctx.is_cyber_analyst_track(track_name):
        if ctx.matches_any_pattern(title, [r"\bsecurity analyst\b", r"\bcyber(?:security)? analyst\b", r"\biam analyst\b", r"\bidentity\b"]):
            add(18, "title is clearly inside a cyber or identity path")
        elif ctx.matches_any_pattern(title, [r"\brisk analyst\b", r"\btrust\b", r"\bfraud\b", r"\binvestigations?\b"]):
            add(10, "title is adjacent enough to explain as a bridge into security")
    else:
        if ctx.matches_any_pattern(
            title,
            [
                r"\btechnical support\b",
                r"\bhelp ?desk\b",
                r"\bservice ?desk\b",
                r"\bdesktop support\b",
                r"\bapplication support\b",
                r"\bsupport engineer\b",
            ],
        ):
            add(16, "hands-on support work is easy to connect to systems and troubleshooting")
        elif ctx.matches_any_pattern(title, [r"\bit operations?\b", r"\bsaas administrator\b", r"\bsystems?(?: administrator| admin)?\b"]):
            add(14, "systems and operations work is easy to explain as a bridge into security")

    if ctx.contains_any(
        text,
        [
            "tickets",
            "troubleshooting",
            "incident",
            "monitoring",
            "logs",
            "alerts",
            "iam",
            "identity",
            "siem",
            "defender",
            "splunk",
        ],
    ):
        add(10, "description gives concrete technical work you can talk about later")

    if ctx.UGLY_ENTRY_TAGS & tags:
        add(6, "boring entry-friendly company makes the story more believable")
    if ctx.PRESTIGE_HEAVY_TAGS & tags:
        add(-4, "prestige brand can look good but is harder to turn into a believable interview story")

    if re.search(r"\b(customer service|call center)\b", title):
        score -= 12
        risks.append("title reads more like generic customer support than technical work")
    if re.search(r"\b(senior|sr\.?|lead|manager|director|principal|staff)\b", title):
        score -= 18
        risks.append("title signals a level that is harder to justify for your current stage")

    return {
        "narrative_score": max(0, min(score, 100)),
        "narrative_notes": notes,
        "narrative_risks": risks,
    }


def compute_apply_priority_score(
    job,
    fit_result,
    acceptance_result,
    trajectory_result,
    entry_viability_result,
    response_likelihood_result,
    *,
    ctx,
):
    source_type = str(job.get("source_type") or "")
    score = int(
        round(
            (response_likelihood_result["response_likelihood_score"] * 0.34)
            + (entry_viability_result["entry_viability_score"] * 0.28)
            + (ctx.get_freshness_priority_score(job) * 0.20)
            + (acceptance_result["acceptance_score"] * 0.08)
            + (trajectory_result["trajectory_score"] * 0.05)
            + (fit_result["fit_score"] * 0.05)
        )
    )
    notes = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if source_type == "aggregator":
        add(8, "aggregator fast lane favors early messy openings that may respond faster")
    elif source_type == "extended":
        add(3, "extended source often means a more practical funnel than prestige ATS boards")

    if ctx.is_priority_queue_location(job):
        add(8, "priority location should be acted on quickly")
    elif ctx.is_us_location(job):
        add(2, "us-based role is still worth acting on if viable")

    if job.get("application_status", "NEW").upper() == "NEW":
        add(4, "new application opportunity")

    discovery_state = job.get("discovery_state")
    if discovery_state == "NEW":
        add(8, "newly surfaced job should be considered before it gets crowded")
    elif discovery_state == "UPDATED":
        add(4, "job materially changed and may be worth acting on now")

    freshness_priority = ctx.get_freshness_priority_score(job)
    if freshness_priority >= 100:
        add(10, "very fresh role creates a strong apply-now window")
    elif freshness_priority >= 75:
        add(6, "fresh role still has a fast-move edge")
    elif freshness_priority <= 35:
        add(-8, "stale role is less urgent even if the fit is decent")

    if entry_viability_result["entry_viability_score"] >= 80:
        add(6, "realistic entry path matters more than glamour")
    if response_likelihood_result["response_likelihood_score"] >= 85:
        add(6, "high callback odds should move this up")

    if acceptance_result.get("competition_magnetism") == "high":
        add(-6, "prestige pressure lowers practical apply priority")

    return {
        "apply_priority_score": max(0, min(score, 100)),
        "apply_priority_notes": notes,
    }


def compute_effort_score(
    job,
    track_name,
    fit_result,
    acceptance_result,
    execution_result,
    narrative_result,
    *,
    ctx,
):
    """Estimate how much application and interview effort this role may cost."""
    score = 50
    notes = []
    text = job.get("combined_lc") or ""
    title = job.get("title_lc") or ""

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    years_required = acceptance_result.get("years_required", 0)
    if years_required >= 5:
        add(18, "large experience gap means more effort to make the case")
    elif years_required >= 3:
        add(10, "years requirement adds extra application friction")
    elif years_required == 0:
        add(-4, "no years requirement keeps the effort lower")

    if acceptance_result.get("difficulty_tier") == "high":
        add(16, "hard company funnel usually means more interview effort")
    elif acceptance_result.get("difficulty_tier") == "medium":
        add(8, "moderate company funnel adds some effort")

    if acceptance_result.get("missing_certs"):
        add(8, "missing cert language means more explaining during screening")
    if acceptance_result.get("clearance_gap"):
        add(20, "clearance mismatch makes the process high effort with low payoff")
    if acceptance_result.get("disguised_mid_level"):
        add(14, "mid-level expectations hidden in the posting make the effort riskier")

    if execution_result.get("execution_score", 0) <= 45:
        add(10, "lower readiness means more prep before interviews")
    if narrative_result.get("narrative_score", 0) <= 45:
        add(8, "harder-to-explain role takes more effort to position well")
    if fit_result.get("skill_match_score", 0) <= 40:
        add(8, "weak skill overlap usually means more resume and interview work")

    if ctx.contains_any(text, ["on call", "after hours", "travel required", "clearance", "polygraph"]):
        add(10, "posting has extra burden signals")
    if re.search(r"\b(intern|seasonal|associate|junior)\b", title):
        add(-6, "junior framing usually lowers the amount of proof you need")
    if str(job.get("source_type") or "") == "aggregator":
        add(-4, "messier aggregator roles are often faster and lighter to apply to")

    return {
        "effort_score": max(0, min(score, 100)),
        "effort_notes": notes,
    }


def compute_roi_score(
    fit_result,
    acceptance_result,
    execution_result,
    trajectory_result,
    narrative_result,
    effort_result,
    *,
    ctx,
):
    """Estimate whether the likely upside is worth the time cost."""
    score = int(
        round(
            (acceptance_result["acceptance_score"] * 0.34)
            + (trajectory_result["trajectory_score"] * 0.22)
            + (fit_result["fit_score"] * 0.16)
            + (execution_result["execution_score"] * 0.10)
            + (narrative_result["narrative_score"] * 0.08)
            + ((100 - effort_result["effort_score"]) * 0.10)
        )
    )
    notes = []

    def add(points, note):
        nonlocal score
        score += points
        notes.append(note)

    if acceptance_result["acceptance_score"] >= 75:
        add(8, "good callback odds make the effort more worth it")
    elif acceptance_result["acceptance_score"] <= 45:
        add(-10, "low callback odds hurt the payoff")

    if trajectory_result["trajectory_score"] >= 80:
        add(8, "role strongly helps the long-term path into security")
    elif trajectory_result["trajectory_score"] <= 45:
        add(-6, "role does not move the target path forward very much")

    if effort_result["effort_score"] >= 72:
        add(-8, "expected effort is high compared to the likely payoff")
    elif effort_result["effort_score"] <= 42:
        add(4, "effort is light enough that the shot is easier to justify")

    if acceptance_result.get("company_effectiveness_label") == "strong":
        add(4, "this company has produced strong shortlist signal before")
    elif acceptance_result.get("company_effectiveness_label") == "poor":
        add(-4, "this company has mostly produced weak signal before")

    return {
        "roi_score": max(0, min(score, 100)),
        "roi_notes": notes,
    }


def get_source_adjusted_thresholds(job, track_name, mode, base_fit, base_final, *, ctx):
    source_type = str(job.get("source_type") or "")
    minimum_fit = base_fit
    minimum_final = base_final

    if source_type == "extended":
        minimum_fit = max(26 if ctx.is_it_track(track_name) else 30, minimum_fit - 4)
        minimum_final = max(44 if ctx.is_it_track(track_name) else 48, minimum_final - 4)
    elif source_type == "aggregator":
        if ctx.is_it_track(track_name):
            minimum_fit = max(20, minimum_fit - 12)
            minimum_final = max(34, minimum_final - 12)
        elif ctx.is_cyber_track(track_name):
            minimum_fit = max(28, minimum_fit - 8)
            minimum_final = max(42, minimum_final - 8)

    if mode == "volume":
        minimum_fit = max(30, minimum_fit - 8)
        minimum_final = max(46, minimum_final - 10)
    elif mode == "internship":
        minimum_fit = max(28, minimum_fit - 6)
        minimum_final = max(42, minimum_final - 8)

    return minimum_fit, minimum_final


def compute_source_adjusted_final_score(
    job,
    fit_result,
    acceptance_result,
    execution_result,
    trajectory_result,
    narrative_result,
    roi_result,
    target_signal_result,
    entry_viability_result,
    response_likelihood_result,
    *,
    ctx,
):
    source_type = str(job.get("source_type") or "")

    base_score = int(
        round(
            (fit_result["fit_score"] * 0.30)
            + (acceptance_result["acceptance_score"] * 0.24)
            + (execution_result["execution_score"] * 0.12)
            + (trajectory_result["trajectory_score"] * 0.10)
            + (narrative_result["narrative_score"] * 0.12)
            + (roi_result["roi_score"] * 0.12)
            + (target_signal_result["target_signal_score"] * 0.08)
        )
    )
    base_score = int(round((base_score * 0.88) + (entry_viability_result["entry_viability_score"] * 0.12)))

    if source_type == "extended":
        adjusted = int(
            round(
                (base_score * 0.78)
                + (entry_viability_result["entry_viability_score"] * 0.12)
                + (response_likelihood_result["response_likelihood_score"] * 0.10)
            )
        )
        return max(0, min(adjusted, 100))

    if source_type == "aggregator":
        freshness_priority = ctx.get_freshness_priority_score(job)
        adjusted = int(
            round(
                (base_score * 0.54)
                + (entry_viability_result["entry_viability_score"] * 0.20)
                + (response_likelihood_result["response_likelihood_score"] * 0.16)
                + (freshness_priority * 0.10)
            )
        )
        if freshness_priority >= 100:
            adjusted += 8
        elif freshness_priority >= 75:
            adjusted += 4
        return max(0, min(adjusted, 100))

    return max(0, min(base_score, 100))


def choose_decision(roi_score, fit_score, acceptance_score, execution_score, narrative_score, difficulty_tier, *, ctx):
    if roi_score >= 70 and acceptance_score >= 68 and narrative_score >= 60 and execution_score >= 52:
        return "APPLY (High ROI)"
    if difficulty_tier == "high" and (acceptance_score < 60 or roi_score < 50):
        return "LOTTERY"
    if roi_score >= 62 and fit_score >= 70 and acceptance_score >= 58 and execution_score >= 50:
        return "APPLY (Stretch)"
    if roi_score >= 54 and fit_score >= 64 and acceptance_score >= 52 and execution_score >= 45:
        return "APPLY (Low ROI)"
    if difficulty_tier == "standard" and acceptance_score >= 55:
        return "BACKUP (Safe)"
    return "BACKUP (Competitive)"


def build_risk_notes(acceptance_result, execution_result, narrative_result, effort_result, *, ctx):
    risks = []

    if acceptance_result["difficulty_tier"] == "high":
        risks.append("High competition and applicant volume")
    elif acceptance_result["difficulty_tier"] == "medium":
        risks.append("Competitive company funnel")

    if acceptance_result["years_required"] >= 3:
        risks.append(f"{acceptance_result['years_required']}+ years requested")

    if acceptance_result["missing_certs"]:
        risks.append("Cert gap may matter")

    if acceptance_result["clearance_gap"]:
        risks.append("Clearance requirement mismatch")

    if acceptance_result["hidden_signals"]:
        risks.append(", ".join(acceptance_result["hidden_signals"][:2]))

    if acceptance_result.get("disguised_mid_level"):
        risks.append("Looks entry-level by title but reads mid-level in the details")

    risks.extend(execution_result["execution_risks"][:2])
    risks.extend(narrative_result["narrative_risks"][:1])

    if effort_result["effort_score"] >= 72:
        risks.append("Application and interview burden looks heavier than average")

    return risks[:3]


def get_execution_tier(score, *, ctx):
    if score >= 80:
        return "Ready now"
    if score >= 60:
        return "Ramp-up likely"
    if score >= 40:
        return "Interview risk"
    return "Not ready"
