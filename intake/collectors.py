import html
import re

import requests
from shared.utils import normalize_company_id


# Basic request settings used by the structured ATS collectors.
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 20


# Session and text-cleaning helpers.
# These give the collectors one shared HTTP session and one shared way to turn
# HTML job descriptions into plain text.
def create_session():
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def html_to_text(value):
    if not value:
        return ""

    text = value
    for _ in range(2):
        text = html.unescape(text)

    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Structured ATS collectors.
# Each function below knows how to pull jobs from one ATS and convert them into
# the shared job format used by the rest of the project.
def get_greenhouse_jobs(company, session):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company['board']}/jobs?content=true"

    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = []

    for item in payload.get("jobs", []):
        jobs.append(
            {
                "title": item.get("title", "").strip(),
                "company": item.get("company_name") or company["name"],
                "location": (item.get("location") or {}).get("name", "").strip(),
                "secondary_locations": [],
                "url": item.get("absolute_url", ""),
                "description": html_to_text(item.get("content", "")),
                "source": "greenhouse",
                "is_remote": "remote" in ((item.get("location") or {}).get("name", "").lower()),
                "posted_at": item.get("first_published", ""),
                "updated_at": item.get("updated_at", ""),
                "company_id": normalize_company_id(company.get("id", "")),
                "company_group": company.get("group", "standard"),
            }
        )

    return jobs


def get_lever_jobs(company, session):
    url = f"https://api.lever.co/v0/postings/{company['board']}?mode=json"

    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = []

    for item in payload:
        categories = item.get("categories") or {}
        description_parts = [
            item.get("descriptionPlain", ""),
            item.get("additionalPlain", ""),
        ]

        for block in item.get("lists", []):
            description_parts.append(block.get("text", ""))
            description_parts.append(html_to_text(block.get("content", "")))

        location = categories.get("location", "").strip()
        workplace_type = (item.get("workplaceType") or "").lower()

        jobs.append(
            {
                "title": item.get("text", "").strip(),
                "company": company["name"],
                "location": location,
                "secondary_locations": categories.get("allLocations") or [],
                "url": item.get("hostedUrl") or item.get("applyUrl") or "",
                "description": " ".join(part for part in description_parts if part).strip(),
                "source": "lever",
                "is_remote": workplace_type == "remote" or "remote" in location.lower(),
                "posted_at": item.get("createdAt"),
                "updated_at": "",
                "company_id": normalize_company_id(company.get("id", "")),
                "company_group": company.get("group", "standard"),
            }
        )

    return jobs


def get_ashby_jobs(company, session):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{company['board']}"

    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = []

    for item in payload.get("jobs", []):
        secondary_locations = []
        for location in item.get("secondaryLocations", []):
            label = location.get("location")
            if label:
                secondary_locations.append(label.strip())

        workplace_type = (item.get("workplaceType") or "").lower()
        primary_location = (item.get("location") or "").strip()

        jobs.append(
            {
                "title": item.get("title", "").strip(),
                "company": company["name"],
                "location": primary_location,
                "secondary_locations": secondary_locations,
                "url": item.get("jobUrl") or item.get("applyUrl") or "",
                "description": item.get("descriptionPlain") or html_to_text(item.get("descriptionHtml", "")),
                "source": "ashby",
                "is_remote": bool(item.get("isRemote")) or workplace_type == "remote",
                "posted_at": item.get("publishedAt", ""),
                "updated_at": "",
                "company_id": normalize_company_id(company.get("id", "")),
                "company_group": company.get("group", "standard"),
            }
        )

    return jobs


# Structured ATS dispatch.
# This is the entry point the rest of the project uses when it wants jobs from
# a company in `companies.py`.
def collect_jobs_for_company(company, session):
    source_type = company["type"]

    # This picks the right job-pulling function for the company's hiring system.
    # It also makes sure the jobs come back in the same format, so the rest of the
    # project can handle all structured sources the same way.
    if source_type == "greenhouse":
        return get_greenhouse_jobs(company, session)

    if source_type == "lever":
        return get_lever_jobs(company, session)

    if source_type == "ashby":
        return get_ashby_jobs(company, session)

    return []
