import requests
from bs4 import BeautifulSoup

from intake.collectors import TIMEOUT, html_to_text
from intake.extended_collectors import clean_text, passes_source_filters
from shared.utils import normalize_company_id


# Shared aggregator job builder.
# This turns messy aggregator records into the same general job format the rest
# of the project already knows how to score.
def build_aggregator_job(
    source,
    *,
    company,
    title,
    location="",
    url="",
    description="",
    is_remote=False,
    posted_at="",
    updated_at="",
):
    return {
        "title": clean_text(title),
        "company": clean_text(company),
        "location": clean_text(location),
        "secondary_locations": [],
        "url": url,
        "description": clean_text(description),
        "source": f"aggregator:{source['provider']}",
        "is_remote": bool(is_remote),
        "posted_at": posted_at,
        "updated_at": updated_at,
        "company_id": normalize_company_id(f"aggregator:{source['provider']}:{company}"),
        "source_feed_id": source["id"],
        "company_group": "aggregator",
        "company_tags": source.get("tags", []),
        "company_difficulty": source.get("difficulty", "standard"),
        "company_hiring_pattern": source.get("hiring_pattern", "steady"),
        "company_industry": source.get("industry", "mixed"),
    }


# Aggregator collectors.
# Each function below knows how to pull jobs from one aggregator source and
# convert them into the shared aggregator-job format.
def collect_remotive_jobs(source, session):
    max_jobs = int(source.get("max_jobs", 60))
    seen_urls = set()
    jobs = []

    for search_text in source.get("search_terms") or []:
        try:
            response = session.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": search_text},
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            continue

        for item in payload.get("jobs", []):
            url = item.get("url") or ""
            if not url or url in seen_urls:
                continue

            title = item.get("title") or ""
            location = item.get("candidate_required_location") or ""
            description = html_to_text(item.get("description", ""))

            if not passes_source_filters(source, title=title, location=location, description=description):
                continue

            jobs.append(
                build_aggregator_job(
                    source,
                    company=item.get("company_name") or source["name"],
                    title=title,
                    location=location,
                    url=url,
                    description=description,
                    is_remote=True,
                    posted_at=item.get("publication_date") or "",
                )
            )
            seen_urls.add(url)

            if len(jobs) >= max_jobs:
                return jobs

    return jobs


def collect_themuse_jobs(source, session):
    max_jobs = int(source.get("max_jobs", 60))
    page_limit = int(source.get("page_limit", 6))
    jobs = []
    seen_urls = set()

    for page in range(1, page_limit + 1):
        try:
            response = session.get(
                "https://www.themuse.com/api/public/jobs",
                params={"page": page},
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            break

        results = payload.get("results") or []
        if not results:
            break

        for item in results:
            refs = item.get("refs") or {}
            url = refs.get("landing_page") or ""
            if not url or url in seen_urls:
                continue

            locations = [clean_text(location.get("name", "")) for location in item.get("locations", []) if location.get("name")]
            location = " | ".join(location for location in locations if location)
            title = item.get("name") or ""
            description = html_to_text(item.get("contents", ""))

            if not passes_source_filters(source, title=title, location=location, description=description):
                continue

            remote_flag = "remote" in location.lower() or "remote" in description.lower()
            jobs.append(
                build_aggregator_job(
                    source,
                    company=(item.get("company") or {}).get("name") or source["name"],
                    title=title,
                    location=location,
                    url=url,
                    description=description,
                    is_remote=remote_flag,
                    posted_at=item.get("publication_date") or "",
                )
            )
            seen_urls.add(url)

            if len(jobs) >= max_jobs:
                return jobs

    return jobs


def collect_remoteok_jobs(source, session):
    max_jobs = int(source.get("max_jobs", 60))

    try:
        response = session.get("https://remoteok.com/api", timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = []
    for item in payload[1:]:
        title = item.get("position") or ""
        location = item.get("location") or "Remote"
        description = html_to_text(item.get("description", ""))

        if not passes_source_filters(source, title=title, location=location, description=description):
            continue

        jobs.append(
            build_aggregator_job(
                source,
                company=item.get("company") or source["name"],
                title=title,
                location=location,
                url=item.get("url") or item.get("apply_url") or "",
                description=description,
                is_remote=True,
                posted_at=item.get("date") or "",
            )
        )

        if len(jobs) >= max_jobs:
            break

    return [job for job in jobs if job.get("url")]


def collect_jobicy_jobs(source, session):
    max_jobs = int(source.get("max_jobs", 60))
    request_count = max(50, int(source.get("request_count", max_jobs * 3)))

    try:
        response = session.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={
                "count": request_count,
                "tag": source.get("api_tag", "support"),
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return []

    jobs = []
    for item in payload.get("jobs", []):
        title = item.get("jobTitle") or ""
        location = item.get("jobGeo") or ""
        description = html_to_text(item.get("jobDescription") or item.get("jobExcerpt") or "")

        if not passes_source_filters(source, title=title, location=location, description=description):
            continue

        jobs.append(
            build_aggregator_job(
                source,
                company=item.get("companyName") or source["name"],
                title=title,
                location=location,
                url=item.get("url") or "",
                description=description,
                is_remote=True,
                posted_at=item.get("pubDate") or "",
            )
        )

        if len(jobs) >= max_jobs:
            break

    return [job for job in jobs if job.get("url")]


def collect_weworkremotely_jobs(source, session):
    max_jobs = int(source.get("max_jobs", 60))
    max_detail_fetches = int(source.get("max_detail_fetches", max_jobs))
    category_url = source.get("url") or ""
    if not category_url:
        return []

    try:
        response = session.get(
            category_url,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    seen_urls = set()

    for anchor in soup.select('a[href*="/remote-jobs/"]'):
        href = anchor.get("href") or ""
        if not href or href.startswith("/remote-jobs/new") or "/listing_ads/" in href:
            continue

        url = f"https://weworkremotely.com{href}" if href.startswith("/") else href
        if url in seen_urls:
            continue

        title = clean_text((anchor.select_one(".new-listing__header__title__text") or anchor).get_text(" ", strip=True))
        company = clean_text((anchor.select_one(".new-listing__company-name") or anchor).get_text(" ", strip=True))
        headquarters = clean_text((anchor.select_one(".new-listing__company-headquarters") or anchor).get_text(" ", strip=True))
        categories = [clean_text(node.get_text(" ", strip=True)) for node in anchor.select(".new-listing__categories__category")]
        location = " | ".join(part for part in [headquarters, *categories] if part)
        description = " | ".join(part for part in [title, company, location] if part)

        if not passes_source_filters(source, title=title, location=location, description=description):
            continue

        jobs.append(
            {
                "company": company or source["name"],
                "title": title,
                "location": location,
                "url": url,
                "description": description,
            }
        )
        seen_urls.add(url)

        if len(jobs) >= max_jobs:
            break

    detailed_jobs = []
    for index, job in enumerate(jobs):
        detail_description = job["description"]
        detail_location = job["location"]

        if index < max_detail_fetches:
            try:
                detail_response = session.get(
                    job["url"],
                    timeout=TIMEOUT,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                detail_response.raise_for_status()
                detail_soup = BeautifulSoup(detail_response.text, "html.parser")

                detail_main = (
                    detail_soup.select_one("section.listing-container")
                    or detail_soup.select_one("article")
                    or detail_soup.select_one("main")
                    or detail_soup
                )
                detail_text = clean_text(detail_main.get_text(" ", strip=True))
                if detail_text:
                    detail_description = detail_text

                meta_bits = []
                for node in detail_soup.select(
                    ".listing-header-container .listing-header__meta li, "
                    ".listing-header-container .listing-header__meta span, "
                    ".listing-container__meta li, "
                    ".listing-container__meta span"
                ):
                    text = clean_text(node.get_text(" ", strip=True))
                    if text and text not in meta_bits:
                        meta_bits.append(text)
                if meta_bits:
                    detail_location = " | ".join(meta_bits)
            except requests.RequestException:
                pass

        if not passes_source_filters(
            source,
            title=job["title"],
            location=detail_location,
            description=detail_description,
        ):
            continue

        detailed_jobs.append(
            build_aggregator_job(
                source,
                company=job["company"],
                title=job["title"],
                location=detail_location,
                url=job["url"],
                description=detail_description,
                is_remote=True,
            )
        )

    return detailed_jobs


# Aggregator dispatch.
# This is the entry point the rest of the project uses for the messy discovery layer.
def collect_jobs_for_aggregator_source(source, session):
    provider = source.get("provider")
    # Each aggregator site uses a different API or page layout.
    # This picks the right scraper so those messy sources still end up in the same
    # job format as everything else.
    if provider == "remotive":
        return collect_remotive_jobs(source, session)
    if provider == "themuse":
        return collect_themuse_jobs(source, session)
    if provider == "remoteok":
        return collect_remoteok_jobs(source, session)
    if provider == "jobicy":
        return collect_jobicy_jobs(source, session)
    if provider == "weworkremotely":
        return collect_weworkremotely_jobs(source, session)
    return []
