"""Legacy Google link collector.

This file is intentionally kept in the repo, but the active pipeline no longer
depends on Google or Indeed scraping. The current system pulls jobs directly
from public ATS APIs through companies.py and collectors.py.
"""


def get_job_links(_query):
    raise RuntimeError(
        "Google link collection is disabled. Use ATS collectors in collectors.py."
    )
