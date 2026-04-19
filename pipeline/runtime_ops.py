"""Runtime and setup helpers for the job tool.

This file handles project plumbing: folders, cache files, source summaries,
and the job collection loop that feeds the rest of the pipeline.
"""

import json
import os
import re
import shutil
import time


def ensure_results_dir(*, ctx):
    """Create the results folders the pipeline writes into."""
    os.makedirs(ctx.RESULTS_DIR, exist_ok=True)
    os.makedirs(ctx.CURRENT_DIR, exist_ok=True)
    os.makedirs(ctx.TRACKER_DIR, exist_ok=True)
    os.makedirs(ctx.DIAGNOSTICS_DIR, exist_ok=True)
    os.makedirs(ctx.ARCHIVE_DIR, exist_ok=True)
    os.makedirs(ctx.JOBS_ARCHIVE_DIR, exist_ok=True)
    os.makedirs(ctx.REVIEWS_ARCHIVE_DIR, exist_ok=True)
    os.makedirs(ctx.REJECTIONS_ARCHIVE_DIR, exist_ok=True)


def get_snapshot_archive_path(name, *, ctx):
    """Pick the archive folder for a dated output filename."""
    if re.match(r"^jobs_output_\d{8}_\d{4}\.(csv|txt|html|md)$", name):
        return os.path.join(ctx.JOBS_ARCHIVE_DIR, name)
    if re.match(r"^ranking_review_\d{8}_\d{4}\.(csv|md)$", name):
        return os.path.join(ctx.REVIEWS_ARCHIVE_DIR, name)
    if re.match(r"^rejection_breakdown_\d{8}_\d{4}\.(txt|md)$", name):
        return os.path.join(ctx.REJECTIONS_ARCHIVE_DIR, name)
    if re.match(r"^hit_report_\d{8}_\d{4}\.(txt|md)$", name):
        return os.path.join(ctx.REJECTIONS_ARCHIVE_DIR, name)
    return None


def get_result_destination_path(name, *, ctx):
    """Map a result filename to its current live or archive location."""
    if name in ctx.RESULT_DESTINATIONS:
        return ctx.RESULT_DESTINATIONS[name]
    return ctx.get_snapshot_archive_path(name)


def migrate_existing_results(*, ctx):
    """Move older output files into the current folder layout."""
    ctx.ensure_results_dir()

    search_roots = [os.path.dirname(ctx.BASE_DIR), ctx.BASE_DIR, ctx.RESULTS_DIR]
    for directory in search_roots:
        if not os.path.isdir(directory):
            continue

        for name in os.listdir(directory):
            source_path = os.path.join(directory, name)
            if not os.path.isfile(source_path):
                continue

            destination_path = ctx.get_result_destination_path(name)
            if not destination_path:
                continue

            if os.path.abspath(source_path) == os.path.abspath(destination_path):
                continue

            if os.path.exists(destination_path):
                try:
                    source_mtime = os.path.getmtime(source_path)
                    destination_mtime = os.path.getmtime(destination_path)
                except OSError:
                    continue

                if source_mtime <= destination_mtime:
                    os.remove(source_path)
                    continue

                os.replace(source_path, destination_path)
                continue

            shutil.move(source_path, destination_path)


def load_resumes(*, ctx):
    """Load the saved resume text for each track."""
    required_files = [
        "resume_it_support.txt",
        "resume_cyber.txt",
    ]
    missing_files = [name for name in required_files if not os.path.exists(os.path.join(ctx.BASE_DIR, name))]
    if missing_files:
        missing_list = ", ".join(missing_files)
        raise FileNotFoundError(
            "Missing private resume input file(s): "
            f"{missing_list}\n\n"
            "Create them from the public-safe templates, then edit the new files with your real resume text:\n"
            "  Copy-Item resume_cyber.example.txt resume_cyber.txt\n"
            "  Copy-Item resume_it_support.example.txt resume_it_support.txt\n\n"
            "The real resume files are ignored by Git, so they stay private."
        )

    with open(os.path.join(ctx.BASE_DIR, "resume_it_support.txt"), encoding="utf-8") as handle:
        it_support = handle.read()

    with open(os.path.join(ctx.BASE_DIR, "resume_cyber.txt"), encoding="utf-8") as handle:
        cyber = handle.read()

    return {
        "it_support": it_support,
        "cyber": cyber,
    }


def load_cache(*, ctx):
    """Return the saved raw-job pool if today's cache still matches the source setup."""
    if not os.path.exists(ctx.CACHE_PATH):
        return None

    try:
        with open(ctx.CACHE_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("date") != ctx.TODAY:
        return None

    if payload.get("cache_version") != ctx.CACHE_VERSION:
        return None

    if payload.get("company_signature") != ctx.COMPANY_SIGNATURE:
        return None

    if payload.get("extended_source_signature") != ctx.EXTENDED_SOURCE_SIGNATURE:
        return None

    if payload.get("aggregator_source_signature") != ctx.AGGREGATOR_SOURCE_SIGNATURE:
        return None

    return payload.get("jobs", [])


def save_cache(jobs, *, ctx):
    """Save today's raw-job pool so the pipeline can reuse it if needed."""
    payload = {
        "date": ctx.TODAY,
        "cache_version": ctx.CACHE_VERSION,
        "company_signature": ctx.COMPANY_SIGNATURE,
        "extended_source_signature": ctx.EXTENDED_SOURCE_SIGNATURE,
        "aggregator_source_signature": ctx.AGGREGATOR_SOURCE_SIGNATURE,
        "jobs": jobs,
    }

    with open(ctx.CACHE_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def load_company_effectiveness(*, ctx):
    """Load remembered source quality scores from previous runs."""
    if not os.path.exists(ctx.COMPANY_EFFECTIVENESS_PATH):
        return {}

    try:
        with open(ctx.COMPANY_EFFECTIVENESS_PATH, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    if payload.get("version") != ctx.EFFECTIVENESS_VERSION:
        return {}

    return payload.get("companies", {})


def save_company_effectiveness(companies, *, ctx):
    """Write the updated source quality scores back to disk."""
    payload = {
        "version": ctx.EFFECTIVENESS_VERSION,
        "updated_on": ctx.TODAY,
        "companies": companies,
    }

    with open(ctx.COMPANY_EFFECTIVENESS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def get_company_effectiveness_profile(company_id, *, ctx):
    """Turn stored company score data into simple labels and score bonuses."""
    company_id = ctx.normalize_company_id(company_id)
    stats = ctx.COMPANY_EFFECTIVENESS.get(company_id, {})
    score = int(round(stats.get("score", 50)))

    if score >= 72:
        return {"score": score, "label": "strong", "acceptance_bonus": 4, "roi_multiplier": 1.08}
    if score >= 60:
        return {"score": score, "label": "useful", "acceptance_bonus": 2, "roi_multiplier": 1.04}
    if score >= 45:
        return {"score": score, "label": "neutral", "acceptance_bonus": 0, "roi_multiplier": 1.0}
    if score >= 35:
        return {"score": score, "label": "weak", "acceptance_bonus": -2, "roi_multiplier": 0.97}
    return {"score": score, "label": "poor", "acceptance_bonus": -4, "roi_multiplier": 0.92}


def should_skip_external_source(source, *, ctx):
    """Skip sources that repeatedly produced no useful jobs.

    This keeps full runs faster without permanently deleting the source. Every
    N runs, the source is allowed through again so a recovered career board can
    re-enter the pipeline.
    """
    source_id = ctx.normalize_company_id(source.get("id"))
    if not source_id:
        return False, ""
    if source.get("type") == "workday":
        return False, ""
    if source.get("provider"):
        return False, ""

    stats = ctx.COMPANY_EFFECTIVENESS.get(source_id, {})
    total_runs = int(stats.get("total_runs", 0))
    total_raw_jobs = int(stats.get("total_raw_jobs", 0))
    total_shortlist_jobs = int(stats.get("total_shortlist_jobs", 0))
    recheck_every = max(1, int(getattr(ctx, "DEAD_SOURCE_RECHECK_EVERY_RUNS", 30)))

    if total_runs and total_runs % recheck_every == 0:
        return False, "periodic recheck"

    if total_runs >= ctx.DEAD_EXTENDED_SOURCE_MIN_RUNS and total_raw_jobs == 0:
        return True, f"{total_runs} straight runs with 0 jobs"

    if total_runs >= 6 and total_raw_jobs <= 3 and total_shortlist_jobs == 0:
        return True, "repeated low-yield source with no shortlist signal"

    return False, ""


def summarize_source_mix(raw_jobs, *, ctx):
    """Count how much of the raw pool came from each source family."""
    structured_sources = {"greenhouse": 0, "lever": 0, "ashby": 0}
    extended_sources = {}
    aggregator_sources = {}

    for job in raw_jobs:
        source = str(job.get("source", ""))
        if source in structured_sources:
            structured_sources[source] += 1
        elif source.startswith("extended:"):
            provider = source.split(":", 1)[1]
            extended_sources[provider] = extended_sources.get(provider, 0) + 1
        elif source.startswith("aggregator:"):
            provider = source.split(":", 1)[1]
            aggregator_sources[provider] = aggregator_sources.get(provider, 0) + 1

    structured_count = sum(structured_sources.values())
    extended_count = sum(extended_sources.values())
    aggregator_count = sum(aggregator_sources.values())

    summary = (
        f"{len(raw_jobs)} raw jobs = "
        f"{structured_count} structured, "
        f"{extended_count} extended, "
        f"{aggregator_count} aggregator"
    )

    def format_details(label, values):
        if not sum(values.values()):
            return f"{label}: none"
        parts = [f"{name} {count}" for name, count in values.items() if count]
        return f"{label}: " + " | ".join(parts)

    details = [
        format_details("Structured", structured_sources),
        format_details("Extended", dict(sorted(extended_sources.items()))),
        format_details("Aggregator", dict(sorted(aggregator_sources.items()))),
    ]

    return {
        "summary": summary,
        "details": details,
        "structured_count": structured_count,
        "extended_count": extended_count,
        "aggregator_count": aggregator_count,
    }


def collect_jobs(*, ctx):
    """Pull jobs from every configured source into one raw pool."""
    print(f"Refreshing job results for {ctx.TODAY}", flush=True)

    session = ctx.create_session()
    collected_jobs = []
    total = len(ctx.COMPANIES)

    for index, company in enumerate(ctx.COMPANIES, start=1):
        should_skip, skip_reason = ctx.should_skip_external_source(company)
        if should_skip:
            print(
                f"[{index}/{total}] Skipping {company['name']} from {company['type']} ({skip_reason})",
                flush=True,
            )
            continue
        print(
            f"[{index}/{total}] Collecting {company['name']} from {company['type']}...",
            flush=True,
        )
        jobs = ctx.collect_jobs_for_company(company, session=session)
        print(f"  Found {len(jobs)} jobs", flush=True)
        collected_jobs.extend(jobs)
        time.sleep(ctx.REQUEST_DELAY)

    if ctx.EXTENDED_SOURCES:
        print("\nCollecting extended sources...", flush=True)
    for index, source in enumerate(ctx.EXTENDED_SOURCES, start=1):
        should_skip, skip_reason = ctx.should_skip_external_source(source)
        if should_skip:
            print(
                f"[extended {index}/{len(ctx.EXTENDED_SOURCES)}] Skipping {source['name']} ({skip_reason})",
                flush=True,
            )
            continue
        print(
            f"[extended {index}/{len(ctx.EXTENDED_SOURCES)}] Collecting {source['name']} from {source['type']}...",
            flush=True,
        )
        jobs = ctx.collect_jobs_for_extended_source(source, session=session)
        print(f"  Found {len(jobs)} jobs", flush=True)
        collected_jobs.extend(jobs)
        time.sleep(ctx.REQUEST_DELAY)

    if ctx.AGGREGATOR_SOURCES:
        print("\nCollecting aggregator sources...", flush=True)
    for index, source in enumerate(ctx.AGGREGATOR_SOURCES, start=1):
        should_skip, skip_reason = ctx.should_skip_external_source(source)
        if should_skip:
            print(
                f"[aggregator {index}/{len(ctx.AGGREGATOR_SOURCES)}] Skipping {source['name']} ({skip_reason})",
                flush=True,
            )
            continue
        print(
            f"[aggregator {index}/{len(ctx.AGGREGATOR_SOURCES)}] Collecting {source['name']} from {source['provider']}...",
            flush=True,
        )
        jobs = ctx.collect_jobs_for_aggregator_source(source, session=session)
        print(f"  Found {len(jobs)} jobs", flush=True)
        collected_jobs.extend(jobs)
        time.sleep(ctx.REQUEST_DELAY)

    ctx.save_cache(collected_jobs)
    return collected_jobs


def update_run_metadata(scrape_duration_seconds, source_mix=None, *, ctx):
    """Store run timing and pool summary data for the output files."""
    local_now = ctx.datetime.datetime.now().astimezone()
    ctx.RUN_METADATA["generated_on"] = local_now.date().isoformat()
    ctx.RUN_METADATA["generated_at"] = local_now.strftime("%Y-%m-%d %I:%M:%S %p %Z")
    ctx.RUN_METADATA["scrape_duration"] = ctx.format_runtime(scrape_duration_seconds)
    ctx.RUN_METADATA["run_id"] = ctx.TIMESTAMP
    source_mix = source_mix or {}
    ctx.RUN_METADATA["pool_summary"] = source_mix.get("summary", "")
    ctx.RUN_METADATA["pool_details"] = list(source_mix.get("details", []))
