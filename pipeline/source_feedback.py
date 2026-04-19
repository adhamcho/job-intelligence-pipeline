"""Source feedback helpers for the job tool.

This file updates remembered source quality so the pipeline can learn which
companies and boards keep producing useful jobs.
"""

from pipeline import tracker_ops


def _known_source_rows(*, ctx):
    """Return one metadata row for every configured source."""
    rows = []
    seen_ids = set()

    for source in ctx.COMPANIES:
        rows.append(
            {
                "id": source["id"],
                "name": source["name"],
                "family": source["type"],
                "group": source.get("group", ""),
                "board": source.get("board", ""),
            }
        )
        seen_ids.add(source["id"])

    for source in ctx.EXTENDED_SOURCES:
        rows.append(
            {
                "id": source["id"],
                "name": source["name"],
                "family": f"extended:{source['type']}",
                "group": ", ".join(source.get("tags", [])),
                "board": source.get("url", ""),
            }
        )
        seen_ids.add(source["id"])

    # Aggregator feed configs are not the same thing as job companies.
    # For example, the Remotive feed can produce KnownHost jobs, but the job
    # quality score belongs to KnownHost, not the Remotive feed definition.
    for source_id, stats in ctx.COMPANY_EFFECTIVENESS.items():
        if source_id in seen_ids:
            continue
        if not str(source_id).startswith("aggregator:"):
            continue
        if not int(stats.get("total_raw_jobs", 0)) and not int(stats.get("total_shortlist_jobs", 0)):
            continue
        source_family = str(stats.get("source", "unknown"))
        if not source_family.startswith("aggregator:"):
            source_family = f"aggregator:{source_family}"
        rows.append(
            {
                "id": source_id,
                "name": stats.get("name", source_id),
                "family": source_family,
                "group": stats.get("group", "aggregator"),
                "board": stats.get("board", ""),
            }
        )

    return rows


def _source_health_label(stats):
    """Translate source metrics into a simple action label."""
    total_runs = int(stats.get("total_runs", 0))
    raw_jobs = int(stats.get("total_raw_jobs", 0))
    primary_jobs = int(stats.get("total_primary_jobs", 0))
    shortlist_jobs = int(stats.get("total_shortlist_jobs", 0))
    score = int(stats.get("score", 50))

    if total_runs >= 4 and raw_jobs == 0:
        return "dead or broken"
    if total_runs >= 6 and raw_jobs <= 3 and shortlist_jobs == 0:
        return "very low yield"
    if raw_jobs >= 200 and primary_jobs == 0:
        return "high noise"
    if primary_jobs >= 2 or score >= 72:
        return "keep investing"
    if shortlist_jobs:
        return "watch"
    return "unproven"


def write_source_health_report(path, *, ctx):
    """Write a diagnostics report showing which source lanes deserve attention next."""
    rows = []
    for source in _known_source_rows(ctx=ctx):
        stats = ctx.COMPANY_EFFECTIVENESS.get(source["id"], {})
        total_runs = int(stats.get("total_runs", 0))
        raw_jobs = int(stats.get("total_raw_jobs", 0))
        shortlist_jobs = int(stats.get("total_shortlist_jobs", 0))
        primary_jobs = int(stats.get("total_primary_jobs", 0))
        applied = int(stats.get("tracker_applied", 0))
        positive = int(stats.get("tracker_positive", 0))
        score = int(stats.get("score", 50))
        rows.append(
            {
                **source,
                "total_runs": total_runs,
                "raw_jobs": raw_jobs,
                "shortlist_jobs": shortlist_jobs,
                "primary_jobs": primary_jobs,
                "applied": applied,
                "positive": positive,
                "score": score,
                "label": _source_health_label(stats),
            }
        )

    def sort_by_signal(row):
        return (
            row["label"] != "keep investing",
            -row["primary_jobs"],
            -row["shortlist_jobs"],
            -row["score"],
            row["name"],
        )

    def sort_by_problem(row):
        problem_order = {
            "dead or broken": 0,
            "very low yield": 1,
            "high noise": 2,
            "unproven": 3,
            "watch": 4,
            "keep investing": 5,
        }
        return (
            problem_order.get(row["label"], 99),
            -row["raw_jobs"],
            row["name"],
        )

    keep_investing = [row for row in sorted(rows, key=sort_by_signal) if row["label"] == "keep investing"]
    needs_attention = [row for row in sorted(rows, key=sort_by_problem) if row["label"] in {"dead or broken", "very low yield", "high noise"}]
    unproven = [row for row in sorted(rows, key=lambda row: (row["family"], row["name"])) if row["label"] == "unproven"]

    def line_for(row):
        return (
            f"- `{row['label']}` | `{row['name']}` | `{row['family']}` | "
            f"raw `{row['raw_jobs']}` | shortlist `{row['shortlist_jobs']}` | "
            f"primary `{row['primary_jobs']}` | source score `{row['score']}` | "
            f"tracker `{row['applied']} applied / {row['positive']} positive`"
        )

    lines = [
        "# Source Health Report",
        "",
        f"Updated on `{ctx.TODAY}`.",
        "",
        "This report helps decide where to expand, fix, or stop spending source effort.",
        "",
        "## Summary",
        "",
        f"- Total tracked source/company records: `{len(rows)}`",
        f"- Keep investing: `{sum(1 for row in rows if row['label'] == 'keep investing')}`",
        f"- Watch: `{sum(1 for row in rows if row['label'] == 'watch')}`",
        f"- Unproven: `{sum(1 for row in rows if row['label'] == 'unproven')}`",
        f"- Needs attention: `{len(needs_attention)}`",
        "",
        "## Keep Investing",
        "",
        *(line_for(row) for row in keep_investing[:30]),
        "",
        "## Needs Attention",
        "",
        *(line_for(row) for row in needs_attention[:40]),
        "",
        "## Unproven Sources",
        "",
        *(line_for(row) for row in unproven[:40]),
        "",
        "## How To Use This",
        "",
        "- Add more sources that resemble `keep investing` rows.",
        "- Fix or remove `dead or broken` rows if they are supposed to matter.",
        "- Treat `high noise` rows carefully: they add volume but may not improve the apply queue.",
        "- Tracker outcomes become more useful after more applications are marked in the tracker.",
    ]

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def build_tracker_outcome_metrics(*, ctx):
    """Read past tracker outcomes so source quality can learn from real responses."""
    existing_rows = tracker_ops.load_application_tracker(
        ctx.APPLICATION_TRACKER_PATH,
        ctx.APPLICATION_TRACKER_MD_PATH,
    )
    metrics = {}

    for row in existing_rows.values():
        company_id = ctx.normalize_company_id(row.get("Company ID"))
        if not company_id:
            continue

        bucket = metrics.setdefault(
            company_id,
            {
                "applied": 0,
                "positive": 0,
                "interview": 0,
                "offer": 0,
                "rejected": 0,
            },
        )

        status = str(row.get("Status") or "").strip().upper()
        response = str(row.get("Response") or "").strip().lower()

        if status in {"APPLIED", "INTERVIEW", "OFFER", "REJECTED"}:
            bucket["applied"] += 1
        if status == "INTERVIEW":
            bucket["interview"] += 1
        if status == "OFFER":
            bucket["offer"] += 1
        if status == "REJECTED":
            bucket["rejected"] += 1

        if status in {"INTERVIEW", "OFFER"} or ctx.contains_any(
            response,
            ["interview", "screen", "callback", "recruiter", "positive", "offer"],
        ):
            bucket["positive"] += 1

    return metrics


def update_company_effectiveness(raw_jobs, jobs_by_track, *, ctx):
    """Update the saved source-quality scores based on this run's results."""
    current = ctx.load_company_effectiveness()
    tracker_outcomes = build_tracker_outcome_metrics(ctx=ctx)
    run_metrics = {}
    known_sources = {company["id"]: company for company in ctx.COMPANIES}
    known_sources.update({source["id"]: source for source in ctx.EXTENDED_SOURCES})
    known_sources.update({source["id"]: source for source in ctx.AGGREGATOR_SOURCES})

    for job in raw_jobs:
        company_id = ctx.normalize_company_id(job.get("company_id"))
        if not company_id:
            continue

        metrics = run_metrics.setdefault(
            company_id,
            {
                "name": job.get("company", ""),
                "group": job.get("company_group", "standard"),
                "source": job.get("source", "other"),
                "raw_jobs": 0,
                "shortlist_jobs": 0,
                "primary_jobs": 0,
                "overflow_jobs": 0,
                "volume_jobs": 0,
                "final_score_sum": 0,
                "roi_score_sum": 0,
            },
        )
        metrics["raw_jobs"] += 1

    for sections in jobs_by_track.values():
        for section_name in ("primary", "overflow", "volume"):
            for job in sections.get(section_name, []):
                company_id = ctx.normalize_company_id(job.get("company_id"))
                if not company_id:
                    continue

                metrics = run_metrics.setdefault(
                    company_id,
                    {
                        "name": job.get("company", ""),
                        "group": job.get("company_group", "standard"),
                        "source": job.get("source", "other"),
                        "raw_jobs": 0,
                        "shortlist_jobs": 0,
                        "primary_jobs": 0,
                        "overflow_jobs": 0,
                        "volume_jobs": 0,
                        "final_score_sum": 0,
                        "roi_score_sum": 0,
                    },
                )
                metrics["shortlist_jobs"] += 1
                metrics[f"{section_name}_jobs"] += 1
                metrics["final_score_sum"] += job.get("final_score", 0)
                metrics["roi_score_sum"] += job.get("roi_score", 0)

    for company_id, metrics in list(run_metrics.items()):
        if company_id in known_sources:
            continue
        known_sources[company_id] = {
            "id": company_id,
            "name": metrics.get("name", ""),
            "group": metrics.get("group", "aggregator"),
            "type": metrics.get("source", "other"),
            "url": "",
        }

    for company_id, source_meta in known_sources.items():
        existing = current.get(company_id, {})
        metrics = run_metrics.get(
            company_id,
            {
                "name": source_meta["name"],
                "group": source_meta.get("group", "extended"),
                "raw_jobs": 0,
                "shortlist_jobs": 0,
                "primary_jobs": 0,
                "overflow_jobs": 0,
                "volume_jobs": 0,
                "final_score_sum": 0,
                "roi_score_sum": 0,
            },
        )

        total_runs = int(existing.get("total_runs", 0)) + 1
        total_raw_jobs = int(existing.get("total_raw_jobs", 0)) + metrics["raw_jobs"]
        total_shortlist_jobs = int(existing.get("total_shortlist_jobs", 0)) + metrics["shortlist_jobs"]
        total_primary_jobs = int(existing.get("total_primary_jobs", 0)) + metrics["primary_jobs"]
        total_overflow_jobs = int(existing.get("total_overflow_jobs", 0)) + metrics["overflow_jobs"]
        total_volume_jobs = int(existing.get("total_volume_jobs", 0)) + metrics["volume_jobs"]
        total_final_score_sum = int(existing.get("total_final_score_sum", 0)) + metrics["final_score_sum"]
        total_roi_score_sum = int(existing.get("total_roi_score_sum", 0)) + metrics["roi_score_sum"]
        signal_runs = int(existing.get("signal_runs", 0)) + (1 if metrics["shortlist_jobs"] else 0)
        primary_signal_runs = int(existing.get("primary_signal_runs", 0)) + (1 if metrics["primary_jobs"] else 0)
        no_signal_runs = total_runs - signal_runs
        tracker_stats = tracker_outcomes.get(company_id, {})
        applied_count = int(tracker_stats.get("applied", 0))
        positive_count = int(tracker_stats.get("positive", 0))
        interview_count = int(tracker_stats.get("interview", 0))
        offer_count = int(tracker_stats.get("offer", 0))
        rejected_count = int(tracker_stats.get("rejected", 0))

        avg_shortlist_per_run = total_shortlist_jobs / max(1, total_runs)
        avg_primary_per_run = total_primary_jobs / max(1, total_runs)
        avg_final = total_final_score_sum / max(1, total_shortlist_jobs)
        avg_roi = total_roi_score_sum / max(1, total_shortlist_jobs)

        score = 50
        score += min(18, round(avg_primary_per_run * 8))
        score += min(10, round(avg_shortlist_per_run * 3))
        score += min(8, round((signal_runs / max(1, total_runs)) * 10))

        if avg_final >= 80:
            score += 6
        elif avg_final >= 72:
            score += 3
        elif total_shortlist_jobs and avg_final < 60:
            score -= 4

        if avg_roi >= 72:
            score += 5
        elif avg_roi >= 64:
            score += 2
        elif total_shortlist_jobs and avg_roi < 52:
            score -= 4

        if no_signal_runs >= 3:
            score -= min(16, no_signal_runs * 4)
        elif no_signal_runs == 2:
            score -= 7
        elif no_signal_runs == 1:
            score -= 3

        if total_runs >= 3 and total_primary_jobs == 0:
            score -= 6

        # Real tracker outcomes matter more than a source just looking good on paper.
        # A source that gets interviews or positive replies should climb even if its
        # titles are messy, while repeated applications with no response should cool it down.
        if applied_count:
            positive_rate = positive_count / max(1, applied_count)
            if offer_count:
                score += 12
            elif interview_count:
                score += 8
            elif positive_rate >= 0.4:
                score += 6
            elif positive_rate >= 0.2:
                score += 3
            elif positive_count == 0 and applied_count >= 3:
                score -= 8
            elif positive_count == 0 and applied_count >= 1:
                score -= 3

            if rejected_count >= 3 and positive_count == 0:
                score -= 4

        current[company_id] = {
            "company_id": company_id,
            "name": source_meta["name"],
            "group": source_meta.get("group", "aggregator" if source_meta.get("provider") else "extended"),
            "source": source_meta.get("type") or source_meta.get("provider", "other"),
            "board": source_meta.get("board", source_meta.get("url", "")),
            "total_runs": total_runs,
            "total_raw_jobs": total_raw_jobs,
            "total_shortlist_jobs": total_shortlist_jobs,
            "total_primary_jobs": total_primary_jobs,
            "total_overflow_jobs": total_overflow_jobs,
            "total_volume_jobs": total_volume_jobs,
            "total_final_score_sum": total_final_score_sum,
            "total_roi_score_sum": total_roi_score_sum,
            "signal_runs": signal_runs,
            "primary_signal_runs": primary_signal_runs,
            "last_seen": ctx.TODAY,
            "avg_shortlist_per_run": round(avg_shortlist_per_run, 2),
            "avg_primary_per_run": round(avg_primary_per_run, 2),
            "avg_final_score": round(avg_final, 2) if total_shortlist_jobs else 0,
            "avg_roi_score": round(avg_roi, 2) if total_shortlist_jobs else 0,
            "tracker_applied": applied_count,
            "tracker_positive": positive_count,
            "tracker_interview": interview_count,
            "tracker_offer": offer_count,
            "tracker_rejected": rejected_count,
            "score": max(20, min(90, int(round(score)))),
        }

    ctx.save_company_effectiveness(current)
