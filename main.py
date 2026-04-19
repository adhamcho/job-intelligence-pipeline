"""Main entrypoint for the job tool.

This file runs the full pipeline: collect jobs, clean them up, score them,
build the queue, and write the output files. The heaviest helper logic is split
into smaller modules so this file can stay focused on the overall flow.
"""

import csv
import datetime
import html
import json
import os
import re
import shutil
import sys
import textwrap
import time

from intake.collectors import collect_jobs_for_company, create_session
from sources.companies import COMPANIES, COMPANY_METADATA_BY_ID
from intake.aggregator_collectors import collect_jobs_for_aggregator_source
from sources.aggregator_sources import AGGREGATOR_SOURCES
from intake.extended_collectors import collect_jobs_for_extended_source
from sources.extended_sources import EXTENDED_SOURCES
from pipeline import queue_ops
from pipeline import diagnostics
from pipeline import core_helpers
from pipeline import bindings
from pipeline import config_data
from pipeline import evaluation
from pipeline import normalization
from pipeline import policy
from pipeline import ranking
from pipeline import reporting
from pipeline import runtime_ops
from pipeline import scoring_helpers
from pipeline import source_feedback
from pipeline import title_rules
from pipeline.scorer import score_job
from pipeline import tracker_ops
from shared.utils import normalize_company_id
from pipeline.config_data import (
    APPLY_THRESHOLD,
    EAST_COAST_LOCATION_TERMS,
    EFFORT_SIGNALS,
    EXECUTION_DEPTH_TERMS,
    HIDDEN_REQUIREMENT_SIGNALS,
    INTERNSHIP_RESULTS_PER_TRACK,
    LOCATION_MODE_LABELS,
    MAX_RESULTS_PER_TRACK,
    MIN_FINAL_SCORE,
    NARRATIVE_SIGNALS,
    NON_TARGET_REMOTE_TERMS,
    NY_LOCATION_TERMS,
    OVERFLOW_RESULTS_PER_TRACK,
    PRESTIGE_HEAVY_TAGS,
    PROJECT_BACKED_TERMS,
    REMOTE_LOCATION_TERMS,
    REQUEST_DELAY,
    RESULT_FILE_EXTENSIONS,
    STRETCH_RESULTS_PER_TRACK,
    TRACKS,
    UGLY_ENTRY_TAGS,
    US_WIDE_LOCATION_TERMS,
    VOLUME_RESULTS_PER_TRACK,
)

shorten = reporting.shorten
markdown_escape = reporting.markdown_escape

"""
`sys.modules[__name__]` gets the module object for this file (`main.py`).
`RANKING_CTX` and `DIAGNOSTICS_CTX` are variables that reference that `main.py` module object.
These are typically passed to modules in `pipeline/` (e.g., `ranking.py`, `diagnostics.py`)
so they can access shared config, data, and helper functions from `main.py`.
"""
RANKING_CTX = sys.modules[__name__]
DIAGNOSTICS_CTX = sys.modules[__name__]


# Installs helper functions from `bindings.py` into `main.py`'s global namespace.
# This allows calling helpers like `normalize()` and `dedupe_jobs()` directly
# without importing each one explicitly in this file.
bindings.install_bound_helpers(globals(), sys.modules[__name__])


# These are the main folders the project uses.
BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CURRENT_DIR = os.path.join(RESULTS_DIR, "current")
TRACKER_DIR = os.path.join(RESULTS_DIR, "tracker")
DIAGNOSTICS_DIR = os.path.join(RESULTS_DIR, "diagnostics")
ARCHIVE_DIR = os.path.join(RESULTS_DIR, "archive")
JOBS_ARCHIVE_DIR = os.path.join(ARCHIVE_DIR, "jobs_output")
REVIEWS_ARCHIVE_DIR = os.path.join(ARCHIVE_DIR, "ranking_review")
REJECTIONS_ARCHIVE_DIR = os.path.join(ARCHIVE_DIR, "rejection_breakdown")
# These store the date and time for this run.
TODAY = datetime.date.today().isoformat()
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M")
NOW_UTC = datetime.datetime.now(datetime.timezone.utc)
# This stores run info that gets printed in the reports later.
RUN_METADATA = {
    "generated_on": TODAY,
    "generated_at": "",
    "scrape_duration": "",
    "pool_summary": "",
    "pool_details": [],
    "response_summary": [],
    "run_id": TIMESTAMP,
}

OUTPUT_CSV_NAME = f"jobs_output_{TIMESTAMP}.csv"
OUTPUT_CSV_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_CSV_NAME)
LATEST_CSV_PATH = os.path.join(DIAGNOSTICS_DIR, "jobs_output.csv")

OUTPUT_REPORT_NAME = f"jobs_output_{TIMESTAMP}.txt"
OUTPUT_REPORT_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_REPORT_NAME)
LATEST_REPORT_PATH = os.path.join(DIAGNOSTICS_DIR, "jobs_output_report.txt")

OUTPUT_HTML_NAME = f"jobs_output_{TIMESTAMP}.html"
OUTPUT_HTML_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_HTML_NAME)
LATEST_HTML_PATH = os.path.join(DIAGNOSTICS_DIR, "jobs_output_report.html")

OUTPUT_MD_NAME = f"jobs_output_{TIMESTAMP}.md"
OUTPUT_MD_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_MD_NAME)
LATEST_MD_PATH = os.path.join(CURRENT_DIR, "jobs_output.md")
LEGACY_MD_REPORT_PATH = os.path.join(DIAGNOSTICS_DIR, "jobs_output_report.md")
OUTPUT_QUEUE_MD_NAME = f"apply_queue_{TIMESTAMP}.md"
OUTPUT_QUEUE_MD_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_QUEUE_MD_NAME)
LATEST_QUEUE_MD_PATH = os.path.join(CURRENT_DIR, "apply_queue.md")
OUTPUT_QUEUE_TXT_NAME = f"apply_queue_{TIMESTAMP}.txt"
OUTPUT_QUEUE_TXT_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_QUEUE_TXT_NAME)
LATEST_QUEUE_TXT_PATH = os.path.join(DIAGNOSTICS_DIR, "apply_queue.txt")
OUTPUT_BRIEFS_MD_NAME = f"application_briefs_{TIMESTAMP}.md"
OUTPUT_BRIEFS_MD_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_BRIEFS_MD_NAME)
LATEST_BRIEFS_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "application_briefs.md")
OUTPUT_BRIEFS_TXT_NAME = f"application_briefs_{TIMESTAMP}.txt"
OUTPUT_BRIEFS_TXT_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_BRIEFS_TXT_NAME)
LATEST_BRIEFS_TXT_PATH = os.path.join(DIAGNOSTICS_DIR, "application_briefs.txt")
OUTPUT_PACKETS_MD_NAME = f"application_packets_{TIMESTAMP}.md"
OUTPUT_PACKETS_MD_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_PACKETS_MD_NAME)
LATEST_PACKETS_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "application_packets.md")
OUTPUT_PACKETS_TXT_NAME = f"application_packets_{TIMESTAMP}.txt"
OUTPUT_PACKETS_TXT_PATH = os.path.join(JOBS_ARCHIVE_DIR, OUTPUT_PACKETS_TXT_NAME)
LATEST_PACKETS_TXT_PATH = os.path.join(DIAGNOSTICS_DIR, "application_packets.txt")
START_HERE_PATH = os.path.join(DIAGNOSTICS_DIR, "START_HERE.md")

OUTPUT_REVIEW_CSV_NAME = f"ranking_review_{TIMESTAMP}.csv"
OUTPUT_REVIEW_CSV_PATH = os.path.join(REVIEWS_ARCHIVE_DIR, OUTPUT_REVIEW_CSV_NAME)
LATEST_REVIEW_CSV_PATH = os.path.join(DIAGNOSTICS_DIR, "ranking_review.csv")

OUTPUT_REVIEW_MD_NAME = f"ranking_review_{TIMESTAMP}.md"
OUTPUT_REVIEW_MD_PATH = os.path.join(REVIEWS_ARCHIVE_DIR, OUTPUT_REVIEW_MD_NAME)
LATEST_REVIEW_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "ranking_review.md")

APPLICATION_TRACKER_PATH = os.path.join(TRACKER_DIR, "application_tracker.csv")
APPLICATION_TRACKER_REPORT_PATH = os.path.join(TRACKER_DIR, "application_tracker.txt")
APPLICATION_TRACKER_MD_PATH = os.path.join(TRACKER_DIR, "application_tracker.md")
OUTPUT_REJECTION_MD_NAME = f"rejection_breakdown_{TIMESTAMP}.md"
OUTPUT_REJECTION_MD_PATH = os.path.join(REJECTIONS_ARCHIVE_DIR, OUTPUT_REJECTION_MD_NAME)
LATEST_REJECTION_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "rejection_breakdown.md")
OUTPUT_REJECTION_TXT_NAME = f"rejection_breakdown_{TIMESTAMP}.txt"
OUTPUT_REJECTION_TXT_PATH = os.path.join(REJECTIONS_ARCHIVE_DIR, OUTPUT_REJECTION_TXT_NAME)
LATEST_REJECTION_TXT_PATH = os.path.join(DIAGNOSTICS_DIR, "rejection_breakdown.txt")
OUTPUT_HIT_MD_NAME = f"hit_report_{TIMESTAMP}.md"
OUTPUT_HIT_MD_PATH = os.path.join(REJECTIONS_ARCHIVE_DIR, OUTPUT_HIT_MD_NAME)
LATEST_HIT_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "hit_report.md")
OUTPUT_HIT_TXT_NAME = f"hit_report_{TIMESTAMP}.txt"
OUTPUT_HIT_TXT_PATH = os.path.join(REJECTIONS_ARCHIVE_DIR, OUTPUT_HIT_TXT_NAME)
LATEST_HIT_TXT_PATH = os.path.join(DIAGNOSTICS_DIR, "hit_report.txt")
COMPANY_EFFECTIVENESS_PATH = os.path.join(DIAGNOSTICS_DIR, "company_effectiveness.json")
SOURCE_HEALTH_MD_PATH = os.path.join(DIAGNOSTICS_DIR, "source_health.md")

# These settings are for caching and saved source history.
CACHE_PATH = os.path.join(BASE_DIR, "jobs_cache.json")
CACHE_VERSION = 3
EFFECTIVENESS_VERSION = 1
# These signatures help the program tell whether the source lists changed.
COMPANY_SIGNATURE = json.dumps(
    [
        {
            "id": company["id"],
            "name": company["name"],
            "type": company["type"],
            "board": company["board"],
            "group": company["group"],
        }
        for company in COMPANIES
    ],
    sort_keys=True,
)
EXTENDED_SOURCE_SIGNATURE = json.dumps(
    [source for source in EXTENDED_SOURCES],
    sort_keys=True,
)
AGGREGATOR_SOURCE_SIGNATURE = json.dumps(
    [source for source in AGGREGATOR_SOURCES],
    sort_keys=True,
)
COMPANY_EFFECTIVENESS = {}
DEAD_EXTENDED_SOURCE_MIN_RUNS = 4
DEAD_SOURCE_RECHECK_EVERY_RUNS = 30

# This chooses the location rule for the run.
LOCATION_MODE = os.environ.get("JOB_TOOL_LOCATION_MODE", "nyc_strict").strip().lower()
# This tells the program where each live result file should go.
RESULT_DESTINATIONS = {
    "jobs_output.csv": LATEST_CSV_PATH,
    "jobs_output.md": LATEST_MD_PATH,
    "apply_queue.md": LATEST_QUEUE_MD_PATH,
    "apply_queue.txt": LATEST_QUEUE_TXT_PATH,
    "application_briefs.md": LATEST_BRIEFS_MD_PATH,
    "application_briefs.txt": LATEST_BRIEFS_TXT_PATH,
    "application_packets.md": LATEST_PACKETS_MD_PATH,
    "application_packets.txt": LATEST_PACKETS_TXT_PATH,
    "START_HERE.md": START_HERE_PATH,
    "jobs_output_report.txt": LATEST_REPORT_PATH,
    "jobs_output_report.html": LATEST_HTML_PATH,
    "jobs_output_report.md": LEGACY_MD_REPORT_PATH,
    "ranking_review.csv": LATEST_REVIEW_CSV_PATH,
    "ranking_review.md": LATEST_REVIEW_MD_PATH,
    "application_tracker.csv": APPLICATION_TRACKER_PATH,
    "application_tracker.txt": APPLICATION_TRACKER_REPORT_PATH,
    "application_tracker.md": APPLICATION_TRACKER_MD_PATH,
    "rejection_breakdown.md": LATEST_REJECTION_MD_PATH,
    "rejection_breakdown.txt": LATEST_REJECTION_TXT_PATH,
    "hit_report.md": LATEST_HIT_MD_PATH,
    "hit_report.txt": LATEST_HIT_TXT_PATH,
    "company_effectiveness.json": COMPANY_EFFECTIVENESS_PATH,
    "source_health.md": SOURCE_HEALTH_MD_PATH,
}


# Everything above `main()` is setup code.
# It defines helpers, folders, file names, dates, and config values.
# The real pipeline flow starts inside `main()`.

def main():
    global COMPANY_EFFECTIVENESS

    # This prevents Windows console encoding errors when job titles or
    # locations contain characters outside plain ASCII.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        
    only_remote = "--only-remote" in sys.argv

    # Setup phase: make sure folders exist, move older files into the current
    # layout, and load saved inputs from disk.
    migrate_existing_results()
    COMPANY_EFFECTIVENESS = load_company_effectiveness()
    resumes = load_resumes()

    # Intake phase: pull raw jobs from all configured sources and remember how
    # long the scrape took for the report header.
    scrape_started_at = time.perf_counter()
    raw_jobs = collect_jobs()
    scrape_duration_seconds = time.perf_counter() - scrape_started_at
    source_mix = summarize_source_mix(raw_jobs)
    update_run_metadata(scrape_duration_seconds, source_mix)
    structured_count = source_mix["structured_count"]
    extended_count = source_mix["extended_count"]
    aggregator_count = source_mix["aggregator_count"]
    print(
        f"\nCollected {len(raw_jobs)} raw jobs "
        f"({structured_count} structured, {extended_count} extended, {aggregator_count} aggregator)",
        flush=True,
    )

    # Normalize once here so every later step sees the same cleaned job shape.
    # Dedupe means "remove duplicates" so one posting does not get ranked twice.
    # Normalizes every raw job into a consistent format, then removes duplicates, 
    # and stores the final cleaned list in normalized_jobs.
    normalized_jobs = dedupe_jobs([normalize(job) for job in raw_jobs])
    if only_remote:
        normalized_jobs = [job for job in normalized_jobs if job.get("is_remote")]
    ranked_jobs_by_track = {
        track_name: {"primary": [], "stretch": [], "overflow": [], "volume": [], "internships": []}
        for track_name in TRACKS
    }
    ranked_candidates_by_track = {track_name: [] for track_name in TRACKS}
    volume_candidates_by_track = {track_name: [] for track_name in TRACKS}
    internship_candidates_by_track = {track_name: [] for track_name in TRACKS}

    # Ranking phase: test every cleaned job against every lane.
    # A lane here means one target path, like SOC, cyber bridge, or IT bridge.
    for job in normalized_jobs:
        for track_name in TRACKS:
            resume_text = get_resume_for_track(resumes, track_name)
            ranked_job = ranking.build_ranked_job(job, track_name, resume_text, ctx=RANKING_CTX)
            if ranked_job is None:
                ranked_job = ranking.build_ranked_job(
                    job,
                    track_name,
                    resume_text,
                    mode="volume",
                    ctx=RANKING_CTX,
                )
                if ranked_job is not None:
                    volume_candidates_by_track[track_name].append(ranked_job)
            else:
                ranked_candidates_by_track[track_name].append(ranked_job)

            internship_job = ranking.build_ranked_job(
                job,
                track_name,
                resume_text,
                mode="internship",
                ctx=RANKING_CTX,
            )
            if internship_job is not None:
                internship_candidates_by_track[track_name].append(internship_job)

    # Selection phase: turn the full ranked candidate pool into smaller sections
    # the reports can show, like primary, overflow, volume, and internships.
    for track_name in TRACKS:
        sections = diagnostics.split_primary_overflow_volume(
            ranked_candidates_by_track[track_name],
            track_name,
            ctx=DIAGNOSTICS_CTX,
        )
        primary_and_overflow_urls = {
            job["url"]
            for section_name in ("primary", "stretch", "overflow")
            for job in sections[section_name]
        }
        extra_volume = [
            job
            for job in diagnostics.sort_jobs(volume_candidates_by_track[track_name])
            if job["url"] not in primary_and_overflow_urls
        ]
        sections["volume"] = (sections["volume"] + extra_volume)[: VOLUME_RESULTS_PER_TRACK.get(track_name, 20)]
        existing_urls = {
            job["url"]
            for section_name in ("primary", "stretch", "overflow", "volume")
            for job in sections.get(section_name, [])
        }
        sections["internships"] = diagnostics.pick_internship_scouts(
            internship_candidates_by_track[track_name],
            existing_urls,
            track_name,
            ctx=DIAGNOSTICS_CTX,
        )
        ranked_jobs_by_track[track_name] = sections

    # Feedback phase: update the saved memory about which sources keep producing
    # useful jobs, then refresh the tracker and diagnostics.
    update_company_effectiveness(normalized_jobs, ranked_jobs_by_track)
    COMPANY_EFFECTIVENESS = load_company_effectiveness()
    source_feedback.write_source_health_report(SOURCE_HEALTH_MD_PATH, ctx=sys.modules[__name__])
    tracker_ops.sync_application_tracker(
        ranked_jobs_by_track,
        tracks=TRACKS,
        today=TODAY,
        tracker_csv_path=APPLICATION_TRACKER_PATH,
        tracker_text_path=APPLICATION_TRACKER_REPORT_PATH,
        tracker_md_path=APPLICATION_TRACKER_MD_PATH,
        run_metadata=RUN_METADATA,
        contains_any=contains_any,
        shorten=reporting.shorten,
        markdown_escape=reporting.markdown_escape,
    )
    rejection_breakdown = diagnostics.build_rejection_breakdown(normalized_jobs, resumes, ctx=DIAGNOSTICS_CTX)
    hit_report = diagnostics.build_hit_report(normalized_jobs, ranked_jobs_by_track, resumes, ctx=DIAGNOSTICS_CTX)
    geo_ambiguous_cyber_leads = diagnostics.build_geo_ambiguous_cyber_leads(
        normalized_jobs,
        resumes,
        ctx=DIAGNOSTICS_CTX,
    )
    apply_queue = queue_ops.build_apply_queue(
        ranked_jobs_by_track,
        today=TODAY,
        normalize_company_id=normalize_company_id,
        is_priority_queue_location=is_priority_queue_location,
        is_us_location=is_us_location,
        is_new_york_location=is_new_york_location,
        remote_location_terms=REMOTE_LOCATION_TERMS,
        ugly_entry_tags=UGLY_ENTRY_TAGS,
        get_freshness_priority_score=get_freshness_priority_score,
    )
    application_briefs = queue_ops.build_application_briefs(apply_queue)
    application_packets = queue_ops.build_application_packets(application_briefs)

    # Console summary: print a short human-readable view of the top jobs before
    # writing all the detailed files to disk.
    for track_name, track in TRACKS.items():
        print(f"\nTop jobs for {track['label']}:", flush=True)
        jobs = ranked_jobs_by_track[track_name]["primary"]

        if not jobs:
            print("No matches", flush=True)
            continue

        for job in jobs:
            print(
                f"{job['final_score']} | roi {job['roi_score']} | fit {job['fit_score']} | "
                f"acc {job['acceptance_score']} | exec {job['execution_score']} | story {job['narrative_score']} | {job['decision']} | "
                f"{job['company']} | {job['title']} | {job['location']}",
                flush=True,
            )

    # Output phase: write every report, queue, tracker view, and archive file.
    # The same ranked data gets written in several formats for different uses.
    reporting.write_markdown_report(
        OUTPUT_MD_PATH,
        ranked_jobs_by_track,
        tracks=TRACKS,
        run_metadata=RUN_METADATA,
        location_mode=LOCATION_MODE,
        location_mode_labels=LOCATION_MODE_LABELS,
        format_days_old=format_days_old,
        geo_ambiguous_cyber_leads=geo_ambiguous_cyber_leads,
    )
    reporting.write_markdown_report(
        LATEST_MD_PATH,
        ranked_jobs_by_track,
        tracks=TRACKS,
        run_metadata=RUN_METADATA,
        location_mode=LOCATION_MODE,
        location_mode_labels=LOCATION_MODE_LABELS,
        format_days_old=format_days_old,
        geo_ambiguous_cyber_leads=geo_ambiguous_cyber_leads,
    )
    reporting.write_markdown_report(
        LEGACY_MD_REPORT_PATH,
        ranked_jobs_by_track,
        tracks=TRACKS,
        run_metadata=RUN_METADATA,
        location_mode=LOCATION_MODE,
        location_mode_labels=LOCATION_MODE_LABELS,
        format_days_old=format_days_old,
        geo_ambiguous_cyber_leads=geo_ambiguous_cyber_leads,
    )
    queue_ops.write_apply_queue_markdown(
        OUTPUT_QUEUE_MD_PATH,
        apply_queue,
        run_metadata=RUN_METADATA,
        format_days_old=format_days_old,
        application_tracker_md_path=APPLICATION_TRACKER_MD_PATH,
        get_tracker_anchor_id=tracker_ops.get_tracker_anchor_id,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_apply_queue_markdown(
        LATEST_QUEUE_MD_PATH,
        apply_queue,
        run_metadata=RUN_METADATA,
        format_days_old=format_days_old,
        application_tracker_md_path=APPLICATION_TRACKER_MD_PATH,
        get_tracker_anchor_id=tracker_ops.get_tracker_anchor_id,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_application_briefs_markdown(
        OUTPUT_BRIEFS_MD_PATH,
        application_briefs,
        today=TODAY,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_application_briefs_markdown(
        LATEST_BRIEFS_MD_PATH,
        application_briefs,
        today=TODAY,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_application_packets_markdown(
        OUTPUT_PACKETS_MD_PATH,
        application_packets,
        today=TODAY,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_application_packets_markdown(
        LATEST_PACKETS_MD_PATH,
        application_packets,
        today=TODAY,
        markdown_escape=reporting.markdown_escape,
    )
    queue_ops.write_start_here(
        START_HERE_PATH,
        latest_queue_md_path=LATEST_QUEUE_MD_PATH,
        latest_briefs_md_path=LATEST_BRIEFS_MD_PATH,
        latest_packets_md_path=LATEST_PACKETS_MD_PATH,
        latest_md_path=LATEST_MD_PATH,
        application_tracker_md_path=APPLICATION_TRACKER_MD_PATH,
        latest_rejection_md_path=LATEST_REJECTION_MD_PATH,
    )
    reporting.write_review_markdown(OUTPUT_REVIEW_MD_PATH, ranked_jobs_by_track, tracks=TRACKS, today=TODAY)
    reporting.write_review_markdown(LATEST_REVIEW_MD_PATH, ranked_jobs_by_track, tracks=TRACKS, today=TODAY)
    reporting.write_review_csv(OUTPUT_REVIEW_CSV_PATH, ranked_jobs_by_track, tracks=TRACKS)
    reporting.write_review_csv(LATEST_REVIEW_CSV_PATH, ranked_jobs_by_track, tracks=TRACKS)
    diagnostics.write_rejection_breakdown_markdown(OUTPUT_REJECTION_MD_PATH, rejection_breakdown, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_rejection_breakdown_markdown(LATEST_REJECTION_MD_PATH, rejection_breakdown, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_rejection_breakdown_text(OUTPUT_REJECTION_TXT_PATH, rejection_breakdown, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_rejection_breakdown_text(LATEST_REJECTION_TXT_PATH, rejection_breakdown, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_hit_report_markdown(OUTPUT_HIT_MD_PATH, hit_report, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_hit_report_markdown(LATEST_HIT_MD_PATH, hit_report, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_hit_report_text(OUTPUT_HIT_TXT_PATH, hit_report, ctx=DIAGNOSTICS_CTX)
    diagnostics.write_hit_report_text(LATEST_HIT_TXT_PATH, hit_report, ctx=DIAGNOSTICS_CTX)
    reporting.write_csv(OUTPUT_CSV_PATH, ranked_jobs_by_track, tracks=TRACKS)
    reporting.write_csv(LATEST_CSV_PATH, ranked_jobs_by_track, tracks=TRACKS)
    reporting.write_text_report(OUTPUT_REPORT_PATH, ranked_jobs_by_track, tracks=TRACKS)
    reporting.write_text_report(LATEST_REPORT_PATH, ranked_jobs_by_track, tracks=TRACKS)
    queue_ops.write_apply_queue_text(
        OUTPUT_QUEUE_TXT_PATH,
        apply_queue,
        run_metadata=RUN_METADATA,
        format_days_old=format_days_old,
    )
    queue_ops.write_apply_queue_text(
        LATEST_QUEUE_TXT_PATH,
        apply_queue,
        run_metadata=RUN_METADATA,
        format_days_old=format_days_old,
    )
    queue_ops.write_application_briefs_text(
        OUTPUT_BRIEFS_TXT_PATH,
        application_briefs,
        today=TODAY,
    )
    queue_ops.write_application_briefs_text(
        LATEST_BRIEFS_TXT_PATH,
        application_briefs,
        today=TODAY,
    )
    queue_ops.write_application_packets_text(
        OUTPUT_PACKETS_TXT_PATH,
        application_packets,
        today=TODAY,
    )
    queue_ops.write_application_packets_text(
        LATEST_PACKETS_TXT_PATH,
        application_packets,
        today=TODAY,
    )
    reporting.write_html_report(
        OUTPUT_HTML_PATH,
        ranked_jobs_by_track,
        tracks=TRACKS,
        today=TODAY,
        location_mode=LOCATION_MODE,
        location_mode_labels=LOCATION_MODE_LABELS,
    )
    reporting.write_html_report(
        LATEST_HTML_PATH,
        ranked_jobs_by_track,
        tracks=TRACKS,
        today=TODAY,
        location_mode=LOCATION_MODE,
        location_mode_labels=LOCATION_MODE_LABELS,
    )

    # Final console lines show exactly which files were updated in this run.
    print(f"Saved Markdown: {OUTPUT_MD_PATH}", flush=True)
    print(f"Updated latest Markdown: {LATEST_MD_PATH}", flush=True)
    print(f"Updated compatibility Markdown: {LEGACY_MD_REPORT_PATH}", flush=True)
    print(f"Saved calibration Markdown: {OUTPUT_REVIEW_MD_PATH}", flush=True)
    print(f"Updated latest calibration Markdown: {LATEST_REVIEW_MD_PATH}", flush=True)
    print(f"Saved calibration CSV: {OUTPUT_REVIEW_CSV_PATH}", flush=True)
    print(f"Updated latest calibration CSV: {LATEST_REVIEW_CSV_PATH}", flush=True)
    print(f"Saved rejection Markdown: {OUTPUT_REJECTION_MD_PATH}", flush=True)
    print(f"Updated latest rejection Markdown: {LATEST_REJECTION_MD_PATH}", flush=True)
    print(f"Saved rejection text: {OUTPUT_REJECTION_TXT_PATH}", flush=True)
    print(f"Updated latest rejection text: {LATEST_REJECTION_TXT_PATH}", flush=True)
    print(f"Saved hit report Markdown: {OUTPUT_HIT_MD_PATH}", flush=True)
    print(f"Updated latest hit report Markdown: {LATEST_HIT_MD_PATH}", flush=True)
    print(f"Saved hit report text: {OUTPUT_HIT_TXT_PATH}", flush=True)
    print(f"Updated latest hit report text: {LATEST_HIT_TXT_PATH}", flush=True)
    print(f"Updated application tracker: {APPLICATION_TRACKER_PATH}", flush=True)
    print(f"Updated source health report: {SOURCE_HEALTH_MD_PATH}", flush=True)
    print(f"Saved CSV: {OUTPUT_CSV_PATH}", flush=True)
    print(f"Updated latest CSV: {LATEST_CSV_PATH}", flush=True)
    print(f"Saved report: {OUTPUT_REPORT_PATH}", flush=True)
    print(f"Updated latest report: {LATEST_REPORT_PATH}", flush=True)
    print(f"Saved HTML: {OUTPUT_HTML_PATH}", flush=True)
    print(f"Updated latest HTML: {LATEST_HTML_PATH}", flush=True)


if __name__ == "__main__":
    main()
