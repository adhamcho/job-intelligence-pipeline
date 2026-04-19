import argparse
import csv
import datetime
import os
import sys


BASE_DIR = os.path.dirname(__file__)
TRACKER_PATH = os.path.join(BASE_DIR, "results", "tracker", "application_tracker.csv")


def parse_args():
    parser = argparse.ArgumentParser(description="Mark a tracked job application status.")
    parser.add_argument("--company", help="Company name match, e.g. Datadog")
    parser.add_argument("--title", help="Title match, e.g. SaaS Administrator 1")
    parser.add_argument("--url", help="Exact job URL match")
    parser.add_argument("--track", help="Optional track filter, e.g. it_bridge")
    parser.add_argument("--status", default="APPLIED", help="Status to set, default APPLIED")
    parser.add_argument("--applied-on", default=datetime.date.today().isoformat(), help="Applied date, default today")
    parser.add_argument("--follow-up-on", default="", help="Optional follow-up date")
    parser.add_argument("--response", default="", help="Optional response value")
    parser.add_argument("--notes", default="", help="Optional notes")
    return parser.parse_args()


def matches(row, args):
    if args.url and (row.get("URL") or "").strip() != args.url.strip():
        return False
    if args.track and (row.get("Track") or "").strip() != args.track.strip():
        return False
    if args.company and args.company.lower() not in (row.get("Company") or "").lower():
        return False
    if args.title and args.title.lower() not in (row.get("Title") or "").lower():
        return False
    return any([args.url, args.company, args.title])


def main():
    args = parse_args()
    if not os.path.exists(TRACKER_PATH):
        print(f"Tracker not found: {TRACKER_PATH}")
        return 1

    with open(TRACKER_PATH, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    matched_indexes = [index for index, row in enumerate(rows) if matches(row, args)]

    if not matched_indexes:
        print("No matching tracker rows found.")
        return 1

    if len(matched_indexes) > 1:
        print("Multiple matches found. Add --track or --url to narrow it down.")
        for index in matched_indexes:
            row = rows[index]
            print(f"- {row.get('Company')} | {row.get('Title')} | {row.get('Track')} | {row.get('URL')}")
        return 1

    row = rows[matched_indexes[0]]
    row["Status"] = args.status
    if args.applied_on:
        row["Applied On"] = args.applied_on
    if args.follow_up_on:
        row["Follow Up On"] = args.follow_up_on
    if args.response:
        row["Response"] = args.response
    if args.notes:
        row["Notes"] = args.notes

    with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"Updated: {row.get('Company')} | {row.get('Title')} | {row.get('Track')} -> {row.get('Status')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
