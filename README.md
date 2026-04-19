# Job Intelligence Pipeline

`Job Intelligence Pipeline` is a Python job-search pipeline that pulls roles from multiple job-source families, normalizes them into one format, scores them against resume tracks, and produces a ranked apply queue plus diagnostics.

This project is part automation tool and part decision-support system. The goal is not just to scrape postings, but to reduce a noisy job market into a smaller set of realistic next applications.

## Portfolio Summary

Built a multi-source job-intelligence pipeline in Python that collects postings from ATS boards and aggregators, normalizes them into a shared schema, scores them against multiple resume tracks, and generates a prioritized apply queue with diagnostic reporting.

This public repo is a sanitized showcase version of a larger private working project.

## How It Works

- Input: job postings from ATS boards, custom career pages, and aggregators
- Processing: normalize, filter, score, and rank the postings
- Output: a prioritized apply queue plus source-health and ranking diagnostics

## Why This Exists

Most job boards create the same problem:

- too much volume
- mixed quality across sources
- weak prioritization
- no feedback loop once applications start going out

This project addresses that by:

- collecting jobs from structured ATS boards, custom/extended sources, and aggregators
- normalizing the raw postings into one schema
- filtering by location, title lane, and entry-level realism
- scoring jobs for fit, acceptance odds, execution cost, and trajectory
- building an apply queue instead of a giant undifferentiated dump
- tracking outcomes so source quality can improve over time

## What It Covers

The pipeline currently pulls from:

- Structured ATS boards: Greenhouse, Lever, Ashby
- Extended/custom sources: SmartRecruiters, Workday, iCIMS, Workable, and direct/custom pages
- Aggregators: Remote OK, The Muse, We Work Remotely, Remotive, Jobicy

## Outputs

The pipeline produces:

- `results/current/apply_queue.md`: prioritized jobs to act on first
- `results/current/jobs_output.md`: broader ranked job report
- `results/tracker/application_tracker.md`: editable application-state tracker
- `results/diagnostics/`: source health, hit reports, rejection breakdowns, and ranking review files

## Sample Output

The real private workflow writes large markdown and diagnostic files. A simplified example looks like this:

```md
# Apply Queue

Generated on 2026-04-18 | Scrape time 5m 15s
Pool: 14745 raw jobs = 14324 structured, 251 extended, 170 aggregator

## Fast Lane

### Information Security Analyst
- Company: Betterment
- Decision: APPLY (High ROI)
- Final / ROI / Freshness: 90 / 97 / last week (5d)
- Apply Priority: 100
- Entry Viability: 95
- Response Likelihood: 100
- Resume To Use: cyber
- Location: New York City
```

The diagnostics layer also summarizes source quality over time:

```md
# Source Health Report

- Total tracked source/company records: 419
- Keep investing: 31
- Watch: 13
- Unproven: 212
- Needs attention: 163
```

That combination is the core idea of the project: not just collecting jobs, but ranking them, exposing why they were ranked that way, and measuring which source families are worth future effort.

## Engineering Highlights

- Modular pipeline split across `intake/`, `pipeline/`, `shared/`, and `sources/`
- Resume-aware scoring for multiple tracks
- Tracker feedback loop so application outcomes can influence source evaluation
- Smoke test script for fast validation without a full scrape
- GitHub Actions workflow that runs the smoke test on pushes and pull requests
- Public-release tooling that creates a sanitized copy without private resumes, tracker state, cache files, or generated output

## Project Structure

- `main.py`: orchestrates collection, normalization, ranking, queue building, and report writing
- `intake/`: source collectors
- `pipeline/`: scoring, filtering, ranking, diagnostics, reporting, and tracker logic
- `sources/`: source definitions and company lists
- `scripts/`: smoke testing and public-release helpers

For a guided reading order, see `CODEBASE_GUIDE.md`.

## Running It

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create local private resume inputs from the templates:

```powershell
Copy-Item resume_cyber.example.txt resume_cyber.txt
Copy-Item resume_it_support.example.txt resume_it_support.txt
```

Then edit those new `.txt` files with your own resume text. Those real resume files stay local and are not part of this public repo.

Run the full pipeline:

```powershell
python main.py
```

`python main.py` performs a real collection pass and may take several minutes depending on source count and network conditions.

## Quick Validation

Run this when you want a fast confidence check without waiting for a full scrape:

```powershell
python scripts\smoke_test.py
```

The smoke test:

- compiles project Python files
- imports core modules
- rebuilds the sanitized public copy when run from the private repo
- validates the current checkout when run from the public repo
- runs the release safety check

## Roadmap

The project roadmap and current definition of "done enough" live in `ROADMAP.md`.
