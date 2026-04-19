"""Legacy direct-scraping module.

This file is intentionally kept in the repo, but the Playwright-based Indeed
search flow has been disabled. The active pipeline now uses Google link
collection in link_collector.py and lightweight requests-based page fetches in
main.py.
"""


def get_job_links(_search_url):
    raise RuntimeError(
        "Direct Indeed scraping is disabled. Use link_collector.get_job_links()."
    )


def get_job_text(_url):
    raise RuntimeError(
        "Direct job-page scraping is disabled. Use fetch_job_page() in main.py."
    )
