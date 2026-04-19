import json
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from intake.collectors import TIMEOUT, html_to_text


# Small cleaning helpers used by all extended-source collectors.
def clean_text(value):
    return re.sub(r"\s+", " ", (value or "")).strip()


def normalize_term_list(values):
    return [str(value).strip().lower() for value in (values or []) if str(value).strip()]


def contains_any_term(text, terms):
    haystack = str(text or "").lower()
    return any(term in haystack for term in normalize_term_list(terms))


# Shared filtering and shared job builder for extended sources.
# These helpers make different ATS sites obey the same title/location/description
# rules before they enter scoring.
def passes_source_filters(source, *, title="", location="", description=""):
    title_text = clean_text(title).lower()
    location_text = clean_text(location).lower()
    description_text = clean_text(description).lower()
    combined_text = " ".join(part for part in [title_text, location_text, description_text] if part)

    title_allow_terms = source.get("title_allow_terms") or []
    # This is the first filter for noisy custom sources.
    # If a source requires certain title words, jobs without those words stop here
    # and never reach scoring.
    if title_allow_terms:
        allow_in_combined_text = bool(source.get("allow_in_combined_text"))
        if not contains_any_term(title_text, title_allow_terms):
            if not (allow_in_combined_text and contains_any_term(combined_text, title_allow_terms)):
                return False

    if contains_any_term(title_text, source.get("title_block_terms") or []):
        return False

    location_allow_terms = source.get("location_allow_terms") or []
    if location_allow_terms and location_text and not contains_any_term(location_text, location_allow_terms):
        return False

    if contains_any_term(location_text, source.get("location_block_terms") or []):
        return False

    if contains_any_term(combined_text, source.get("description_block_terms") or []):
        return False

    return True


def build_extended_job(source, *, title, location="", url="", description="", is_remote=False, posted_at="", updated_at=""):
    return {
        "title": clean_text(title),
        "company": source["name"],
        "location": clean_text(location),
        "secondary_locations": [],
        "url": url,
        "description": clean_text(description),
        "source": f"extended:{source['type']}",
        "is_remote": bool(is_remote),
        "posted_at": posted_at,
        "updated_at": updated_at,
        "company_id": source["id"],
        "company_group": "",
        "company_tags": source.get("tags", []),
        "company_difficulty": source.get("difficulty", "standard"),
        "company_hiring_pattern": source.get("hiring_pattern", "standard"),
        "company_industry": source.get("industry", "tech"),
    }


# Custom source collectors.
# Each function below knows how to pull jobs from one non-standard source type
# and convert them into the shared extended-job format.
def collect_happydance_jobs(source, session):
    try:
        response = session.get(source["url"], timeout=TIMEOUT)
        response.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    seen_urls = set()

    for anchor in soup.select("a[href*='/jobs/']"):
        href = anchor.get("href") or ""
        absolute_url = urljoin(source["url"], href)
        parsed = urlparse(absolute_url)

        if parsed.netloc != urlparse(source["url"]).netloc:
            continue
        if absolute_url.rstrip("/") == source["url"].rstrip("/"):
            continue
        if absolute_url in seen_urls:
            continue

        title = clean_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        seen_urls.add(absolute_url)
        jobs.append(
            {
                "title": title,
                "company": source["name"],
                "url": absolute_url,
            }
        )

        if len(jobs) >= source.get("max_jobs", 25):
            break

    detail_limit = min(len(jobs), source.get("max_detail_fetches", 12))
    detailed_jobs = []
    for job in jobs[:detail_limit]:
        try:
            detail_response = session.get(job["url"], timeout=TIMEOUT)
            detail_response.raise_for_status()
        except Exception:
            continue

        detail_soup = BeautifulSoup(detail_response.text, "html.parser")
        page_text = clean_text(detail_soup.get_text(" ", strip=True))
        main_content = detail_soup.select_one("main") or detail_soup
        description = html_to_text(str(main_content))

        location = ""
        date_text = ""
        lines = [clean_text(text) for text in detail_soup.stripped_strings]
        for index, line in enumerate(lines):
            if re.fullmatch(r"\d{2}/\d{2}/\d{4}", line):
                date_text = line
                if index + 4 < len(lines):
                    location = lines[index + 4]
                break

        detailed_jobs.append(
            build_extended_job(
                source,
                title=detail_soup.find("h1").get_text(" ", strip=True) if detail_soup.find("h1") else job["title"],
                location=location,
                url=job["url"],
                description=description or page_text,
                is_remote="remote" in page_text.lower() or "home office" in page_text.lower(),
                posted_at=date_text,
            )
        )

    return detailed_jobs


def collect_smartrecruiters_jobs(source, session):
    company_identifier = source["url"]
    postings_url = f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings"
    page_size = 100
    page_limit = max(1, int(source.get("page_limit", 1)))
    max_jobs = int(source.get("max_jobs", 50))
    postings = []
    offset = 0
    pages_seen = 0

    while pages_seen < page_limit and len(postings) < max_jobs:
        try:
            response = session.get(
                postings_url,
                params={"offset": offset, "limit": page_size},
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            break

        batch = payload.get("content", []) or []
        if not batch:
            break

        postings.extend(batch)
        pages_seen += 1
        offset += len(batch)

        total_found = int(payload.get("totalFound") or 0)
        if total_found and offset >= total_found:
            break

    jobs = []

    for posting in postings:
        posting_title = posting.get("name") or ""
        title_allow_terms = source.get("title_allow_terms") or []
        if title_allow_terms and not contains_any_term(posting_title, title_allow_terms):
            continue
        if contains_any_term(posting_title, source.get("title_block_terms") or []):
            continue

        job_ad_id = posting.get("id") or posting.get("ref")
        if not job_ad_id:
            continue

        detail_url = f"https://api.smartrecruiters.com/v1/companies/{company_identifier}/postings/{job_ad_id}"
        try:
            detail_response = session.get(detail_url, timeout=TIMEOUT)
            detail_response.raise_for_status()
            detail = detail_response.json()
        except Exception:
            detail = posting

        location_data = detail.get("location") or posting.get("location") or {}
        location_parts = [
            location_data.get("city"),
            location_data.get("region"),
            location_data.get("country"),
        ]
        location = ", ".join(part.strip() for part in location_parts if part and str(part).strip())

        job_url = detail.get("applyUrl") or posting.get("applyUrl") or detail.get("jobAd", {}).get("sections", [{}])[0].get("text", "")
        description_sections = []
        for section in (detail.get("jobAd") or {}).get("sections", []):
            if isinstance(section, dict):
                description_sections.append(section.get("title", ""))
                description_sections.append(html_to_text(section.get("text", "")))
            elif isinstance(section, str):
                description_sections.append(html_to_text(section))

        full_text = " ".join(description_sections)
        remote_text = " ".join([detail.get("name", ""), location, full_text]).lower()

        if not passes_source_filters(source, title=detail.get("name") or posting.get("name"), location=location, description=full_text):
            continue

        jobs.append(
            build_extended_job(
                source,
                title=detail.get("name") or posting.get("name"),
                location=location,
                url=job_url or f"https://careers.smartrecruiters.com/{company_identifier}/{job_ad_id}",
                description=full_text,
                is_remote="remote" in remote_text or "work from home" in remote_text,
                posted_at=detail.get("releasedDate") or posting.get("releasedDate") or "",
            )
        )

        if len(jobs) >= max_jobs:
            break

    return [job for job in jobs if job.get("title") and job.get("url")]


def collect_workday_jobs(source, session):
    jobs_url = source.get("jobs_url") or source.get("url")
    if not jobs_url:
        return []

    method = str(source.get("method", "post")).strip().lower()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    max_jobs = int(source.get("max_jobs", 25))
    page_limit = min(max_jobs, int(source.get("page_limit", 20)))
    page_limit = max(1, page_limit)
    search_terms = source.get("search_terms") or [source.get("search_text", "")]
    postings = []
    seen_paths = set()

    for search_text in search_terms:
        offset = 0

        while len(postings) < max_jobs:
            payload = {
                "limit": page_limit,
                "offset": offset,
                "searchText": search_text,
            }

            try:
                if method == "get":
                    response = session.get(jobs_url, headers=headers, timeout=TIMEOUT)
                else:
                    response = session.post(jobs_url, json=payload, headers=headers, timeout=TIMEOUT)
                response.raise_for_status()
                data = response.json()
            except Exception:
                break

            batch = (
                data.get("jobPostings")
                or data.get("content")
                or data.get("jobs")
                or data.get("items")
                or []
            )
            if not batch:
                break

            new_batch_count = 0
            for posting in batch:
                key = posting.get("externalPath") or posting.get("external_path") or posting.get("id") or json.dumps(posting, sort_keys=True)
                if key in seen_paths:
                    continue
                seen_paths.add(key)
                postings.append(posting)
                new_batch_count += 1
                if len(postings) >= max_jobs:
                    break

            if len(batch) < page_limit or new_batch_count == 0:
                break
            offset += len(batch)

    postings = postings[:max_jobs]
    jobs = []

    for posting in postings:
        title = clean_text(posting.get("title") or posting.get("name") or posting.get("jobTitle"))
        if not title:
            continue

        location = clean_text(
            posting.get("locationsText")
            or posting.get("location")
            or posting.get("locationText")
            or posting.get("country")
            or ""
        )
        external_path = posting.get("externalPath") or posting.get("external_path") or posting.get("id") or ""
        posted_at = posting.get("postedOn") or posting.get("postedDate") or posting.get("publicationDate") or ""
        description_parts = []
        bullet_fields = posting.get("bulletFields") or posting.get("bullet_fields") or []
        if isinstance(bullet_fields, list):
            description_parts.extend(str(item) for item in bullet_fields if item)

        url_template = source.get("public_url_template", "")
        if url_template and external_path:
            public_url = url_template.format(external_path=external_path)
        else:
            public_url = posting.get("externalUrl") or posting.get("applyUrl") or posting.get("jobUrl") or ""

        detail_text = ""
        detail_template = source.get("detail_url_template", "")
        detail_url = ""
        if detail_template and external_path:
            detail_url = detail_template.format(external_path=external_path)
        elif external_path and str(jobs_url).rstrip("/").endswith("/jobs"):
            detail_url = str(jobs_url).rstrip("/")[:-5] + external_path

        if detail_url:
            try:
                detail_response = session.get(detail_url, headers=headers, timeout=TIMEOUT)
                detail_response.raise_for_status()
                detail_data = detail_response.json()
                detail_text = clean_text(
                    detail_data.get("jobPostingInfo", {}).get("jobDescription")
                    or detail_data.get("jobDescription")
                    or html_to_text(detail_response.text)
                )
                public_url = public_url or detail_data.get("externalUrl") or detail_url
            except Exception:
                detail_text = ""

        combined_text = " ".join(part for part in [detail_text, *description_parts] if part)
        remote_text = " ".join([title, location, combined_text]).lower()

        if not passes_source_filters(source, title=title, location=location, description=combined_text):
            continue

        jobs.append(
            build_extended_job(
                source,
                title=title,
                location=location,
                url=public_url,
                description=combined_text,
                is_remote="remote" in remote_text or "work from home" in remote_text,
                posted_at=posted_at,
            )
        )

    return [job for job in jobs if job.get("title") and job.get("url")]


def collect_icims_jobs(source, session):
    search_url = source.get("url")
    search_urls = source.get("search_urls") or ([search_url] if search_url else [])
    if not search_urls:
        return []

    jobs = []
    seen_urls = set()
    candidate_urls = []
    page_limit = max(1, int(source.get("page_limit", 3)))
    max_jobs = int(source.get("max_jobs", 25))

    for base_search_url in search_urls:
        try:
            response = session.get(base_search_url, timeout=TIMEOUT)
            response.raise_for_status()
        except Exception:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        page_urls = [base_search_url]

        # iCIMS uses `pr=` links for page 2, page 3, and so on.
        # Adding those links here makes the collector keep pulling jobs after page 1
        # instead of missing later results.
        for anchor in soup.select("a[href*='/jobs/search?']"):
            href = anchor.get("href") or ""
            if "pr=" not in href:
                continue
            absolute = urljoin(base_search_url, href)
            if absolute not in page_urls:
                page_urls.append(absolute)
            if len(page_urls) >= page_limit:
                break

        for page_url in page_urls[:page_limit]:
            try:
                page_response = session.get(page_url, timeout=TIMEOUT)
                page_response.raise_for_status()
            except Exception:
                continue

            page_soup = BeautifulSoup(page_response.text, "html.parser")
            for anchor in page_soup.select("a[href*='/jobs/']"):
                href = anchor.get("href") or ""
                if "/job" not in href:
                    continue
                title_text = clean_text(" ".join(anchor.stripped_strings))
                if not title_text:
                    continue
                title_text = re.sub(r"^(requisition )?title\s+", "", title_text, flags=re.IGNORECASE).strip()
                if not title_text:
                    continue
                absolute = urljoin(page_url, href)
                parsed = urlparse(absolute)
                # This removes extra URL parts that do not change which job it is.
                # The result is one cleaned-up link per job, so the same posting does
                # not get scored twice when two searches point to it.
                clean_url = parsed._replace(query="", fragment="").geturl()
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                candidate_urls.append((clean_url, title_text))
                if len(candidate_urls) >= max_jobs:
                    break
            if len(candidate_urls) >= max_jobs:
                break
        if len(candidate_urls) >= max_jobs:
            break

    for detail_url, fallback_title in candidate_urls:
        try:
            detail_response = session.get(f"{detail_url}?in_iframe=1", timeout=TIMEOUT)
            detail_response.raise_for_status()
        except Exception:
            continue

        detail_soup = BeautifulSoup(detail_response.text, "html.parser")
        content = detail_soup.select_one(".iCIMS_JobContent") or detail_soup
        content_text = clean_text(content.get_text(" ", strip=True))
        if not content_text:
            continue

        title = fallback_title
        title_patterns = [
            r"(.+?)\s+Req\.\s*#",
            r"(.+?)\s+Location\s+",
        ]
        # These patterns remove iCIMS header text like `Req. #` and `Location`.
        # That leaves `title` as just the job name, which the ranking and duplicate checks expect.
        for pattern in title_patterns:
            title_match = re.match(pattern, content_text, re.IGNORECASE)
            if title_match:
                title = clean_text(title_match.group(1))
                break

        location = ""
        location_patterns = [
            r"\bJob Locations\s+(.+?)\s+ID\s+",
            r"\bJob Locations\s+(.+?)\s+Category\s+",
            r"\bJob Locations\s+(.+?)\s+Type\s+",
            r"\bLocation\s+(.+?)\s+Overview\b",
            r"\bLocation\s+(.+?)\s+Category\s+",
            r"\bLocation\s+(.+?)\s+Position Type\s+",
            r"\bLocation\s+(.+?)\s+ID\s+",
        ]
        # This checks the more exact location patterns first.
        # That stops words like `Identity` from being mistaken for the `ID` field,
        # which would put description text into `location` and break location filtering.
        for pattern in location_patterns:
            location_match = re.search(pattern, content_text, re.IGNORECASE)
            if location_match:
                location = clean_text(location_match.group(1))
                break

        apply_url = detail_url
        apply_anchor = detail_soup.find("a", string=re.compile(r"apply", re.IGNORECASE))
        if apply_anchor and apply_anchor.get("href"):
            apply_url = urljoin(detail_url, apply_anchor.get("href"))

        description = content_text
        remote_text = " ".join([title, location, description]).lower()

        if not passes_source_filters(source, title=title, location=location, description=description):
            continue

        jobs.append(
            build_extended_job(
                source,
                title=title,
                location=location,
                url=detail_url,
                description=description,
                is_remote="remote" in remote_text or "work from home" in remote_text,
            )
        )

    return [job for job in jobs if job.get("title") and job.get("url")]


def collect_workable_jobs(source, session):
    account = source.get("account") or source.get("url")
    if not account:
        return []

    api_url = f"https://apply.workable.com/api/v1/widget/accounts/{account}"
    max_jobs = int(source.get("max_jobs", 50))

    try:
        response = session.get(api_url, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    jobs = []
    for item in payload.get("jobs", []) or []:
        title = item.get("title") or ""
        location_parts = []
        for location in item.get("locations", []) or []:
            location_bits = [
                location.get("city"),
                location.get("region"),
                location.get("country") or location.get("countryCode"),
            ]
            location_label = ", ".join(clean_text(bit) for bit in location_bits if clean_text(bit))
            if location_label:
                location_parts.append(location_label)

        if not location_parts:
            location_bits = [item.get("city"), item.get("state"), item.get("country")]
            fallback_location = ", ".join(clean_text(bit) for bit in location_bits if clean_text(bit))
            if fallback_location:
                location_parts.append(fallback_location)

        if item.get("telecommuting"):
            location_parts.append("Remote")

        location = " | ".join(dict.fromkeys(location_parts))
        description_parts = [
            item.get("department") or "",
            item.get("function") or "",
            item.get("industry") or "",
            item.get("experience") or "",
            item.get("description") or "",
            payload.get("description") or "",
        ]
        description = html_to_text(" ".join(part for part in description_parts if part))
        remote_text = " ".join([title, location, description]).lower()

        if not passes_source_filters(source, title=title, location=location, description=description):
            continue

        jobs.append(
            build_extended_job(
                source,
                title=title,
                location=location,
                url=item.get("url") or item.get("shortlink") or item.get("application_url") or "",
                description=description,
                is_remote=bool(item.get("telecommuting")) or "remote" in remote_text,
                posted_at=item.get("published_on") or item.get("created_at") or "",
            )
        )

        if len(jobs) >= max_jobs:
            break

    return [job for job in jobs if job.get("title") and job.get("url")]


# Extended-source dispatch.
# This is the entry point the rest of the project uses for Workday, iCIMS,
# SmartRecruiters, Workable, and direct/custom sources.
def collect_jobs_for_extended_source(source, session):
    # This picks the parser that matches the source's job site.
    # The result is that SmartRecruiters, Workday, iCIMS, Workable, and direct pages all end up
    # in the same job format before ranking starts.
    if source["type"] == "smartrecruiters":
        return collect_smartrecruiters_jobs(source, session)
    if source["type"] == "happydance":
        return collect_happydance_jobs(source, session)
    if source["type"] == "workday":
        return collect_workday_jobs(source, session)
    if source["type"] == "icims":
        return collect_icims_jobs(source, session)
    if source["type"] == "workable":
        return collect_workable_jobs(source, session)
    return []
