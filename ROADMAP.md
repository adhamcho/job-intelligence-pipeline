# Project Roadmap

This file defines what "100% done" means for this project in practical terms.

The goal is not to scrape the literal whole internet. The goal is to build a
job pipeline that:

1. covers most relevant online job sources for the target lanes
2. produces a useful daily apply queue
3. learns from tracker outcomes over time
4. can be safely turned into a public repo later

## Current Status

Estimated overall progress: `about 90%`

Strong areas:

- code organization
- private repo safety
- public-release prep
- smoke testing and CI
- queue and tracker workflow

Main remaining gap:

- source coverage

## What 100% Means

The project counts as "100%" when these are true:

### 1. Core Pipeline Is Stable

- `python main.py` runs cleanly
- `python scripts\smoke_test.py` runs cleanly
- the queue and reports update correctly
- tracker edits flow back into generated output

### 2. Source Coverage Feels Broad Enough

We should have strong coverage across:

- structured ATS boards
  - Greenhouse
  - Lever
  - Ashby
- extended ATS/custom sources
  - SmartRecruiters
  - Workday
  - iCIMS
  - Workable
- aggregator sources
  - The Muse
  - Remote OK
  - We Work Remotely
  - Remotive
  - Jobicy

And within those, we should keep finding jobs in these lanes:

- direct SOC / incident / detection titles
- cyber analyst / IAM / security analyst bridge titles
- IT support / service desk / technical support bridge titles
- local NY / Long Island / Remote US roles

### 3. Source Quality Is Good Enough

The source pool should not just be large. It should keep producing:

- real queue candidates
- realistic bridge roles
- direct or near-direct cyber roles

And the source health report should make it obvious:

- which sources are worth expanding
- which sources are dead
- which sources are noisy but still useful

### 4. Public Release Is Ready

Before public release, we need:

- sanitized export copy
- release safety check
- smoke test
- README
- example input files
- no private resumes, tracker state, or generated results in the public copy

## Current Priorities

### Priority 1: Source Coverage

This is the main remaining work.

Focus on:

- verified Greenhouse / Lever / Ashby boards
- verified Workable sources only when they return real US-support or cyber-adjacent jobs
- local NY / Long Island employers
- Remote US support and security-adjacent boards
- "Kraft Kennedy style" wins:
  - direct SOC
  - security analyst
  - technical support
  - help desk
  - IAM

### Priority 2: Parser / Normalization Fixes

When a good source exposes a parsing bug, fix it immediately.

Examples:

- bad location parsing
- false years-required parsing
- duplicate URL cleanup
- remote-US inference
- title cleanup

### Priority 3: Outcome Learning

The tracker should keep becoming more useful as real outcomes are marked.

We want better evidence for:

- which source families get responses
- which title families convert
- which queue categories are actually worth the effort

### Priority 4: Public Repo Polish

This is important, but it is not the main bottleneck right now.

Do this after source coverage is strong enough:

- tighten public README
- improve docs
- review sanitized copy
- choose final public repo name

## What Not To Prioritize Right Now

These are lower priority than source coverage:

- more big refactors
- redesigning the score system from scratch
- building a fancy UI
- trying to scrape LinkedIn directly
- polishing the public repo before the private version is ready

## Working Definition Of "Done Enough"

If the project:

- keeps finding fresh, relevant jobs
- keeps producing a useful queue
- covers the main source ecosystems we care about
- survives smoke tests and full runs
- can generate a safe public copy

then it is effectively done enough to publish a public version.
