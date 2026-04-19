"""Diagnostic helpers for the job tool.

This file builds the extra analysis views that help improve the pipeline, like
rejection breakdowns, hit reports, and shortlist splitting.
"""


def build_rejection_breakdown(normalized_jobs, resumes, *, ctx):
    breakdown = {}

    for track_name in ctx.TRACKS:
        counts = {}
        total_jobs = 0
        standard_rejected = 0
        volume_recovered = 0
        primary_candidates = 0
        resume_text = ctx.get_resume_for_track(resumes, track_name)

        for job in normalized_jobs:
            total_jobs += 1
            standard_reason = ctx.ranking.diagnose_track_rejection(
                job,
                track_name,
                resume_text,
                mode="standard",
                ctx=ctx,
            )

            if standard_reason == "eligible":
                primary_candidates += 1
                continue

            standard_rejected += 1
            counts[standard_reason] = counts.get(standard_reason, 0) + 1

            volume_reason = ctx.ranking.diagnose_track_rejection(
                job,
                track_name,
                resume_text,
                mode="volume",
                ctx=ctx,
            )
            if volume_reason == "eligible":
                volume_recovered += 1
                counts["main_shortlist_threshold"] = counts.get("main_shortlist_threshold", 0) + 1

        breakdown[track_name] = {
            "track_label": ctx.TRACKS[track_name]["label"],
            "total_jobs": total_jobs,
            "primary_candidates": primary_candidates,
            "standard_rejected": standard_rejected,
            "volume_recovered": volume_recovered,
            "reasons": dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))),
        }

    return breakdown


def write_rejection_breakdown_markdown(path, breakdown, *, ctx):
    reason_labels = {
        "location": "Wrong location",
        "physical_security": "Physical security / non-target role",
        "soc_title_mismatch": "Not a SOC-style title",
        "cyber_title_mismatch": "Not a cyber-analyst title",
        "it_title_mismatch": "Not an IT bridge / helpdesk title",
        "entry_level_cyber_gate": "Fails entry-level cyber gate",
        "weak_fit": "Weak fit / resume overlap",
        "final_score_too_low": "Score too low after realism checks",
        "main_shortlist_threshold": "Only recovered by stretch / volume rules",
    }

    lines = [
        "# Rejection Breakdown",
        "",
        f"Generated on `{ctx.TODAY}`.",
        f"Location mode: `{ctx.LOCATION_MODE_LABELS.get(ctx.LOCATION_MODE, ctx.LOCATION_MODE)}`.",
        "",
        "This report shows where jobs were rejected before making the shortlist, so we can see which filters are actually choking the funnel.",
        "",
    ]

    for _, data in breakdown.items():
        lines.extend(
            [
                f"## {data['track_label']}",
                "",
                f"- `Total Jobs Checked`: {data['total_jobs']}",
                f"- `Primary Candidates`: {data['primary_candidates']}",
                f"- `Rejected Before Main Shortlist`: {data['standard_rejected']}",
                f"- `Recovered By Stretch/Volume`: {data['volume_recovered']}",
                "",
            ]
        )

        if not data["reasons"]:
            lines.extend(["_No rejection reasons recorded._", ""])
            continue

        lines.append("| Reason | Count |")
        lines.append("| --- | ---: |")
        for reason, count in data["reasons"].items():
            lines.append(f"| {reason_labels.get(reason, reason)} | {count} |")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_rejection_breakdown_text(path, breakdown, *, ctx):
    reason_labels = {
        "location": "Wrong location",
        "physical_security": "Physical security / non-target role",
        "soc_title_mismatch": "Not a SOC-style title",
        "cyber_title_mismatch": "Not a cyber-analyst title",
        "it_title_mismatch": "Not an IT bridge / helpdesk title",
        "entry_level_cyber_gate": "Fails entry-level cyber gate",
        "weak_fit": "Weak fit / resume overlap",
        "final_score_too_low": "Score too low after realism checks",
        "main_shortlist_threshold": "Only recovered by stretch / volume rules",
    }

    lines = [
        f"Generated on {ctx.TODAY}.",
        f"Location mode: {ctx.LOCATION_MODE_LABELS.get(ctx.LOCATION_MODE, ctx.LOCATION_MODE)}.",
        "",
    ]
    for _, data in breakdown.items():
        lines.append(f"===== {data['track_label']} =====")
        lines.append(f"Total Jobs Checked: {data['total_jobs']}")
        lines.append(f"Primary Candidates: {data['primary_candidates']}")
        lines.append(f"Rejected Before Main Shortlist: {data['standard_rejected']}")
        lines.append(f"Recovered By Stretch/Volume: {data['volume_recovered']}")
        lines.append("")
        for reason, count in data["reasons"].items():
            lines.append(f"{ctx.shorten(reason_labels.get(reason, reason), 42):<42} {count:>6}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def get_title_family(title, *, ctx):
    title = (title or "").lower()
    family_patterns = [
        ("soc_analyst", [r"\bsoc analyst\b", r"\bsecurity operations analyst\b"]),
        ("noc_analyst", [r"\bnoc analyst\b", r"\bnetwork operations? analyst\b"]),
        ("incident_response", [r"\bincident response\b", r"\bincident responder\b", r"\bdetection (?:and|&) response\b"]),
        ("threat_operations", [r"\bthreat operations? (?:analyst|specialist|associate)\b", r"\bmanaged detection (?:and|&) response\b", r"\bmdr analyst\b"]),
        ("threat_analyst", [r"\bthreat (?:intel(?:ligence)?|detection|response)? ?analyst\b", r"\bthreat hunting\b"]),
        ("security_analyst", [r"\bsecurity analyst\b", r"\bcyber(?:security)? analyst\b"]),
        ("identity_access", [r"\biam\b", r"\bidentity\b", r"\baccess (?:control|management|administration)?\b"]),
        ("trust_safety", [r"\btrust(?: |-)and(?: |-)safety\b"]),
        ("fraud_ops", [r"\bfraud (?:analyst|operations?|investigations?)\b"]),
        ("risk_grc", [r"\brisk\b", r"\bgrc\b", r"\bcompliance\b", r"\baudit\b"]),
        ("technical_support", [r"\btechnical support\b", r"\bsupport engineer\b", r"\bsupport specialist\b"]),
        ("application_support", [r"\bapplication support\b", r"\bapplication specialist\b"]),
        ("it_support", [r"\bit support\b", r"\bhelp ?desk\b", r"\bservice ?desk\b", r"\bdesktop support\b"]),
        ("it_ops", [r"\bit operations?\b", r"\bsystems?(?: administrator| admin)?\b", r"\bsaas administrator\b"]),
        ("security_engineer", [r"\bsecurity engineer\b", r"\bsoc engineer\b"]),
    ]
    for label, patterns in family_patterns:
        if ctx.matches_any_pattern(title, patterns):
            return label
    return "other"


def build_hit_report(normalized_jobs, ranked_jobs_by_track, resumes, *, ctx):
    company_hits = {}
    title_family_hits = {}
    near_miss_titles = {}

    primary_urls = {
        job["url"]
        for sections in ranked_jobs_by_track.values()
        for job in sections.get("primary", [])
    }
    stretch_urls = {
        job["url"]
        for sections in ranked_jobs_by_track.values()
        for job in sections.get("stretch", [])
    }

    for track_name in ctx.TRACKS:
        resume_text = ctx.get_resume_for_track(resumes, track_name)
        company_hits[track_name] = {}
        title_family_hits[track_name] = {}
        near_miss_titles[track_name] = {}

        for job in normalized_jobs:
            title_family = get_title_family(job.get("title"), ctx=ctx)
            company_name = job.get("company", "Unknown")
            source_type = job.get("source_type", "other")
            company_entry = company_hits[track_name].setdefault(
                company_name,
                {
                    "company": company_name,
                    "source_type": source_type,
                    "seen": 0,
                    "primary": 0,
                    "stretch": 0,
                    "near_miss": 0,
                },
            )
            company_entry["seen"] += 1

            family_entry = title_family_hits[track_name].setdefault(
                title_family,
                {"family": title_family, "seen": 0, "primary": 0, "stretch": 0, "near_miss": 0},
            )
            family_entry["seen"] += 1

            if job["url"] in primary_urls:
                company_entry["primary"] += 1
                family_entry["primary"] += 1
                continue

            if job["url"] in stretch_urls:
                company_entry["stretch"] += 1
                family_entry["stretch"] += 1
                continue

            reason = ctx.ranking.diagnose_track_rejection(
                job,
                track_name,
                resume_text,
                mode="standard",
                ctx=ctx,
            )
            if reason in {"weak_fit", "final_score_too_low", "entry_level_cyber_gate"}:
                company_entry["near_miss"] += 1
                family_entry["near_miss"] += 1
                title_entry = near_miss_titles[track_name].setdefault(
                    job["title"],
                    {"title": job["title"], "company": company_name, "reason": reason, "count": 0},
                )
                title_entry["count"] += 1

    return {
        "companies": company_hits,
        "title_families": title_family_hits,
        "near_miss_titles": near_miss_titles,
    }


def build_geo_ambiguous_cyber_leads(normalized_jobs, resumes, limit=8, *, ctx):
    leads = []
    seen_urls = set()

    for job in normalized_jobs:
        if not ctx.is_geo_ambiguous_us_region(job):
            continue
        if ctx.is_physical_security(f"{job['title_lc']} {job['description_lc']}"):
            continue

        for track_name in ("soc_analyst", "cyber_analyst"):
            title_lc = job["title_lc"]
            if track_name == "soc_analyst":
                if not ctx.is_target_soc_role_title(title_lc):
                    continue
            else:
                if not ctx.is_target_cyber_analyst_role_title(title_lc):
                    continue

            scoring_job = dict(job)
            scoring_job["location"] = "Remote - USA (geo-ambiguous original)"
            scoring_job["location_lc"] = scoring_job["location"].lower()
            scoring_job["is_remote"] = True
            scoring_job["combined_lc"] = (
                f"{scoring_job['title_lc']} {scoring_job['location_lc']} {scoring_job['description_lc']}"
            )

            ranked = ctx.ranking.build_ranked_job(
                scoring_job,
                track_name,
                ctx.get_resume_for_track(resumes, track_name),
                ctx=ctx,
            )
            if ranked is None:
                continue

            url = ranked.get("url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            ranked["location"] = job["location"]
            ranked["geo_ambiguous_note"] = (
                "Blocked from the strict queue because the posting location is geo-ambiguous, "
                "but it looks cyber-relevant enough to keep in view."
            )
            leads.append(ranked)

    return sort_jobs(leads)[:limit]


def write_hit_report_markdown(path, hit_report, *, ctx):
    lines = [
        "# Company and Title Hit Report",
        "",
        f"Generated on `{ctx.TODAY}`.",
        "",
        "This report shows which companies and title families are actually producing signal for each path tier, plus the closest near-miss titles.",
        "",
    ]

    for track_name, track in ctx.TRACKS.items():
        lines.append(f"## {track['label']}")
        lines.append("")

        companies = sorted(
            hit_report["companies"][track_name].values(),
            key=lambda item: (-item["primary"], -item["stretch"], -item["near_miss"], -item["seen"], item["company"]),
        )[:12]
        lines.append("### Best Company Yield")
        lines.append("")
        lines.append("| Company | Source | Seen | Main | Stretch | Near Miss |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
        for item in companies:
            lines.append(
                f"| {ctx.markdown_escape(item['company'])} | {item['source_type']} | {item['seen']} | {item['primary']} | {item['stretch']} | {item['near_miss']} |"
            )
        lines.append("")

        families = sorted(
            hit_report["title_families"][track_name].values(),
            key=lambda item: (-item["primary"], -item["stretch"], -item["near_miss"], -item["seen"], item["family"]),
        )[:12]
        lines.append("### Best Title Families")
        lines.append("")
        lines.append("| Title Family | Seen | Main | Stretch | Near Miss |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for item in families:
            lines.append(
                f"| {ctx.markdown_escape(item['family'])} | {item['seen']} | {item['primary']} | {item['stretch']} | {item['near_miss']} |"
            )
        lines.append("")

        near_misses = sorted(
            hit_report["near_miss_titles"][track_name].values(),
            key=lambda item: (-item["count"], item["title"]),
        )[:10]
        lines.append("### Closest Near Miss Titles")
        lines.append("")
        if not near_misses:
            lines.append("_No strong near misses right now._")
            lines.append("")
        else:
            for item in near_misses:
                lines.append(
                    f"- `{ctx.markdown_escape(item['title'])}` at `{ctx.markdown_escape(item['company'])}` | reason: `{item['reason']}` | count: `{item['count']}`"
                )
            lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_hit_report_text(path, hit_report, *, ctx):
    lines = [f"Generated on {ctx.TODAY}.", ""]
    for track_name, track in ctx.TRACKS.items():
        lines.append(f"===== {track['label']} =====")
        lines.append("")
        lines.append("Best Company Yield")
        for item in sorted(
            hit_report["companies"][track_name].values(),
            key=lambda x: (-x["primary"], -x["stretch"], -x["near_miss"], -x["seen"], x["company"]),
        )[:10]:
            lines.append(
                f"{ctx.shorten(item['company'], 28):<28} seen {item['seen']:>3} | main {item['primary']:>2} | stretch {item['stretch']:>2} | near {item['near_miss']:>2} | {item['source_type']}"
            )
        lines.append("")
        lines.append("Best Title Families")
        for item in sorted(
            hit_report["title_families"][track_name].values(),
            key=lambda x: (-x["primary"], -x["stretch"], -x["near_miss"], -x["seen"], x["family"]),
        )[:10]:
            lines.append(
                f"{ctx.shorten(item['family'], 24):<24} seen {item['seen']:>3} | main {item['primary']:>2} | stretch {item['stretch']:>2} | near {item['near_miss']:>2}"
            )
        lines.append("")
        lines.append("Closest Near Miss Titles")
        for item in sorted(
            hit_report["near_miss_titles"][track_name].values(),
            key=lambda x: (-x["count"], x["title"]),
        )[:8]:
            lines.append(
                f"{ctx.shorten(item['title'], 46):<46} {ctx.shorten(item['company'], 18):<18} {item['reason']}"
            )
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def sort_jobs(rows):
    decision_rank = {
        "APPLY (High ROI)": 0,
        "APPLY (Stretch)": 1,
        "APPLY (Low ROI)": 2,
        "BACKUP (Safe)": 3,
        "BACKUP (Competitive)": 4,
        "LOTTERY": 5,
    }
    return sorted(
        rows,
        key=lambda item: (
            decision_rank.get(item["decision"], 99),
            -item["freshness_score"],
            -item.get("entry_viability_score", 0),
            -item.get("target_signal_score", 0),
            -item["roi_score"],
            -item["final_score"],
            -item["fit_score"],
            -item.get("trajectory_score", 0),
            -item["narrative_score"],
            -item["execution_score"],
            -item["title_score"],
            -item["acceptance_score"],
            item["company"],
            item["title"],
        ),
    )


def split_primary_overflow_volume(rows, track_name, *, ctx):
    """Split ranked jobs into report sections with different trust levels.

    Primary is the clean shortlist. Stretch keeps competitive or reachy cyber
    roles visible. Overflow catches stale/disguised-mid-level jobs that may still
    matter. Volume is for pipeline analysis, not direct application priority.
    """
    ranked = sort_jobs(rows)
    primary_limit = ctx.MAX_RESULTS_PER_TRACK.get(track_name, 15)
    overflow_limit = ctx.OVERFLOW_RESULTS_PER_TRACK.get(track_name, 8)
    stretch_limit = ctx.STRETCH_RESULTS_PER_TRACK.get(track_name, 0)
    volume_limit = ctx.VOLUME_RESULTS_PER_TRACK.get(track_name, 20)

    primary_candidates = [
        job
        for job in ranked
        if not job.get("disguised_mid_level")
        and job.get("freshness_score", 50) > 30
        and (job.get("freshness_days_old") is None or job.get("freshness_days_old", 0) <= 60)
    ]
    primary = primary_candidates[:primary_limit]
    primary_urls = {job["url"] for job in primary}

    stretch = []
    stretch_urls = set()
    if ctx.is_cyber_track(track_name) and stretch_limit:
        stretch_candidates = [
            job
            for job in ranked
            if job["url"] not in primary_urls
            and (
                job["decision"] in {"APPLY (Stretch)", "APPLY (Low ROI)", "BACKUP (Competitive)", "LOTTERY"}
                or "engineer" in job["title"].lower()
                or job.get("company_difficulty") in {"stretch", "lottery"}
                or job.get("disguised_mid_level")
            )
        ]
        stretch = stretch_candidates[:stretch_limit]
        stretch_urls = {job["url"] for job in stretch}

    overflow_candidates = [
        job
        for job in ranked
        if job["url"] not in primary_urls
        and job["url"] not in stretch_urls
        and (
            job.get("disguised_mid_level")
            or job.get("freshness_score", 50) <= 30
            or (job.get("freshness_days_old") is not None and job.get("freshness_days_old", 0) > 60)
        )
    ]
    overflow = overflow_candidates[:overflow_limit]
    overflow_urls = {job["url"] for job in overflow}

    volume = [
        job
        for job in ranked
        if job["url"] not in primary_urls and job["url"] not in overflow_urls and job["url"] not in stretch_urls
    ][:volume_limit]

    return {
        "primary": primary,
        "stretch": stretch,
        "overflow": overflow,
        "volume": volume,
    }


def pick_internship_scouts(rows, existing_urls, track_name, *, ctx):
    ranked = sort_jobs(rows)
    picked = [job for job in ranked if job["url"] not in existing_urls]
    return picked[: ctx.INTERNSHIP_RESULTS_PER_TRACK.get(track_name, 8)]
