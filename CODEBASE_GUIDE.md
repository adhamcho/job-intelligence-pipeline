# Codebase Guide

This file explains the shortest path to understanding how this project works.

## What This Project Does

This project:

1. pulls jobs from many sources
2. puts them into one shared format
3. filters out jobs that are not relevant
4. scores the remaining jobs
5. builds:
   - [results/current/apply_queue.md](results/current/apply_queue.md)
   - [results/current/jobs_output.md](results/current/jobs_output.md)

## Best Reading Order

If you are new to the codebase, read these files in this order:

1. [main.py](main.py)
2. [pipeline/runtime_ops.py](pipeline/runtime_ops.py)
3. [pipeline/normalization.py](pipeline/normalization.py)
4. [pipeline/ranking.py](pipeline/ranking.py)
5. [pipeline/queue_ops.py](pipeline/queue_ops.py)
6. [pipeline/reporting.py](pipeline/reporting.py)
7. [pipeline/diagnostics.py](pipeline/diagnostics.py)
8. [pipeline/scorer.py](pipeline/scorer.py)
9. [intake/collectors.py](intake/collectors.py)
10. [intake/extended_collectors.py](intake/extended_collectors.py)
11. [intake/aggregator_collectors.py](intake/aggregator_collectors.py)
12. [sources/companies.py](sources/companies.py)
13. [sources/extended_sources.py](sources/extended_sources.py)
14. [sources/aggregator_sources.py](sources/aggregator_sources.py)

## Architecture Note

[main.py](main.py) is the orchestrator. It wires together the run, defines output paths, and calls the helper modules in order.

Most of the detailed logic lives under [pipeline/](pipeline/). [pipeline/bindings.py](pipeline/bindings.py) installs helper names into `main.py` so older call sites can keep using a single context object while the implementation stays modular.

## The Main Flow

### 1. Job Intake

Raw jobs come from three places:

- `structured` in [intake/collectors.py](intake/collectors.py)
  - Greenhouse
  - Lever
  - Ashby
- `extended` in [intake/extended_collectors.py](intake/extended_collectors.py)
  - Workday
  - SmartRecruiters
  - iCIMS
  - direct/custom pages
- `aggregator` in [intake/aggregator_collectors.py](intake/aggregator_collectors.py)
  - The Muse
  - Remote OK
  - We Work Remotely
  - Remotive
  - Jobicy

The main entry point is:

- `collect_jobs()` in [pipeline/runtime_ops.py](pipeline/runtime_ops.py)

## 2. Normalization

Different sites return different fields.

The project fixes that in:

- `normalize()` in [pipeline/normalization.py](pipeline/normalization.py)

This function creates the common fields the rest of the project expects, like:

- lowercase title
- lowercase location
- lowercase combined text
- source type
- freshness data

## 3. Filtering

Before a job can rank, it must survive hard gates.

The most important ones are:

- `is_target_location()` in [pipeline/policy.py](pipeline/policy.py)
  - keeps only jobs in the allowed geography
- `is_target_soc_role_title()` in [pipeline/title_rules.py](pipeline/title_rules.py)
  - checks if a title belongs in the SOC lane
- `is_target_cyber_analyst_role_title()` in [pipeline/title_rules.py](pipeline/title_rules.py)
  - checks if a title belongs in the broader cyber lane
- `is_target_it_role_title()` in [pipeline/title_rules.py](pipeline/title_rules.py)
  - checks if a title belongs in the IT bridge lane
- `fails_entry_level_cyber_gate()` in [pipeline/policy.py](pipeline/policy.py)
  - blocks cyber jobs that are too senior or unrealistic

If a job fails one of these, it never reaches the queue.

## 4. Scoring

The score system is built in layers.

The first layer is resume overlap:

- `score_job()` in [pipeline/scorer.py](pipeline/scorer.py)

Then the pipeline builds larger scores like:

- fit
- acceptance
- execution
- trajectory
- entry viability
- response likelihood
- apply priority

The most important scoring functions are:

- `compute_fit_score()` in [pipeline/ranking.py](pipeline/ranking.py)
- `compute_acceptance_score()` in [pipeline/ranking.py](pipeline/ranking.py)
- `get_source_adjusted_thresholds()` in [pipeline/scoring_helpers.py](pipeline/scoring_helpers.py)

## 5. Final Ranking

The main function that decides whether one job survives is:

- `build_ranked_job()` in [pipeline/ranking.py](pipeline/ranking.py)

That function:

1. checks hard blockers
2. computes the major scores
3. returns a fully ranked job
4. or returns `None` if the job should be dropped

## 6. Queue Building

After jobs are ranked, the queue is built in:

- `build_apply_queue()` in [pipeline/queue_ops.py](pipeline/queue_ops.py)

This function decides:

- what goes into `Fast Lane`
- what goes into `Daily Drop`
- what goes into `Apply Now`
- what gets pushed to `Watchlist`

It also removes duplicate versions of the same role.

## 7. Reports

The main report is written by:

- `write_markdown_report()` in [pipeline/reporting.py](pipeline/reporting.py)

The tracker is handled by [pipeline/tracker_ops.py](pipeline/tracker_ops.py), and queue outputs are handled by [pipeline/queue_ops.py](pipeline/queue_ops.py). [main.py](main.py) still decides when these writers run.

## If Something Looks Wrong

Use this rule:

- wrong jobs entering the system:
  - check source files and collectors
- good jobs missing:
  - check title filters in [pipeline/title_rules.py](pipeline/title_rules.py), location filters in [pipeline/policy.py](pipeline/policy.py), and ranking gates in [pipeline/ranking.py](pipeline/ranking.py)
- score feels weird:
  - check [pipeline/scorer.py](pipeline/scorer.py), [pipeline/ranking.py](pipeline/ranking.py), and [pipeline/scoring_helpers.py](pipeline/scoring_helpers.py)
- queue feels weird:
  - check `build_apply_queue()` in [pipeline/queue_ops.py](pipeline/queue_ops.py)

## Short Version

If you only remember four things:

1. `collect_jobs()` in [pipeline/runtime_ops.py](pipeline/runtime_ops.py) gets the raw jobs
2. `normalize()` in [pipeline/normalization.py](pipeline/normalization.py) puts them into one format
3. `build_ranked_job()` in [pipeline/ranking.py](pipeline/ranking.py) decides which jobs survive
4. `build_apply_queue()` in [pipeline/queue_ops.py](pipeline/queue_ops.py) decides what you actually see first
