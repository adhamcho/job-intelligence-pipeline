"""Tracker helpers for the job tool.

This file reads and writes the application tracker so job status changes can
flow back into the queue and reports on the next run.
"""

import csv
import datetime
import hashlib
import os
import re


EDITABLE_TRACKER_FIELDS = ("Status", "Applied On", "Follow Up On", "Response", "Notes")

STATUS_PRIORITY = {
    "NEW": 0,
    "WITHDRAWN": 10,
    "APPLIED": 20,
    "REJECTED": 30,
    "INTERVIEW": 40,
    "OFFER": 50,
}


def status_rank(status):
    return STATUS_PRIORITY.get((status or "NEW").upper(), 0)


def build_url_level_application_state(existing):
    """Share application edits across duplicate tracker rows for the same job URL.

    The tracker keeps one row per URL + track because the same job can be scored
    differently for SOC, cyber, and IT bridge paths. The actual application state
    should still be per job URL, so marking one copy as APPLIED updates every copy
    of that job on the next run.
    """
    by_url = {}
    for (url, _track), row in existing.items():
        if not url:
            continue

        current = by_url.setdefault(url, {})
        if status_rank(row.get("Status")) > status_rank(current.get("Status")):
            current["Status"] = row.get("Status") or "NEW"

        for field in ("Applied On", "Follow Up On", "Response", "Notes"):
            if row.get(field) and not current.get(field):
                current[field] = row[field]

    return by_url


def load_application_tracker(tracker_csv_path, tracker_md_path):
    existing = {}

    if os.path.exists(tracker_csv_path):
        try:
            with open(tracker_csv_path, newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                existing = {
                    (
                        (row.get("URL") or "").strip(),
                        (row.get("Track") or "").strip(),
                    ): row
                    for row in reader
                    if (row.get("URL") or "").strip()
                }
        except OSError:
            existing = {}

    markdown_edits = load_application_tracker_markdown(tracker_md_path)
    for tracker_key, edited_row in markdown_edits.items():
        current = dict(existing.get(tracker_key, {}))
        current.update(edited_row)
        existing[tracker_key] = current

    return existing


def load_application_tracker_markdown(tracker_md_path):
    if not os.path.exists(tracker_md_path):
        return {}

    try:
        with open(tracker_md_path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return {}

    rows = {}
    current = None
    heading_pattern = re.compile(r"^#{2,3}\s+(?:\[(?P<title>.+?)\]\((?P<url>.+?)\)|(?P<plain>.+))$")
    field_pattern = re.compile(r"^- `(?P<field>[^`]+)`: (?P<value>.*)$")

    def normalize_md_value(field, value):
        value = value.strip()
        if field == "Applied On" and value == "Not yet":
            return ""
        if field == "Follow Up On" and value == "Not set":
            return ""
        if field in {"Response", "Notes"} and value == "None":
            return ""
        return value

    def finalize_current():
        nonlocal current
        if not current:
            return
        url = (current.get("URL") or "").strip()
        track = (current.get("Track") or "").strip()
        if url and track:
            rows[(url, track)] = current
        current = None

    for raw_line in lines:
        line = raw_line.rstrip()
        heading_match = heading_pattern.match(line)
        if heading_match:
            finalize_current()
            current = {
                "Title": heading_match.group("title") or heading_match.group("plain") or "",
                "URL": heading_match.group("url") or "",
            }
            continue

        if current is None:
            continue

        field_match = field_pattern.match(line)
        if not field_match:
            continue

        field = field_match.group("field")
        value = normalize_md_value(field, field_match.group("value"))
        if field == "Company":
            current["Company"] = value
        elif field == "Location":
            current["Location"] = value
        elif field == "Status":
            current["Status"] = value
        elif field == "Applied On":
            current["Applied On"] = value
        elif field == "Follow Up On":
            current["Follow Up On"] = value
        elif field == "Track":
            current["Track"] = value
        elif field == "Response":
            current["Response"] = value
        elif field == "Notes":
            current["Notes"] = value

    finalize_current()
    return rows


def tracker_sort_key(row):
    section_order = {
        "primary": 0,
        "stretch": 1,
        "internships": 2,
        "overflow": 3,
        "volume": 4,
    }
    return (
        -status_rank(row.get("Status")),
        section_order.get((row.get("Section") or "").lower(), 99),
        parse_sort_int(row.get("Current Rank")),
        row.get("Company", ""),
        row.get("Title", ""),
        row.get("Track", ""),
    )


def parse_sort_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 9999


def tracker_group_name(row):
    status = (row.get("Status") or "NEW").upper()
    section = (row.get("Section") or "").lower()
    if status in {"APPLIED", "INTERVIEW", "OFFER"}:
        return "Active / Applied"
    if status in {"REJECTED", "WITHDRAWN"}:
        return "Closed"
    if section in {"primary", "stretch", "internships"}:
        return "Main Queue Candidates"
    return "Lower Priority / Analysis Rows"


def get_tracker_source_bucket(row):
    company_id = str(row.get("Company ID") or "").lower()
    if company_id.startswith("aggregator:"):
        return "aggregator"
    if company_id.startswith("extended:"):
        return "extended"
    if company_id.startswith(("greenhouse:", "lever:", "ashby:")):
        return "structured"
    return "other"


def build_tracker_response_summary(rows, *, contains_any):
    buckets = {
        "structured": {"applied": 0, "positive": 0},
        "extended": {"applied": 0, "positive": 0},
        "aggregator": {"applied": 0, "positive": 0},
    }

    for row in rows:
        bucket = get_tracker_source_bucket(row)
        if bucket not in buckets:
            continue
        status = (row.get("Status") or "").strip().upper()
        response = (row.get("Response") or "").strip().lower()
        if status in {"APPLIED", "INTERVIEW", "OFFER"}:
            buckets[bucket]["applied"] += 1
        if status in {"INTERVIEW", "OFFER"} or contains_any(
            response,
            ["interview", "screen", "callback", "recruiter", "positive", "offer"],
        ):
            buckets[bucket]["positive"] += 1

    return [
        f"{bucket}: applied {stats['applied']} | positive responses {stats['positive']}"
        for bucket, stats in buckets.items()
    ]


def get_tracker_anchor_id(row):
    base = (
        f"{row.get('Track', '')}-"
        f"{row.get('Company', '')}-"
        f"{row.get('Title', '')}-"
        f"{row.get('URL', '')}"
    ).lower()
    anchor = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    # Similar jobs can share the same first 120 characters, so the hash makes
    # each tracker link unique while keeping the readable part of the anchor.
    unique_suffix = hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()[:10]
    readable_prefix = (anchor[:100].strip("-") or "tracker-entry")
    return f"{readable_prefix}-{unique_suffix}"


def write_application_tracker_text(path, rows, *, shorten):
    ordered_rows = sorted(rows, key=tracker_sort_key)
    lines = []
    header = (
        f"{'Company':<18} {'Title':<42} {'Status':<12} {'Applied':<10} "
        f"{'Follow Up':<10} {'Track':<14} {'Section':<10}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    for row in ordered_rows:
        lines.append(
            f"{shorten(row.get('Company', ''), 18):<18} "
            f"{shorten(row.get('Title', ''), 42):<42} "
            f"{shorten(row.get('Status', ''), 12):<12} "
            f"{shorten(row.get('Applied On', ''), 10):<10} "
            f"{shorten(row.get('Follow Up On', ''), 10):<10} "
            f"{shorten(row.get('Track', ''), 14):<14} "
            f"{shorten(row.get('Section', ''), 10):<10}"
        )
        lines.append(f"      URL: {row.get('URL', '')}")
        if row.get("Notes"):
            lines.append(f"      Notes: {row.get('Notes')}")
        if row.get("Response"):
            lines.append(f"      Response: {row.get('Response')}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_application_tracker_markdown(path, rows, *, today, markdown_escape):
    ordered_rows = sorted(rows, key=tracker_sort_key)
    lines = [
        "# Application Tracker",
        "",
        f"Updated on `{today}`.",
        "",
        "## Simplest Workflow",
        "",
        "1. Use the tracker link from `results/current/apply_queue.md` to jump to the exact job.",
        "2. Change the `Status` line from `NEW` to `APPLIED` for the job you applied to.",
        "3. Optionally change `Applied On`, `Follow Up On`, `Response`, or `Notes` here too.",
        "4. Run `main.py`.",
        "5. The tool will read your edits from this Markdown tracker and carry them into the queue, report, and CSV tracker.",
        "",
        "Only edit these fields here:",
        "- `Status`",
        "- `Applied On`",
        "- `Follow Up On`",
        "- `Response`",
        "- `Notes`",
        "",
        "Do not worry about editing the CSV unless you want to.",
        "",
        "If the same job appears under multiple tracks, edit any one copy. The next run will copy that application status to the other copies of the same job URL.",
        "",
    ]

    current_group = None
    for row in ordered_rows:
        group = tracker_group_name(row)
        if group != current_group:
            current_group = group
            lines.append(f"## {group}")
            lines.append("")

        title = markdown_escape(row.get("Title", "Untitled"))
        url = row.get("URL", "")
        anchor_id = get_tracker_anchor_id(row)
        lines.append(f'<a id="{anchor_id}"></a>')
        lines.append("")
        if url:
            lines.append(f"### [{title}]({url})")
        else:
            lines.append(f"### {title}")
        lines.append("")
        lines.extend(
            [
                f"- `Company`: {markdown_escape(row.get('Company', ''))}",
                f"- `Location`: {markdown_escape(row.get('Location', '')) if row.get('Location') else 'Unknown'}",
                f"- `Status`: {row.get('Status', '') or 'NEW'}",
                f"- `Applied On`: {row.get('Applied On', '') or 'Not yet'}",
                f"- `Follow Up On`: {row.get('Follow Up On', '') or 'Not set'}",
                f"- `Track`: {row.get('Track', '')}",
                f"- `Section`: {row.get('Section', '')}",
                f"- `Current Decision`: {row.get('Current Decision', '')}",
                f"- `Current Final / ROI`: {row.get('Current Final Score', '')} / {row.get('Current ROI Score', '')}",
                f"- `Freshness`: {row.get('Freshness', '')}",
                f"- `Response`: {markdown_escape(row.get('Response', '')) if row.get('Response') else 'None'}",
                f"- `Notes`: {markdown_escape(row.get('Notes', '')) if row.get('Notes') else 'None'}",
                "",
            ]
        )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def sync_application_tracker(
    jobs_by_track,
    *,
    tracks,
    today,
    tracker_csv_path,
    tracker_text_path,
    tracker_md_path,
    run_metadata,
    contains_any,
    shorten,
    markdown_escape,
):
    existing = load_application_tracker(tracker_csv_path, tracker_md_path)
    url_application_state = build_url_level_application_state(existing)
    synced_rows = []
    seen_urls = set()
    default_follow_up_on = (datetime.date.fromisoformat(today) + datetime.timedelta(days=7)).isoformat()

    def parse_tracker_int(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    for track_name, track in tracks.items():
        section_jobs = jobs_by_track.get(track_name, {})
        ordered_jobs = (
            section_jobs.get("primary", [])
            + section_jobs.get("stretch", [])
            + section_jobs.get("overflow", [])
            + section_jobs.get("volume", [])
            + section_jobs.get("internships", [])
        )
        for rank, job in enumerate(ordered_jobs, start=1):
            url = (job.get("url") or "").strip()
            if not url:
                continue

            tracker_key = (url, track_name)
            previous = existing.get(tracker_key, {})
            shared_application_state = url_application_state.get(url, {})
            current_decision = job["decision"]
            current_final_score = str(job["final_score"])
            current_roi_score = str(job["roi_score"])
            current_section = (
                "primary"
                if job in section_jobs.get("primary", [])
                else "stretch"
                if job in section_jobs.get("stretch", [])
                else "overflow"
                if job in section_jobs.get("overflow", [])
                else "volume"
                if job in section_jobs.get("volume", [])
                else "internships"
            )

            change_reasons = []
            if not previous:
                discovery_state = "NEW"
                change_reasons.append("new to tracker")
                updated_on = today
            else:
                previous_final = parse_tracker_int(previous.get("Current Final Score"))
                previous_roi = parse_tracker_int(previous.get("Current ROI Score"))
                if previous.get("Current Decision") and previous.get("Current Decision") != current_decision:
                    change_reasons.append("decision changed")
                if previous.get("Section") and previous.get("Section") != current_section:
                    change_reasons.append("section changed")
                if previous_final is not None and abs(job["final_score"] - previous_final) >= 5:
                    change_reasons.append("final score moved")
                if previous_roi is not None and abs(job["roi_score"] - previous_roi) >= 5:
                    change_reasons.append("roi moved")
                if (
                    previous.get("Freshness")
                    and previous.get("Freshness") != job["freshness_label"]
                    and job.get("freshness_score", 0) >= 80
                ):
                    change_reasons.append("freshness improved")
                if previous.get("Location") and previous.get("Location") != job.get("location", ""):
                    change_reasons.append("location changed")

                if (previous.get("Status") or "NEW").upper() != "NEW":
                    discovery_state = "TRACKED"
                elif change_reasons:
                    discovery_state = "UPDATED"
                else:
                    discovery_state = "SEEN"

                updated_on = (
                    today
                    if discovery_state in {"NEW", "UPDATED"}
                    else previous.get("Updated On") or previous.get("Added On") or today
                )

            tracker_row = {
                "URL": url,
                "Company ID": job.get("company_id", ""),
                "Company": job["company"],
                "Title": job["title"],
                "Location": previous.get("Location") or job.get("location", ""),
                "Track": track_name,
                "Track Label": track["label"],
                "Current Decision": current_decision,
                "Current Final Score": current_final_score,
                "Current ROI Score": current_roi_score,
                "Freshness": job["freshness_label"],
                "Section": current_section,
                "Current Rank": str(rank),
                "Last Seen": today,
                "Added On": previous.get("Added On") or today,
                "Updated On": updated_on,
                "Discovery State": discovery_state,
                "Update Reason": " | ".join(change_reasons) if change_reasons else "",
                "Status": shared_application_state.get("Status") or previous.get("Status") or "NEW",
                "Applied On": shared_application_state.get("Applied On") or previous.get("Applied On") or "",
                "Follow Up On": shared_application_state.get("Follow Up On") or previous.get("Follow Up On") or "",
                "Response": shared_application_state.get("Response") or previous.get("Response") or "",
                "Notes": shared_application_state.get("Notes") or previous.get("Notes") or "",
            }
            if tracker_row["Status"].upper() == "APPLIED" and not tracker_row["Follow Up On"]:
                tracker_row["Follow Up On"] = default_follow_up_on
            synced_rows.append(tracker_row)
            seen_urls.add(tracker_key)

            job["application_status"] = tracker_row["Status"]
            job["applied_on"] = tracker_row["Applied On"]
            job["follow_up_on"] = tracker_row["Follow Up On"]
            job["application_notes"] = tracker_row["Notes"]
            job["discovery_state"] = tracker_row["Discovery State"]
            job["update_reason"] = tracker_row["Update Reason"]
            job["updated_on"] = tracker_row["Updated On"]

    for tracker_key, row in existing.items():
        if tracker_key in seen_urls:
            continue
        shared_application_state = url_application_state.get(tracker_key[0], {})
        synced_rows.append(
            {
                "URL": row.get("URL", ""),
                "Company ID": row.get("Company ID", ""),
                "Company": row.get("Company", ""),
                "Title": row.get("Title", ""),
                "Location": row.get("Location", ""),
                "Track": row.get("Track", ""),
                "Track Label": row.get("Track Label", ""),
                "Current Decision": row.get("Current Decision", ""),
                "Current Final Score": row.get("Current Final Score", ""),
                "Current ROI Score": row.get("Current ROI Score", ""),
                "Freshness": row.get("Freshness", ""),
                "Section": row.get("Section", ""),
                "Current Rank": row.get("Current Rank", ""),
                "Last Seen": row.get("Last Seen", ""),
                "Added On": row.get("Added On", ""),
                "Updated On": row.get("Updated On", ""),
                "Discovery State": row.get("Discovery State", ""),
                "Update Reason": row.get("Update Reason", ""),
                "Status": shared_application_state.get("Status") or row.get("Status", ""),
                "Applied On": shared_application_state.get("Applied On") or row.get("Applied On", ""),
                "Follow Up On": shared_application_state.get("Follow Up On") or row.get("Follow Up On", ""),
                "Response": shared_application_state.get("Response") or row.get("Response", ""),
                "Notes": shared_application_state.get("Notes") or row.get("Notes", ""),
            }
        )

    with open(tracker_csv_path, "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "Company",
            "Title",
            "Location",
            "Status",
            "Applied On",
            "Follow Up On",
            "Response",
            "Notes",
            "URL",
            "Company ID",
            "Track",
            "Track Label",
            "Section",
            "Current Rank",
            "Current Decision",
            "Current Final Score",
            "Current ROI Score",
            "Freshness",
            "Last Seen",
            "Added On",
            "Updated On",
            "Discovery State",
            "Update Reason",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(synced_rows)

    write_application_tracker_text(tracker_text_path, synced_rows, shorten=shorten)
    write_application_tracker_markdown(path=tracker_md_path, rows=synced_rows, today=today, markdown_escape=markdown_escape)
    run_metadata["response_summary"] = build_tracker_response_summary(synced_rows, contains_any=contains_any)
