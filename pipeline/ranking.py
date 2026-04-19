"""Rank one job for one target lane.

Inputs:
- one normalized job from `pipeline/normalization.py`
- one track name, like SOC, cyber bridge, or IT bridge
- the matching resume text for that track

Output:
- either `None` if the job should be rejected for that lane
- or a ranked job dictionary with fit, acceptance, ROI, trajectory,
  entry viability, response likelihood, and queue/report metadata

This file is where "looks good" gets separated from "worth applying to."
"""

import re


def compute_fit_score(job, track_name, resume_text, *, ctx):
    """Combine title fit and resume overlap into one fit score."""
    title_score, title_reasons = ctx.compute_title_fit_score(job, track_name)
    if title_score == 0:
        return None

    resume_result = ctx.score_job(
        resume_text,
        f"{job['title']}\n{job['description']}",
        ctx.get_skill_profile(track_name),
    )
    skill_score = resume_result["match_percent"]

    # Each lane mixes title fit and resume overlap differently.
    # This changes how strict the lane is before the job can continue.
    if ctx.is_soc_track(track_name):
        fit_score = int(round((title_score * 0.70) + (skill_score * 0.30)))
    elif ctx.is_cyber_analyst_track(track_name):
        fit_score = int(round((title_score * 0.62) + (skill_score * 0.38)))
    else:
        aggregator_support_title = str(job.get("source_type") or "") == "aggregator" and ctx.has_aggregator_support_title(
            job.get("title_lc") or ""
        )
        if ctx.is_implicit_aggregator_it_role(job):
            fit_score = int(round((title_score * 0.58) + (skill_score * 0.42)))
        else:
            fit_score = int(round((title_score * 0.40) + (skill_score * 0.60)))
        tags = set(job.get("company_tags", []) or ())
        title_lc = job.get("title_lc") or ""

        # Ugly entry roles often have thin descriptions.
        # These floors stop obvious support titles from dying only because the
        # posting text was too short to describe the work well.
        if (ctx.UGLY_ENTRY_TAGS & tags) and ctx.matches_any_pattern(
            title_lc,
            [
                r"\bhelp ?desk\b",
                r"\bservice ?desk\b",
                r"\btechnical support\b",
                r"\bsupport specialist\b",
                r"\bdesktop support\b",
            ],
        ):
            fit_score = max(fit_score, min(44, int(round(title_score * 0.8))))
        if ctx.is_implicit_aggregator_it_role(job):
            fit_score = max(fit_score, min(42, int(round(title_score * 0.9))))
        elif aggregator_support_title:
            fit_score = max(fit_score, min(36, int(round(title_score * 0.88))))

    fit_notes = list(title_reasons[:2])
    if ctx.is_it_track(track_name):
        tags = set(job.get("company_tags", []) or ())
        title_lc = job.get("title_lc") or ""
        if (ctx.UGLY_ENTRY_TAGS & tags) and ctx.matches_any_pattern(
            title_lc,
            [
                r"\bhelp ?desk\b",
                r"\bservice ?desk\b",
                r"\btechnical support\b",
                r"\bsupport specialist\b",
                r"\bdesktop support\b",
            ],
        ):
            fit_notes.append("title is strong enough to carry an ugly but viable support path")
        if ctx.is_implicit_aggregator_it_role(job):
            fit_notes.append("implicit aggregator fit: messy support role kept alive")
        elif aggregator_support_title:
            fit_notes.append("aggregator support title got a fit floor because the listing text is thin")
    if resume_result["matched"]:
        fit_notes.append("skills: " + ", ".join(resume_result["matched"][:3]))
    if resume_result["missing_critical"]:
        fit_notes.append("missing: " + ", ".join(resume_result["missing_critical"][:2]))

    return {
        "fit_score": max(0, min(fit_score, 100)),
        "title_score": title_score,
        "skill_match_score": skill_score,
        "resume_result": resume_result,
        "fit_notes": fit_notes,
    }


def compute_acceptance_score(job, track_name, resume_text, fit_result, *, ctx):
    """Estimate how realistic the job is for the user right now."""
    text = job["combined_lc"]
    title = job["title_lc"]
    location = job["location_lc"]
    implicit_aggregator_it = ctx.is_implicit_aggregator_it_role(job)
    resume_text = resume_text.lower()
    early_career = ctx.is_early_career(job)
    company_id = ctx.normalize_company_id(job.get("company_id", ""))
    difficulty = ctx.get_company_difficulty(company_id)
    company_profile = ctx.get_company_target_profile(company_id, job.get("company_group", ""), job)
    role_difficulty = ctx.get_role_difficulty_modifier(job, track_name)
    competition_magnetism = ctx.detect_competition_magnetism(job, track_name, company_profile["difficulty"])
    hidden_signals, hidden_penalty = ctx.detect_hidden_requirement_signals(text)
    freshness_score = job.get("freshness_score", 50)
    disguised_mid_level, disguised_reasons = ctx.detect_disguised_mid_level(job)
    junior_plus, junior_plus_reasons = ctx.detect_junior_plus(job)

    score = 70
    reasons = []
    years_required = ctx.extract_required_years(text)
    # Only treat clearance as a real blocker when the posting points to
    # government-style clearance requirements. Generic background-screening
    # language should not get the same penalty.
    clearance_gap = ctx.matches_any_pattern(
        text,
        [
            r"\bsecurity clearance\b",
            r"\bactive clearance\b",
            r"\bcurrent clearance\b",
            r"\bsecret clearance\b",
            r"\btop secret(?: clearance)?\b",
            r"\bts\/sci\b",
            r"\bpublic trust\b",
            r"\bclearance required\b",
            r"\bactive secret\b",
            r"\bactive top secret\b",
            r"\bmust be able to obtain\b.{0,40}\b(?:security )?clearance\b",
            r"\bability to obtain\b.{0,40}\b(?:security )?clearance\b",
            r"\beligible to obtain\b.{0,40}\b(?:security )?clearance\b",
            r"\bmaintain\b.{0,40}\b(?:security )?clearance\b",
            r"\brequires?\b.{0,40}\b(?:security |secret |top secret |public trust |active )clearance\b",
        ],
    ) and "clearance" not in resume_text

    def add(points, label):
        nonlocal score
        score += points
        reasons.append(label)

    # The score starts in the middle and moves up or down as this function
    # finds evidence that the role is more or less realistic to win.
    if ctx.is_new_york_location(job):
        add(12, "new york eligible")

    if job.get("is_remote") or any(term in location for term in ctx.REMOTE_LOCATION_TERMS):
        add(10, "remote eligible")

    if early_career:
        add(12, "early-career role")

    if freshness_score >= 92:
        add(18, "fresh posting")
    elif freshness_score >= 80:
        add(12, "recent posting")
    elif freshness_score >= 66:
        add(6, "still fresh enough")
    elif freshness_score >= 54:
        add(1, "older posting")
    elif freshness_score >= 42:
        add(-6, "aging posting")
    elif freshness_score >= 30:
        add(-14, "old posting")
    else:
        add(-22, "stale posting")

    if years_required == 0:
        add(6, "no years stated")
    elif years_required == 1:
        add(4, "1 year required")
    elif years_required == 2:
        add(-2, "2 years required")
    elif years_required == 3:
        add(-14, "3 years required")
    elif years_required == 4:
        add(-22, "4 years required")
    elif years_required == 5:
        add(-34, "5 years required")
    elif years_required in {6, 7}:
        add(-45, f"{years_required}+ years required")
    elif years_required >= 8:
        add(-58, f"{years_required}+ years required")

    # Seniority words are strong warning signs.
    # They push the score down quickly even if the rest of the posting looks good.
    if re.search(r"\b(manager|director|head|vp)\b", title):
        add(-45, "management title")
    elif re.search(r"\b(principal|staff|lead|senior|sr\.?)\b", title):
        add(-28, "senior title")

    if difficulty["penalty"] > 0:
        add(-difficulty["penalty"], f"{difficulty['tier']} competition")

    if role_difficulty["penalty_delta"]:
        add(-role_difficulty["penalty_delta"], role_difficulty["label"])

    if company_profile["acceptance_bonus"]:
        add(company_profile["acceptance_bonus"], f"{company_profile['group']} company bias")

    if hidden_penalty:
        add(-hidden_penalty, "mid-level wording")

    if disguised_mid_level:
        add(-18, "disguised mid-level")

    if junior_plus:
        add(-8, "junior+ expectations")

    if competition_magnetism["label"] == "high":
        add(-10, "high competition magnetism")
    elif competition_magnetism["label"] == "medium":
        add(-5, "medium competition magnetism")

    if ctx.is_soc_track(track_name):
        if re.search(r"\bsoc analyst\b", title):
            add(26, "soc analyst target")
        elif re.search(r"\bnoc analyst\b", title):
            add(20, "noc analyst target")
        elif re.search(r"\bnetwork operations? analyst\b", title):
            add(16, "network operations bridge")
        elif re.search(r"\bsecurity operations analyst\b", title):
            add(22, "security operations target")
        elif re.search(r"\bsoc engineer\b", title):
            add(8, "soc bridge target")
        elif ctx.is_blue_team_cyber_title(title):
            add(10, "blue-team target")

        if re.search(r"\bsoc\b", title):
            add(22, "soc target")
        if ctx.matches_any_pattern(title, [r"\bdetection\b", r"\bresponse\b", r"\bincident response\b"]):
            add(10, "detection-response target")

        if ctx.has_junior_title_signal(title):
            add(14, "junior title")

        if "travel-required" in location or "travel required" in text:
            add(-6, "travel required")

        if ctx.contains_any(
            text,
            [
                "siem",
                "sentinel",
                "splunk",
                "alert triage",
                "security operations",
                "monitoring",
                "log analysis",
                "defender",
            ],
        ):
            add(10, "soc tooling match")

        if re.search(r"\bengineer\b", title) and not re.search(r"\bsoc\b", title):
            add(-24, "engineer title")
        elif re.search(r"\bsoc engineer\b", title):
            add(-10, "engineer title in soc lane")

        if ctx.is_specialized_security_engineering_title(title) and not early_career:
            add(-24, "specialized security engineering")

        if ctx.matches_any_pattern(
            text,
            [
                r"\bsoftware engineering\b",
                r"\bdistributed systems?\b",
                r"\bbackend systems?\b",
                r"\bplatform engineering\b",
                r"\bfrom scratch\b",
            ],
        ):
            add(-16, "engineering-heavy posting")

    elif ctx.is_cyber_analyst_track(track_name):
        if re.search(r"\bsecurity analyst\b", title):
            add(22, "security analyst target")
        elif re.search(r"\bcyber(?:security)? analyst\b", title):
            add(22, "cyber analyst target")
        elif ctx.matches_any_pattern(
            title,
            [r"\biam analyst\b", r"\bidentity analyst\b", r"\baccess (?:control|management|administration)? ?analyst\b"],
        ):
            add(16, "identity-access bridge")
        elif re.search(r"\brisk analyst\b", title):
            add(10, "risk bridge")
        elif ctx.is_cyber_investigator_title(title):
            add(14, "investigations target")
        elif re.search(r"\bthreat (?:intel(?:ligence)?|detection|response)? ?analyst\b", title):
            add(18, "threat analyst target")
        elif re.search(r"\bvulnerability analyst\b", title):
            add(14, "vulnerability target")

        if ctx.is_blue_team_cyber_title(title):
            add(8, "blue-team target")

        if ctx.has_junior_title_signal(title):
            add(12, "junior title")

        if ctx.contains_any(
            text,
            [
                "siem",
                "sentinel",
                "splunk",
                "investigation",
                "incident response",
                "vulnerability",
                "iam",
                "defender",
            ],
        ):
            add(8, "analyst tooling match")

        if re.search(r"\bengineer\b", title) and not ctx.is_blue_team_cyber_title(title):
            add(-18, "engineer title")

        if ctx.is_specialized_security_engineering_title(title) and not early_career:
            add(-16, "specialized security engineering")

        if re.search(r"\bsecurity operations analyst\b", title):
            add(8, "ops analyst adjacency")

        if re.search(r"\bsoc engineer\b", title):
            add(6, "soc bridge adjacency")

    if ctx.is_it_track(track_name):
        if ctx.matches_any_pattern(
            title,
            [
                r"\bit support\b",
                r"\bhelp ?desk\b",
                r"\bservice ?desk\b",
                r"\bdesktop support\b",
                r"\binternal it\b",
                r"\bend user support\b",
                r"\bapplication support\b",
                r"\bsystems support\b",
            ],
        ):
            add(14, "helpdesk transition target")

        if ctx.matches_any_pattern(
            title,
            [r"\bit operations?\b", r"\bsystems?(?: administrator| admin)?\b", r"\bsaas administrator\b", r"\bsupport engineer\b"],
        ):
            add(8, "good bridge role")

        if ctx.matches_any_pattern(title, [r"\bproduct support\b", r"\bcustomer support\b"]):
            if implicit_aggregator_it:
                add(-4, "messy support title but still plausible for a lower-competition entry shot")
            else:
                add(-18, "less relevant support track")

    if ctx.is_cyber_track(track_name) and ctx.is_engineering_heavy_cyber_title(title) and not early_career and not ctx.is_blue_team_cyber_title(title):
        add(-14, "engineering-heavy title")

    if disguised_mid_level:
        score = min(score, 60 if years_required <= 1 else 55)

    missing_certs = ctx.detect_missing_certs(text, resume_text, track_name)
    if missing_certs:
        penalty = min(18, len(missing_certs) * 9)
        add(-penalty, "missing cert")

    if clearance_gap:
        add(-42, "clearance gap")

    missing_critical = len(fit_result["resume_result"]["missing_critical"])
    if missing_critical >= 2:
        add(-18, "missing critical skills")
    elif missing_critical == 1:
        add(-10, "missing one critical skill")

    skill_match_score = fit_result["skill_match_score"]
    if skill_match_score >= 80:
        add(8, "strong resume overlap")
    elif skill_match_score >= 60:
        add(4, "good resume overlap")
    elif skill_match_score < 40:
        add(-12, "weak resume overlap")

    if company_profile["effectiveness_label"] == "strong":
        add(4, "company has produced strong shortlist signal")
    elif company_profile["effectiveness_label"] == "useful":
        add(2, "company has produced useful shortlist signal")
    elif company_profile["effectiveness_label"] == "weak":
        add(-2, "company has produced weak shortlist signal")
    elif company_profile["effectiveness_label"] == "poor":
        add(-4, "company rarely produces strong shortlist signal")

    score_cap = 90
    if company_profile["difficulty"] in {"stretch", "lottery"}:
        score_cap = min(score_cap, 82)
    if competition_magnetism["label"] == "high":
        score_cap = min(score_cap, 75)
    elif competition_magnetism["label"] == "medium":
        score_cap = min(score_cap, 82)
    if junior_plus:
        score_cap = min(score_cap, 78)
    if disguised_mid_level:
        score_cap = min(score_cap, 60 if years_required <= 1 else 55)

    return {
        "acceptance_score": max(0, min(score, score_cap)),
        "acceptance_notes": reasons,
        "years_required": years_required,
        "missing_certs": missing_certs,
        "difficulty_tier": difficulty["tier"],
        "difficulty_penalty": difficulty["penalty"],
        "company_group": company_profile["group"],
        "company_tags": company_profile["tags"],
        "company_difficulty": company_profile["difficulty"],
        "company_hiring_pattern": company_profile["hiring_pattern"],
        "company_industry": company_profile["industry"],
        "company_roi_multiplier": company_profile["roi_multiplier"],
        "company_effectiveness_score": company_profile["effectiveness_score"],
        "company_effectiveness_label": company_profile["effectiveness_label"],
        "junior_plus": junior_plus,
        "junior_plus_reasons": junior_plus_reasons,
        "competition_magnetism": competition_magnetism["label"],
        "competition_magnetism_reasons": competition_magnetism["reasons"],
        "hidden_signals": hidden_signals,
        "clearance_gap": clearance_gap,
        "disguised_mid_level": disguised_mid_level,
        "disguised_reasons": disguised_reasons,
    }


def build_ranked_job(job, track_name, resume_text, mode="standard", *, ctx):
    """Return a ranked job only if it clears the gates for this lane.

    The gates are intentionally different by mode:
    - standard mode feeds the main shortlist and apply queue
    - volume mode is looser so reports can show near misses for analysis
    - internship mode uses separate rules for intern/new-grad opportunities
    """
    # This is the main gate for one job in one lane.
    # If the job survives this function, it can show up in the queue or reports.
    if mode == "internship":
        if not ctx.is_internship_like(job):
            return None
        if not ctx.is_internship_target_location(job):
            return None
    elif not ctx.is_target_location(job):
        return None

    if ctx.is_physical_security(f"{job['title_lc']} {job['description_lc']}"):
        return None

    if ctx.is_soc_track(track_name):
        if not ctx.is_target_soc_role_title(job["title_lc"]):
            return None
        if ctx.fails_entry_level_cyber_gate(job, resume_text, track_name):
            return None
    if ctx.is_cyber_analyst_track(track_name):
        if not ctx.is_target_cyber_analyst_role_title(job["title_lc"]):
            return None
        if ctx.fails_entry_level_cyber_gate(job, resume_text, track_name):
            return None
    if ctx.is_it_track(track_name) and not (
        ctx.is_target_it_role_title(job["title_lc"]) or ctx.is_implicit_aggregator_it_role(job)
    ):
        return None

    fit_result = compute_fit_score(job, track_name, resume_text, ctx=ctx)
    base_fit = 45 if ctx.is_soc_track(track_name) else 42 if ctx.is_cyber_analyst_track(track_name) else 35
    base_final = ctx.TRACKS[track_name].get("min_final_score", ctx.MIN_FINAL_SCORE)
    minimum_fit, minimum_final = ctx.get_source_adjusted_thresholds(job, track_name, mode, base_fit, base_final)
    # Source-adjusted thresholds are where aggregator/local roles get a fairer
    # bar than polished ATS roles. That prevents messy but realistic jobs from
    # losing only because their descriptions are short or inconsistent.
    if not fit_result or fit_result["fit_score"] < minimum_fit:
        return None

    # These scores answer different questions:
    # acceptance = can you plausibly pass screening
    # execution = can you do/interview for the work
    # trajectory = does it move you toward cyber/SOC
    # ROI = is the application worth the time
    acceptance_result = compute_acceptance_score(job, track_name, resume_text, fit_result, ctx=ctx)
    execution_result = ctx.compute_execution_score(job, track_name, resume_text, fit_result)
    trajectory_result = ctx.compute_trajectory_score(job, track_name, fit_result)
    target_signal_result = ctx.compute_target_signal(
        {
            **job,
            "company_tags": acceptance_result["company_tags"],
        }
    )
    narrative_result = ctx.compute_narrative_fit(job, track_name)
    effort_result = ctx.compute_effort_score(job, track_name, fit_result, acceptance_result, execution_result, narrative_result)
    roi_result = ctx.compute_roi_score(
        fit_result,
        acceptance_result,
        execution_result,
        trajectory_result,
        narrative_result,
        effort_result,
    )
    execution_tier = ctx.get_execution_tier(execution_result["execution_score"])
    stepping_stone_label = ctx.get_stepping_stone_label(
        {
            **job,
            "company_tags": acceptance_result["company_tags"],
        },
        track_name,
    )
    entry_viability_result = ctx.compute_entry_viability_score(
        job,
        track_name,
        fit_result,
        acceptance_result,
        execution_result,
        trajectory_result,
        target_signal_result,
        narrative_result,
        stepping_stone_label,
    )
    response_likelihood_result = ctx.compute_response_likelihood_score(
        job,
        acceptance_result,
        execution_result,
        narrative_result,
        target_signal_result,
        entry_viability_result,
    )
    apply_priority_result = ctx.compute_apply_priority_score(
        job,
        fit_result,
        acceptance_result,
        trajectory_result,
        entry_viability_result,
        response_likelihood_result,
    )
    final_score = ctx.compute_source_adjusted_final_score(
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
    )

    if ctx.is_it_track(track_name) and (ctx.UGLY_ENTRY_TAGS & set(acceptance_result["company_tags"])):
        if response_likelihood_result["response_likelihood_score"] >= 70:
            minimum_final = max(40, minimum_final - 10)
        elif entry_viability_result["entry_viability_score"] >= 72:
            minimum_final = max(42, minimum_final - 8)
    if final_score < minimum_final:
        return None

    decision = ctx.choose_decision(
        roi_result["roi_score"],
        fit_result["fit_score"],
        acceptance_result["acceptance_score"],
        execution_result["execution_score"],
        narrative_result["narrative_score"],
        acceptance_result["difficulty_tier"],
    )
    risk_notes = ctx.build_risk_notes(acceptance_result, execution_result, narrative_result, effort_result)

    overflow_reason = ""
    if acceptance_result.get("disguised_mid_level"):
        overflow_reason = "disguised mid-level"
    elif job.get("freshness_score", 50) <= 42:
        overflow_reason = "stale but possible"
    elif mode == "volume":
        overflow_reason = "volume mode"
    elif mode == "internship":
        overflow_reason = "internship scout"

    return {
        "decision": decision,
        "track": track_name,
        "path_tier": ctx.get_path_tier_label(job, track_name),
        "stepping_stone_label": stepping_stone_label,
        "resume": ctx.TRACKS[track_name]["resume_key"],
        "company_id": ctx.normalize_company_id(job.get("company_id")),
        "company": job["company"],
        "title": job["title"],
        "location": job["location"],
        "source": job["source"],
        "source_type": job.get("source_type", "other"),
        "url": job["url"],
        "final_score": final_score,
        "fit_score": fit_result["fit_score"],
        "acceptance_score": acceptance_result["acceptance_score"],
        "execution_score": execution_result["execution_score"],
        "trajectory_score": trajectory_result["trajectory_score"],
        "entry_viability_score": entry_viability_result["entry_viability_score"],
        "response_likelihood_score": response_likelihood_result["response_likelihood_score"],
        "apply_priority_score": apply_priority_result["apply_priority_score"],
        "target_signal_score": target_signal_result["target_signal_score"],
        "narrative_score": narrative_result["narrative_score"],
        "roi_score": roi_result["roi_score"],
        "effort_score": effort_result["effort_score"],
        "freshness_score": job.get("freshness_score", 50),
        "freshness_label": job.get("freshness_label", "unknown"),
        "freshness_days_old": job.get("freshness_days_old"),
        "posted_at_iso": job.get("posted_at_iso", ""),
        "volume_mode": mode == "volume",
        "internship_mode": mode == "internship",
        "overflow_reason": overflow_reason,
        "disguised_mid_level": acceptance_result.get("disguised_mid_level", False),
        "disguised_reasons": " | ".join(acceptance_result.get("disguised_reasons", [])),
        "execution_tier": execution_tier,
        "difficulty_tier": acceptance_result["difficulty_tier"],
        "company_group": acceptance_result["company_group"],
        "company_tags": acceptance_result["company_tags"],
        "company_difficulty": acceptance_result["company_difficulty"],
        "company_hiring_pattern": acceptance_result["company_hiring_pattern"],
        "company_industry": acceptance_result["company_industry"],
        "company_effectiveness_score": acceptance_result["company_effectiveness_score"],
        "company_effectiveness_label": acceptance_result["company_effectiveness_label"],
        "junior_plus": acceptance_result["junior_plus"],
        "junior_plus_reasons": " | ".join(acceptance_result["junior_plus_reasons"]),
        "competition_magnetism": acceptance_result["competition_magnetism"],
        "competition_magnetism_reasons": " | ".join(acceptance_result["competition_magnetism_reasons"]),
        "skill_match_score": fit_result["skill_match_score"],
        "title_score": fit_result["title_score"],
        "matched_skills": fit_result["resume_result"]["matched"],
        "missing_skills": fit_result["resume_result"]["missing"],
        "matched_critical_skills": fit_result["resume_result"]["matched_critical"],
        "missing_critical_skills": fit_result["resume_result"]["missing_critical"],
        "years_required": acceptance_result["years_required"],
        "fit_notes": " | ".join(fit_result["fit_notes"]) if fit_result["fit_notes"] else "",
        "acceptance_notes": " | ".join(acceptance_result["acceptance_notes"])
        if acceptance_result["acceptance_notes"]
        else "",
        "execution_notes": " | ".join(execution_result["execution_notes"])
        if execution_result["execution_notes"]
        else "",
        "trajectory_notes": " | ".join(trajectory_result["trajectory_notes"])
        if trajectory_result["trajectory_notes"]
        else "",
        "entry_viability_notes": " | ".join(entry_viability_result["entry_viability_notes"])
        if entry_viability_result["entry_viability_notes"]
        else "",
        "response_likelihood_notes": " | ".join(response_likelihood_result["response_likelihood_notes"])
        if response_likelihood_result["response_likelihood_notes"]
        else "",
        "apply_priority_notes": " | ".join(apply_priority_result["apply_priority_notes"])
        if apply_priority_result["apply_priority_notes"]
        else "",
        "target_signal_notes": " | ".join(target_signal_result["target_signal_notes"])
        if target_signal_result["target_signal_notes"]
        else "",
        "narrative_notes": " | ".join(narrative_result["narrative_notes"])
        if narrative_result["narrative_notes"]
        else "",
        "roi_notes": " | ".join(roi_result["roi_notes"]) if roi_result["roi_notes"] else "",
        "effort_notes": " | ".join(effort_result["effort_notes"]) if effort_result["effort_notes"] else "",
        "risk_notes": " | ".join(risk_notes) if risk_notes else "",
    }


def diagnose_track_rejection(job, track_name, resume_text, mode="standard", *, ctx):
    """Return the first reason a job fails for one track."""
    if not ctx.is_target_location(job):
        return "location"

    if ctx.is_physical_security(f"{job['title_lc']} {job['description_lc']}"):
        return "physical_security"

    if ctx.is_soc_track(track_name):
        if not ctx.is_target_soc_role_title(job["title_lc"]):
            return "soc_title_mismatch"
        if ctx.fails_entry_level_cyber_gate(job, resume_text, track_name):
            return "entry_level_cyber_gate"

    if ctx.is_cyber_analyst_track(track_name):
        if not ctx.is_target_cyber_analyst_role_title(job["title_lc"]):
            return "cyber_title_mismatch"
        if ctx.fails_entry_level_cyber_gate(job, resume_text, track_name):
            return "entry_level_cyber_gate"

    if ctx.is_it_track(track_name) and not (
        ctx.is_target_it_role_title(job["title_lc"]) or ctx.is_implicit_aggregator_it_role(job)
    ):
        return "it_title_mismatch"

    fit_result = compute_fit_score(job, track_name, resume_text, ctx=ctx)
    base_fit = 45 if ctx.is_soc_track(track_name) else 42 if ctx.is_cyber_analyst_track(track_name) else 35
    base_final = ctx.TRACKS[track_name].get("min_final_score", ctx.MIN_FINAL_SCORE)
    minimum_fit, minimum_final = ctx.get_source_adjusted_thresholds(job, track_name, mode, base_fit, base_final)
    if not fit_result or fit_result["fit_score"] < minimum_fit:
        return "weak_fit"

    acceptance_result = compute_acceptance_score(job, track_name, resume_text, fit_result, ctx=ctx)
    execution_result = ctx.compute_execution_score(job, track_name, resume_text, fit_result)
    trajectory_result = ctx.compute_trajectory_score(job, track_name, fit_result)
    target_signal_result = ctx.compute_target_signal(
        {
            **job,
            "company_tags": acceptance_result["company_tags"],
        }
    )
    narrative_result = ctx.compute_narrative_fit(job, track_name)
    effort_result = ctx.compute_effort_score(job, track_name, fit_result, acceptance_result, execution_result, narrative_result)
    roi_result = ctx.compute_roi_score(
        fit_result,
        acceptance_result,
        execution_result,
        trajectory_result,
        narrative_result,
        effort_result,
    )
    stepping_stone_label = ctx.get_stepping_stone_label(
        {
            **job,
            "company_tags": acceptance_result["company_tags"],
        },
        track_name,
    )
    entry_viability_result = ctx.compute_entry_viability_score(
        job,
        track_name,
        fit_result,
        acceptance_result,
        execution_result,
        trajectory_result,
        target_signal_result,
        narrative_result,
        stepping_stone_label,
    )
    response_likelihood_result = ctx.compute_response_likelihood_score(
        job,
        acceptance_result,
        execution_result,
        narrative_result,
        target_signal_result,
        entry_viability_result,
    )
    final_score = ctx.compute_source_adjusted_final_score(
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
    )
    if final_score < minimum_final:
        return "final_score_too_low"

    return "eligible"
