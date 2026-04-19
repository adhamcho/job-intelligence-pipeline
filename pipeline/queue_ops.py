"""Queue helpers for the job tool.

This file takes already-ranked jobs and turns them into the short action lists
the user actually reads, like Fast Lane, Daily Drop, and Apply Now.
"""

import datetime
import os


def build_apply_queue(
    jobs_by_track,
    *,
    today,
    normalize_company_id,
    is_priority_queue_location,
    is_us_location,
    is_new_york_location,
    remote_location_terms,
    ugly_entry_tags,
    get_freshness_priority_score,
):
    """Build the short application workflow from already-ranked jobs.

    This does not try to show every decent job. It prioritizes roles that are
    realistic to apply to now: preferred geography, stronger response likelihood,
    useful entry path, and freshness. That is why the queue can rank a boring
    support role above a shinier but lower-response cyber role.
    """
    seen_urls = set()
    queue = {
        "fast_lane": [],
        "daily_drop": [],
        "apply_now": [],
        "follow_up": [],
        "watchlist": [],
    }
    today_dt = datetime.date.fromisoformat(today)

    def parse_queue_date(value):
        try:
            return datetime.date.fromisoformat((value or "").strip())
        except ValueError:
            return None

    def is_due_for_follow_up(job):
        status = (job.get("application_status") or "").upper()
        if status not in {"APPLIED", "INTERVIEW"}:
            return False
        follow_up_dt = parse_queue_date(job.get("follow_up_on"))
        return bool(follow_up_dt and follow_up_dt <= today_dt)

    def queue_role_key(job):
        company_id = normalize_company_id(job.get("company") or job.get("company_id") or "")
        title = (job.get("title") or "").strip().lower()
        return (company_id, title)

    def queue_variant_sort_key(job):
        priority_location = 1 if is_priority_queue_location(job) else 0
        us_location = 1 if is_us_location(job) else 0
        remote_usa = 1 if (
            (job.get("is_remote") or any(term in (job.get("location_lc") or "") for term in remote_location_terms))
            and is_us_location(job)
        ) else 0
        new_york = 1 if is_new_york_location(job) else 0
        return (
            -priority_location,
            -new_york,
            -remote_usa,
            -us_location,
            -job.get("entry_viability_score", 0),
            -job.get("target_signal_score", 0),
            -job.get("trajectory_score", 0),
            -job.get("freshness_score", 0),
            -job.get("roi_score", 0),
            -job.get("final_score", 0),
            job.get("location", ""),
            job.get("url", ""),
        )

    def dedupe_queue_candidates(jobs):
        best_by_role = {}
        for job in jobs:
            key = queue_role_key(job)
            current = best_by_role.get(key)
            if current is None or queue_variant_sort_key(job) < queue_variant_sort_key(current):
                best_by_role[key] = job
        return list(best_by_role.values())

    def add_to_bucket(bucket_name, job):
        url = (job.get("url") or "").strip()
        if not url or url in seen_urls:
            return False
        queue[bucket_name].append(job)
        seen_urls.add(url)
        return True

    def is_queue_rescue_candidate(job):
        if not is_us_location(job):
            return False
        if (job.get("application_status") or "NEW").upper() != "NEW":
            return False
        if job.get("apply_priority_score", 0) >= 88:
            return True
        if (
            job.get("decision", "").startswith("APPLY")
            and job.get("entry_viability_score", 0) >= 82
            and job.get("response_likelihood_score", 0) >= 70
        ):
            return True
        return False

    apply_candidates = []
    for track_name in ("soc_analyst", "cyber_analyst", "it_bridge"):
        for section_name in ("primary", "stretch", "internships"):
            apply_candidates.extend(jobs_by_track.get(track_name, {}).get(section_name, []))
        for job in jobs_by_track.get(track_name, {}).get("overflow", []):
            if is_queue_rescue_candidate(job):
                apply_candidates.append({**job, "queue_note": "Queue rescue: strong stale-but-viable role kept visible"})
    apply_candidates = dedupe_queue_candidates(apply_candidates)

    def apply_now_sort_key(job):
        # Apply Now is sorted by best practical move, not highest prestige.
        # Location, apply priority, freshness, response odds, and entry viability
        # all beat pure final score here.
        preferred_location = 1 if is_priority_queue_location(job) else 0
        discovery_priority = 2 if job.get("discovery_state") == "NEW" else 1 if job.get("discovery_state") == "UPDATED" else 0
        freshness_priority = get_freshness_priority_score(job)
        return (
            -preferred_location,
            -job.get("apply_priority_score", 0),
            -discovery_priority,
            -freshness_priority,
            -job.get("response_likelihood_score", 0),
            -job.get("entry_viability_score", 0),
            -(job.get("target_signal_score", 0)),
            -job.get("trajectory_score", 0),
            -job.get("freshness_score", 0),
            -job.get("roi_score", 0),
            -job.get("final_score", 0),
            job.get("company", ""),
            job.get("title", ""),
        )

    def daily_drop_sort_key(job):
        preferred_location = 1 if is_priority_queue_location(job) else 0
        discovery_priority = 2 if job.get("discovery_state") == "NEW" else 1 if job.get("discovery_state") == "UPDATED" else 0
        freshness_priority = get_freshness_priority_score(job)
        return (
            -preferred_location,
            -job.get("apply_priority_score", 0),
            -discovery_priority,
            -freshness_priority,
            -job.get("response_likelihood_score", 0),
            -job.get("entry_viability_score", 0),
            -job.get("target_signal_score", 0),
            -job.get("trajectory_score", 0),
            -job.get("roi_score", 0),
            -job.get("final_score", 0),
            job.get("company", ""),
            job.get("title", ""),
        )

    def is_daily_drop_candidate(job):
        status = (job.get("application_status") or "NEW").upper()
        if status != "NEW":
            return False
        if not is_us_location(job):
            return False
        if job.get("discovery_state") not in {"NEW", "UPDATED"}:
            return False
        if job.get("entry_viability_score", 0) < 48 and job.get("response_likelihood_score", 0) < 55:
            return False
        if get_freshness_priority_score(job) < 45 and job.get("discovery_state") != "UPDATED":
            return False
        return True

    def is_fast_lane_candidate(job):
        status = (job.get("application_status") or "NEW").upper()
        if status != "NEW":
            return False
        if not is_us_location(job):
            return False
        if job.get("response_likelihood_score", 0) < 58:
            return False
        if job.get("entry_viability_score", 0) < 50:
            return False
        if job.get("apply_priority_score", 0) < 58:
            return False
        return True

    def is_forced_exposure_candidate(job):
        # Forced exposure keeps a few ugly/local/aggregator roles visible even
        # when their descriptions are messy. These roles can be less polished but
        # more likely to respond than brand-name structured ATS roles.
        tags = set(job.get("company_tags", []) or ())
        source_type = job.get("source_type")
        if not (ugly_entry_tags & tags or source_type in {"extended", "aggregator"}):
            return False
        if not is_us_location(job):
            return False
        if (job.get("application_status") or "NEW").upper() != "NEW":
            return False
        if source_type == "aggregator":
            if job.get("response_likelihood_score", 0) < 56:
                return False
            if job.get("entry_viability_score", 0) < 46:
                return False
            if get_freshness_priority_score(job) < 75:
                return False
            if job.get("final_score", 0) < 40:
                return False
        else:
            if job.get("response_likelihood_score", 0) < 68:
                return False
            if job.get("entry_viability_score", 0) < 52:
                return False
            if job.get("final_score", 0) < 44:
                return False
        return True

    fast_lane_added = 0
    for job in sorted(apply_candidates, key=apply_now_sort_key):
        if not is_fast_lane_candidate(job):
            continue
        if add_to_bucket("fast_lane", {**job, "queue_note": "Fast lane: strongest mix of response odds, viability, freshness, and speed"}):
            fast_lane_added += 1
        if fast_lane_added >= 5:
            break

    daily_added = 0
    for job in sorted(apply_candidates, key=daily_drop_sort_key):
        if not is_daily_drop_candidate(job):
            continue
        queue_note = (
            "Daily drop: newly surfaced and worth acting on today"
            if job.get("discovery_state") == "NEW"
            else "Daily drop: materially changed since the last run"
        )
        if add_to_bucket("daily_drop", {**job, "queue_note": queue_note}):
            daily_added += 1
        if daily_added >= 8:
            break

    if daily_added < 6:
        for job in sorted(apply_candidates, key=daily_drop_sort_key):
            status = (job.get("application_status") or "NEW").upper()
            if status != "NEW":
                continue
            if not is_us_location(job):
                continue
            if get_freshness_priority_score(job) < 45:
                continue
            if job.get("entry_viability_score", 0) < 52 and job.get("response_likelihood_score", 0) < 58:
                continue
            if add_to_bucket("daily_drop", {**job, "queue_note": "Daily drop: still one of the strongest jobs to act on today"}):
                daily_added += 1
            if daily_added >= 6:
                break

    for job in sorted(apply_candidates, key=apply_now_sort_key):
        status = (job.get("application_status") or "NEW").upper()
        if status != "NEW":
            continue
        if not is_us_location(job):
            continue
        preferred_location = is_priority_queue_location(job)
        if not (
            job.get("entry_viability_score", 0) >= 68
            or job.get("target_signal_score", 0) >= 18
            or (job.get("decision", "").startswith("APPLY") and job.get("entry_viability_score", 0) >= 58)
            or job.get("trajectory_score", 0) >= 72
            or (
                job.get("source_type") == "aggregator"
                and get_freshness_priority_score(job) >= 75
                and job.get("response_likelihood_score", 0) >= 60
            )
            or job.get("stepping_stone_label") in {"Entry via support", "Adjacent analyst bridge"}
        ):
            continue
        if job.get("source_type") == "aggregator":
            if job.get("entry_viability_score", 0) < 46 and job.get("response_likelihood_score", 0) < 60:
                continue
        elif job.get("entry_viability_score", 0) < 52:
            continue
        if not preferred_location:
            if not (
                (
                    job.get("fit_score", 0) >= 82
                    and job.get("trajectory_score", 0) >= 88
                    and job.get("final_score", 0) >= 74
                )
                or (
                    job.get("entry_viability_score", 0) >= 84
                    and job.get("final_score", 0) >= 70
                )
            ):
                continue
        add_to_bucket("apply_now", job)
        if len(queue["apply_now"]) >= 12:
            break

    exposure_candidates = []
    for track_name in ("soc_analyst", "cyber_analyst", "it_bridge"):
        for section_name in ("primary", "stretch", "overflow", "volume", "internships"):
            exposure_candidates.extend(jobs_by_track.get(track_name, {}).get(section_name, []))
    exposure_candidates = dedupe_queue_candidates(exposure_candidates)

    forced_added = 0
    for job in sorted(exposure_candidates, key=apply_now_sort_key):
        if not is_forced_exposure_candidate(job):
            continue
        if add_to_bucket("apply_now", {**job, "queue_note": "Forced exposure: ugly but viable role kept visible"}):
            forced_added += 1
        if forced_added >= 2:
            break

    aggregator_candidates = [
        job
        for job in exposure_candidates
        if job.get("source_type") == "aggregator"
        and is_us_location(job)
        and (job.get("application_status") or "NEW").upper() == "NEW"
    ]

    def aggregator_slot_sort_key(job):
        return (
            -job.get("apply_priority_score", 0),
            -get_freshness_priority_score(job),
            -job.get("entry_viability_score", 0),
            -job.get("response_likelihood_score", 0),
            -job.get("trajectory_score", 0),
            -job.get("final_score", 0),
            job.get("company", ""),
            job.get("title", ""),
        )

    forced_aggregator_added = 0
    for job in sorted(aggregator_candidates, key=aggregator_slot_sort_key):
        if get_freshness_priority_score(job) < 45:
            continue
        if job.get("entry_viability_score", 0) < 40 and job.get("response_likelihood_score", 0) < 56:
            continue
        if add_to_bucket("apply_now", {**job, "queue_note": "Forced aggregator slot: fresh messy discovery kept visible"}):
            forced_aggregator_added += 1
        if forced_aggregator_added >= 2:
            break

    for track_name in ("soc_analyst", "cyber_analyst", "it_bridge"):
        for section_name in ("primary", "stretch", "overflow", "volume", "internships"):
            for job in jobs_by_track.get(track_name, {}).get(section_name, []):
                if is_due_for_follow_up(job):
                    add_to_bucket("follow_up", job)

    watchlist_candidates = []
    for track_name in ("soc_analyst", "cyber_analyst", "it_bridge"):
        for section_name in ("primary", "stretch", "internships"):
            watchlist_candidates.extend(jobs_by_track.get(track_name, {}).get(section_name, []))
        for job in jobs_by_track.get(track_name, {}).get("overflow", []):
            if is_queue_rescue_candidate(job):
                watchlist_candidates.append({**job, "queue_note": "Watchlist rescue: strong stale-but-viable role kept visible"})
    watchlist_candidates = dedupe_queue_candidates(watchlist_candidates)

    for job in sorted(watchlist_candidates, key=apply_now_sort_key):
        status = (job.get("application_status") or "NEW").upper()
        if status in {"REJECTED", "WITHDRAWN"}:
            continue
        if not is_us_location(job):
            continue
        add_to_bucket("watchlist", job)
        if len(queue["watchlist"]) >= 10:
            break

    return queue


def build_application_briefs(queue):
    briefs = []
    seen_urls = set()

    section_labels = {
        "apply_now": "Apply Now",
        "follow_up": "Follow Up Due",
        "watchlist": "Watchlist",
    }

    for bucket_name in ("apply_now", "follow_up", "watchlist"):
        for job in queue.get(bucket_name, []):
            url = (job.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            matched = list(job.get("matched_skills", []))[:6]
            matched_critical = list(job.get("matched_critical_skills", []))[:4]
            missing = list(job.get("missing_skills", []))[:6]
            missing_critical = list(job.get("missing_critical_skills", []))[:4]

            lead_with = []
            if matched_critical:
                lead_with.append("Lead with critical overlap: " + ", ".join(matched_critical))
            elif matched:
                lead_with.append("Lead with direct overlap: " + ", ".join(matched[:4]))

            if job.get("trajectory_notes"):
                lead_with.append("Bridge angle: " + job["trajectory_notes"])

            if job.get("narrative_notes"):
                lead_with.append("Resume story: " + job["narrative_notes"])

            do_not_fake = []
            if missing_critical:
                do_not_fake.append("Do not overclaim: " + ", ".join(missing_critical))
            elif missing:
                do_not_fake.append("Be honest about lighter gaps: " + ", ".join(missing[:4]))

            prep_focus = []
            if job.get("execution_notes"):
                prep_focus.append(job["execution_notes"])
            if job.get("risk_notes"):
                prep_focus.append(job["risk_notes"])
            if job.get("acceptance_notes"):
                prep_focus.append(job["acceptance_notes"])

            next_step = "Apply now" if bucket_name == "apply_now" else "Follow up now" if bucket_name == "follow_up" else "Keep visible and revisit selectively"

            briefs.append(
                {
                    "section": section_labels[bucket_name],
                    "company": job["company"],
                    "title": job["title"],
                    "url": url,
                    "decision": job["decision"],
                    "location": job["location"],
                    "path_tier": job.get("path_tier", ""),
                    "resume": job.get("resume", ""),
                    "status": job.get("application_status", "NEW"),
                    "final_score": job["final_score"],
                    "roi_score": job["roi_score"],
                    "trajectory_score": job.get("trajectory_score", 0),
                    "target_signal_score": job.get("target_signal_score", 0),
                    "lead_with": lead_with[:3],
                    "do_not_fake": do_not_fake[:2],
                    "prep_focus": prep_focus[:3],
                    "matched_skills": matched,
                    "missing_skills": missing,
                    "next_step": next_step,
                }
            )

    return briefs


def build_application_packets(briefs):
    packets = []

    for brief in briefs:
        if brief["section"] != "Apply Now":
            continue

        matched = brief.get("matched_skills", [])[:4]
        missing = brief.get("missing_skills", [])[:3]
        matched_text = ", ".join(matched) if matched else "troubleshooting and technical support work"
        gap_text = ", ".join(missing) if missing else "any tool-specific gaps"

        first_sentence = (
            f"I am targeting this {brief['path_tier']} role because it lines up with the direction I am actively building toward: "
            f"more hands-on work with systems, troubleshooting, logs, and security-adjacent operations."
        )
        second_sentence = (
            f"My strongest overlap for this role is {matched_text}, and I would position myself as someone who can ramp quickly while being honest about lighter gaps like {gap_text}."
        )

        resume_focus = []
        if matched:
            resume_focus.append("Surface these skills early: " + ", ".join(matched))
        if brief.get("lead_with"):
            resume_focus.append(brief["lead_with"][0].replace("Lead with critical overlap: ", "").replace("Lead with direct overlap: ", "Open with: "))
        resume_focus.append("Keep the story centered on bridge value, not on pretending you already have the full destination title.")

        short_pitch = (
            f"I am interested in {brief['title']} at {brief['company']} because it looks like a strong next step into "
            f"more technical, systems-facing work. My background already gives me overlap in {matched_text}, and I can speak clearly "
            f"to why this role strengthens the path I am building toward."
        )

        packets.append(
            {
                "company": brief["company"],
                "title": brief["title"],
                "url": brief["url"],
                "location": brief["location"],
                "path_tier": brief["path_tier"],
                "resume": brief["resume"],
                "decision": brief["decision"],
                "status": brief["status"],
                "positioning_summary": [first_sentence, second_sentence],
                "resume_focus": resume_focus[:3],
                "short_pitch": short_pitch,
                "prep_focus": brief.get("prep_focus", [])[:3],
                "do_not_fake": brief.get("do_not_fake", [])[:2],
            }
        )

    return packets


def write_apply_queue_markdown(
    path,
    queue,
    *,
    run_metadata,
    format_days_old,
    application_tracker_md_path,
    get_tracker_anchor_id,
    markdown_escape,
):
    aggregator_hits = sum(
        1
        for bucket_name in ("fast_lane", "daily_drop", "apply_now", "watchlist")
        for job in queue.get(bucket_name, [])
        if job.get("source_type") == "aggregator"
    )
    lines = [
        "# Apply Queue",
        "",
        f"Last refresh: `{run_metadata['generated_at']}` | Run ID `{run_metadata['run_id']}`",
        "",
        f"Generated on `{run_metadata['generated_on']}` at `{run_metadata['generated_at']}` | Scrape time `{run_metadata['scrape_duration']}`.",
        (f"Pool: `{run_metadata['pool_summary']}`." if run_metadata.get("pool_summary") else ""),
        *[f"- {detail}" for detail in run_metadata.get("pool_details", [])],
        f"- Aggregator queue hits: `{aggregator_hits}`",
        *[f"- Response pulse: {detail}" for detail in run_metadata.get("response_summary", [])],
        "",
        "Freshness priority mode is on: newer and newly-changed viable jobs get pushed up hard.",
        "",
        "This queue is the practical path-in view: fast lane first, then daily drop, then apply-now targets, then due follow-ups, then a watchlist of strong bridge and internship options.",
        "",
    ]

    sections = [
        ("Fast Lane", "Highest-priority applications to send first when you want the fastest realistic path to a response, not just the prettiest role on paper.", queue.get("fast_lane", [])),
        ("Daily Drop", "Top jobs from this run that are new or meaningfully changed, with freshness weighted hard so you can decide what to apply to today.", queue.get("daily_drop", [])),
        ("Apply Now", "Best next applications to submit when you want the shortest path to action.", queue.get("apply_now", [])),
        ("Follow Up Due", "Roles you already touched that have a follow-up date due now or earlier.", queue.get("follow_up", [])),
        ("Watchlist", "Strong roles worth keeping visible, including applied jobs and selective stretch opportunities.", queue.get("watchlist", [])),
    ]

    for heading, intro, jobs in sections:
        lines.extend([f"## {heading}", "", intro, ""])
        if not jobs:
            lines.extend(["_No current matches right now._", ""])
            continue

        for index, job in enumerate(jobs, start=1):
            tracker_anchor = get_tracker_anchor_id({"Track": job.get("track", ""), "Company": job.get("company", ""), "Title": job.get("title", ""), "URL": job.get("url", "")})
            lines.extend(
                [
                    f"### {index}. [{markdown_escape(job['title'])}]({job['url']})",
                    "",
                    f"- `Company`: {markdown_escape(job['company'])}",
                    f"- `Decision`: {job['decision']}",
                    f"- `Final / ROI / Freshness`: {job['final_score']} / {job['roi_score']} / {job['freshness_label']} ({format_days_old(job.get('freshness_days_old'))})",
                    f"- `Apply Priority`: {job.get('apply_priority_score', '')}",
                    f"- `Entry Viability`: {job.get('entry_viability_score', '')}",
                    f"- `Response Likelihood`: {job.get('response_likelihood_score', '')}",
                    f"- `Target Signal`: {job.get('target_signal_score', '')}",
                    f"- `Trajectory`: {job.get('trajectory_score', '')}",
                    f"- `Path Tier`: {job.get('path_tier', '')}",
                    f"- `Stepping Stone`: {job.get('stepping_stone_label', '')}",
                    f"- `Resume To Use`: {job.get('resume', '')}",
                    f"- `Location`: {markdown_escape(job['location'])}",
                    f"- `Discovery`: {job.get('discovery_state', 'SEEN')}",
                    f"- `Update Reason`: {markdown_escape(job.get('update_reason') or 'None')}",
                    f"- `Tracker Entry`: [Open in tracker](../tracker/{os.path.basename(application_tracker_md_path)}#{tracker_anchor})",
                    f"- `Queue Note`: {markdown_escape(job.get('queue_note', 'Standard queue pick'))}",
                    f"- `Why It Is Here`: {markdown_escape(job.get('target_signal_notes') or job.get('trajectory_notes') or job.get('roi_notes') or job.get('narrative_notes') or job.get('fit_notes') or 'Strong bridge or early-career value')}",
                    f"- `Application Status`: {job.get('application_status', 'NEW')}",
                    "",
                ]
            )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_apply_queue_text(path, queue, *, run_metadata, format_days_old):
    aggregator_hits = sum(
        1
        for bucket_name in ("fast_lane", "daily_drop", "apply_now", "watchlist")
        for job in queue.get(bucket_name, [])
        if job.get("source_type") == "aggregator"
    )
    lines = [
        "APPLY QUEUE",
        f"Last refresh: {run_metadata['generated_at']} | Run ID {run_metadata['run_id']}",
        f"Generated on {run_metadata['generated_on']} at {run_metadata['generated_at']} | Scrape time {run_metadata['scrape_duration']}",
        f"Aggregator queue hits: {aggregator_hits}",
        *[f"Response pulse: {detail}" for detail in run_metadata.get("response_summary", [])],
        "",
        "Freshness priority mode is on.",
        "Practical path-in view: fast lane first, then daily drop, then apply-now targets, then due follow-ups, then a watchlist.",
        "",
    ]

    sections = [("FAST LANE", queue.get("fast_lane", [])), ("DAILY DROP", queue.get("daily_drop", [])), ("APPLY NOW", queue.get("apply_now", [])), ("FOLLOW UP DUE", queue.get("follow_up", [])), ("WATCHLIST", queue.get("watchlist", []))]

    for heading, jobs in sections:
        lines.extend([heading, "-" * len(heading)])
        if not jobs:
            lines.extend(["No current matches.", ""])
            continue

        for index, job in enumerate(jobs, start=1):
            lines.extend(
                [
                    f"{index}. {job['company']} | {job['title']}",
                    f"   Decision: {job['decision']}",
                    f"   Final/ROI/Freshness: {job['final_score']} / {job['roi_score']} / {job['freshness_label']} ({format_days_old(job.get('freshness_days_old'))})",
                    f"   Apply priority: {job.get('apply_priority_score', '')}",
                    f"   Target signal: {job.get('target_signal_score', '')}",
                    f"   Trajectory: {job.get('trajectory_score', '')}",
                    f"   Path Tier: {job.get('path_tier', '')}",
                    f"   Resume: {job.get('resume', '')}",
                    f"   Location: {job['location']}",
                    f"   Discovery: {job.get('discovery_state', 'SEEN')}",
                    f"   Status: {job.get('application_status', 'NEW')}",
                    f"   Link: {job['url']}",
                    "",
                ]
            )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_application_briefs_markdown(path, briefs, *, today, markdown_escape):
    lines = [
        "# Application Briefs",
        "",
        f"Generated on `{today}`.",
        "",
        "These briefs are the high-value prep layer for the current queue: how to position yourself, what not to fake, and what to prep before applying or following up.",
        "",
    ]

    current_section = None
    for brief in briefs:
        if brief["section"] != current_section:
            lines.extend([f"## {brief['section']}", ""])
            current_section = brief["section"]

        lines.extend(
            [
                f"### [{markdown_escape(brief['title'])}]({brief['url']})",
                "",
                f"- `Company`: {markdown_escape(brief['company'])}",
                f"- `Decision`: {brief['decision']}",
                f"- `Status`: {brief['status']}",
                f"- `Final / ROI / Trajectory`: {brief['final_score']} / {brief['roi_score']} / {brief['trajectory_score']}",
                f"- `Path Tier`: {brief['path_tier']}",
                f"- `Resume To Use`: {brief['resume']}",
                f"- `Location`: {markdown_escape(brief['location'])}",
                f"- `Next Step`: {brief['next_step']}",
                f"- `Matched Skills To Emphasize`: {markdown_escape(', '.join(brief['matched_skills'])) if brief['matched_skills'] else 'None'}",
                f"- `Gaps To Be Honest About`: {markdown_escape(', '.join(brief['missing_skills'])) if brief['missing_skills'] else 'None'}",
                "",
                "**Lead With**",
            ]
        )
        if brief["lead_with"]:
            lines.extend([f"- {markdown_escape(item)}" for item in brief["lead_with"]])
        else:
            lines.append("- Keep the story simple and direct.")
        lines.extend(["", "**Do Not Fake**"])
        if brief["do_not_fake"]:
            lines.extend([f"- {markdown_escape(item)}" for item in brief["do_not_fake"]])
        else:
            lines.append("- No major skill overclaim risk detected.")
        lines.extend(["", "**Prep Focus**"])
        if brief["prep_focus"]:
            lines.extend([f"- {markdown_escape(item)}" for item in brief["prep_focus"]])
        else:
            lines.append("- Light prep should be enough.")
        lines.append("")

    if not briefs:
        lines.extend(["No current briefs right now.", ""])

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_application_briefs_text(path, briefs, *, today):
    lines = [
        "APPLICATION BRIEFS",
        f"Generated on {today}",
        "",
        "High-value prep notes for the current queue.",
        "",
    ]

    current_section = None
    for brief in briefs:
        if brief["section"] != current_section:
            lines.extend([brief["section"].upper(), "-" * len(brief["section"])])
            current_section = brief["section"]

        lines.extend(
            [
                f"{brief['company']} | {brief['title']}",
                f"  Decision/Status: {brief['decision']} | {brief['status']}",
                f"  Scores: Final {brief['final_score']} | ROI {brief['roi_score']} | Trajectory {brief['trajectory_score']}",
                f"  Path/Resume/Location: {brief['path_tier']} | {brief['resume']} | {brief['location']}",
                f"  Next: {brief['next_step']}",
                f"  Emphasize: {', '.join(brief['matched_skills']) if brief['matched_skills'] else 'None'}",
                f"  Gaps: {', '.join(brief['missing_skills']) if brief['missing_skills'] else 'None'}",
                f"  Lead with: {' ; '.join(brief['lead_with']) if brief['lead_with'] else 'Keep the story simple and direct.'}",
                f"  Do not fake: {' ; '.join(brief['do_not_fake']) if brief['do_not_fake'] else 'No major skill overclaim risk detected.'}",
                f"  Prep: {' ; '.join(brief['prep_focus']) if brief['prep_focus'] else 'Light prep should be enough.'}",
                f"  Link: {brief['url']}",
                "",
            ]
        )

    if not briefs:
        lines.extend(["No current briefs right now.", ""])

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_application_packets_markdown(path, packets, *, today, markdown_escape):
    lines = [
        "# Application Packets",
        "",
        f"Generated on `{today}`.",
        "",
        "These packets are the fastest-usable application layer for `Apply Now` jobs: how to frame yourself, what to emphasize on the resume, and a short pitch you can adapt into an application answer or note.",
        "",
    ]

    if not packets:
        lines.extend(["No current application packets right now.", ""])
    else:
        for packet in packets:
            lines.extend(
                [
                    f"## [{markdown_escape(packet['title'])}]({packet['url']})",
                    "",
                    f"- `Company`: {markdown_escape(packet['company'])}",
                    f"- `Decision`: {packet['decision']}",
                    f"- `Status`: {packet['status']}",
                    f"- `Path Tier`: {packet['path_tier']}",
                    f"- `Resume To Use`: {packet['resume']}",
                    f"- `Location`: {markdown_escape(packet['location'])}",
                    "",
                    "**Positioning Summary**",
                ]
            )
            lines.extend([f"- {markdown_escape(item)}" for item in packet["positioning_summary"]])
            lines.extend(["", "**Resume Focus**"])
            lines.extend([f"- {markdown_escape(item)}" for item in packet["resume_focus"]])
            lines.extend(["", "**Short Pitch**", ""])
            lines.append(packet["short_pitch"])
            lines.extend(["", "**Prep Focus**"])
            if packet["prep_focus"]:
                lines.extend([f"- {markdown_escape(item)}" for item in packet["prep_focus"]])
            else:
                lines.append("- Light prep should be enough.")
            lines.extend(["", "**Do Not Fake**"])
            if packet["do_not_fake"]:
                lines.extend([f"- {markdown_escape(item)}" for item in packet["do_not_fake"]])
            else:
                lines.append("- No major overclaim risk detected.")
            lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_application_packets_text(path, packets, *, today):
    lines = [
        "APPLICATION PACKETS",
        f"Generated on {today}",
        "",
        "Fast-usable application framing for Apply Now jobs.",
        "",
    ]

    if not packets:
        lines.extend(["No current application packets right now.", ""])
    else:
        for packet in packets:
            lines.extend(
                [
                    f"{packet['company']} | {packet['title']}",
                    f"  Decision/Status: {packet['decision']} | {packet['status']}",
                    f"  Path/Resume/Location: {packet['path_tier']} | {packet['resume']} | {packet['location']}",
                    "  Positioning:",
                ]
            )
            lines.extend([f"    - {item}" for item in packet["positioning_summary"]])
            lines.append("  Resume focus:")
            lines.extend([f"    - {item}" for item in packet["resume_focus"]])
            lines.append(f"  Short pitch: {packet['short_pitch']}")
            lines.append("  Prep focus:")
            if packet["prep_focus"]:
                lines.extend([f"    - {item}" for item in packet["prep_focus"]])
            else:
                lines.append("    - Light prep should be enough.")
            lines.append("  Do not fake:")
            if packet["do_not_fake"]:
                lines.extend([f"    - {item}" for item in packet["do_not_fake"]])
            else:
                lines.append("    - No major overclaim risk detected.")
            lines.append(f"  Link: {packet['url']}")
            lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_start_here(path, *, latest_queue_md_path, latest_briefs_md_path, latest_packets_md_path, latest_md_path, application_tracker_md_path, latest_rejection_md_path):
    lines = [
        "# Start Here",
        "",
        "Open the apply queue first if you want the shortest path to action.",
        "",
        f"- Primary file: [apply_queue.md]({os.path.basename(latest_queue_md_path)})",
        f"- Prep briefs: [application_briefs.md]({os.path.basename(latest_briefs_md_path)})",
        f"- Application packets: [application_packets.md]({os.path.basename(latest_packets_md_path)})",
        f"- Full report: [jobs_output.md]({os.path.basename(latest_md_path)})",
        f"- Tracker: [application_tracker.md](../tracker/{os.path.basename(application_tracker_md_path)})",
        f"- Diagnostics: [rejection_breakdown.md](../diagnostics/{os.path.basename(latest_rejection_md_path)})",
        "",
        "Use the queue to decide what to apply to next. It is split into `Apply Now`, `Follow Up Due`, and `Watchlist` so you can act without rereading the whole report.",
        "Use the full report only when you want the explanation layer.",
        "",
    ]

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
