"""Report writers for the job tool.

This file turns ranked jobs into the saved output files, like Markdown, text,
HTML, and CSV reports.
"""

import csv
import html
import textwrap


def shorten(value, width):
    if not value:
        return ""
    return textwrap.shorten(value, width=width, placeholder="...")


def markdown_escape(text):
    return str(text).replace("|", "\\|")


def escape_html(value):
    return html.escape(str(value), quote=True)


def score_class(score):
    if score >= 85:
        return "score-high"
    if score >= 70:
        return "score-mid"
    return "score-low"


def decision_class(decision):
    if decision.startswith("APPLY"):
        return "decision-apply"
    if decision.startswith("BACKUP"):
        return "decision-backup"
    if decision == "LOTTERY":
        return "decision-lottery"
    return "decision-maybe"


def get_review_candidates(jobs_by_track, tracks, per_track=5):
    candidates = []

    for track_name, track in tracks.items():
        jobs = jobs_by_track.get(track_name, {}).get("primary", [])
        for index, job in enumerate(jobs[:per_track], start=1):
            candidates.append((track_name, track["label"], index, job))

    return candidates


def write_csv(path, jobs_by_track, *, tracks):
    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)

        for track_name, track in tracks.items():
            sections = jobs_by_track.get(track_name, {})
            for section_key, section_label in [
                ("primary", track["label"]),
                ("stretch", f"{track['label']} | STRETCH CYBER"),
                ("overflow", f"{track['label']} | LOW PRIORITY BUT POSSIBLE"),
                ("volume", f"{track['label']} | VOLUME MODE"),
                ("internships", f"{track['label']} | INTERNSHIPS / NEW GRAD SCOUT"),
            ]:
                jobs = sections.get(section_key, [])
                if not jobs:
                    continue

                writer.writerow([])
                writer.writerow([f"===== {section_label} ====="])
                writer.writerow(
                    [
                        "Decision",
                        "Final Score",
                        "ROI Score",
                        "Freshness",
                        "Fit Score",
                        "Acceptance Score",
                        "Execution Score",
                        "Trajectory Score",
                        "Entry Viability Score",
                        "Narrative Score",
                        "Effort Score",
                        "Path Tier",
                        "Application Status",
                        "Applied On",
                        "Follow Up On",
                        "Execution Tier",
                        "Difficulty",
                        "Company Group",
                        "Company Effectiveness",
                        "Company ID",
                        "Company",
                        "Track",
                        "Resume",
                        "Source",
                        "Years Req",
                        "Skill Match %",
                        "Title Fit",
                        "Title",
                        "Location",
                        "Fit Notes",
                        "Acceptance Notes",
                        "Execution Notes",
                        "Trajectory Notes",
                        "Narrative Notes",
                        "ROI Notes",
                        "Why Rejected",
                        "Overflow Reason",
                        "Disguised Mid-Level",
                        "Disguised Reasons",
                        "Link",
                    ]
                )

                for job in jobs:
                    writer.writerow(
                        [
                            job["decision"],
                            job["final_score"],
                            job["roi_score"],
                            job["freshness_label"],
                            job["fit_score"],
                            job["acceptance_score"],
                            job["execution_score"],
                            job.get("trajectory_score", ""),
                            job.get("entry_viability_score", ""),
                            job["narrative_score"],
                            job["effort_score"],
                            job.get("path_tier", ""),
                            job.get("application_status", "NEW"),
                            job.get("applied_on", ""),
                            job.get("follow_up_on", ""),
                            job["execution_tier"],
                            job["difficulty_tier"],
                            job["company_group"],
                            f"{job['company_effectiveness_score']} ({job['company_effectiveness_label']})",
                            job.get("company_id", ""),
                            job["company"],
                            job["track"],
                            job["resume"],
                            job["source"],
                            job["years_required"],
                            job["skill_match_score"],
                            job["title_score"],
                            job["title"],
                            job["location"],
                            job["fit_notes"],
                            job["acceptance_notes"],
                            job["execution_notes"],
                            job.get("trajectory_notes", ""),
                            job["narrative_notes"],
                            job["roi_notes"],
                            job["risk_notes"],
                            job.get("overflow_reason", ""),
                            "yes" if job.get("disguised_mid_level") else "",
                            job.get("disguised_reasons", ""),
                            job["url"],
                        ]
                    )

        writer.writerow([])
        writer.writerow(["===== SCORE GUIDE ====="])
        writer.writerow(["Field", "Meaning"])
        writer.writerow(["Freshness", "How recently the job appears to have been published. Newer jobs get a strong boost because early applications matter."])
        writer.writerow(["Final Score", "Overall priority rank used for sorting. Higher means a stronger combined target after fit, attainability, execution, narrative alignment, and ROI are blended."])
        writer.writerow(["ROI Score", "Estimated return on your application time. Higher means stronger probability-to-effort balance."])
        writer.writerow(["Trajectory Score", "How much the role appears to move you toward cyber-relevant work like logs, incidents, tooling, systems access, and troubleshooting depth."])
        writer.writerow(["Fit Score", "How well the role matches your resume and target lane based on title relevance plus skill overlap."])
        writer.writerow(["Acceptance Score", "How attainable the role looks based on seniority, years required, location, and hard requirement penalties."])
        writer.writerow(["Execution Score", "How confident the tool is that your current evidence suggests you can execute the job in interviews and on the job."])
        writer.writerow(["Narrative Score", "How well the role matches the story your resume currently tells. High means the role feels consistent with your background, not just keyword overlap."])
        writer.writerow(["Effort Score", "Estimated application and interview burden. Lower is better and helps the ROI score."])
        writer.writerow(["Path Tier", "Tier A is closest to hands-on security operations, Tier B is the strongest IT/support bridge, and Tier C is a selective cyber-adjacent bridge like IAM, access, or risk."])
        writer.writerow(["Execution Tier", "Ready now means the current resume looks immediately usable, Ramp-up likely means plausible with onboarding, Interview risk means gaps may show up in interviews, Not ready means the gap looks large."])
        writer.writerow(["Company Group", "Rough targetability bucket. MSSP and hire-heavy groups get boosted, realistic tech gets a smaller boost, and lottery or stretch-tech groups get penalized."])
        writer.writerow(["Company Effectiveness", "Learned source score based on prior runs. Higher means the company has actually been producing shortlist-worthy roles for you instead of just noise."])
        writer.writerow(["Difficulty", "Rough company competition tier. High means prestige and applicant volume should make the funnel harder."])
        writer.writerow(["Skill Match %", "Weighted overlap between your resume and important skills mentioned in the job post for that lane."])
        writer.writerow(["Title Fit", "How strongly the job title itself matches the target lane before resume overlap is considered."])
        writer.writerow(["Years Req", "Highest experience requirement detected in the job text. 0 means none was clearly found."])
        writer.writerow(["Decision", "APPLY (High ROI) is your best use of time, APPLY (Stretch) is ambitious but worthwhile, APPLY (Low ROI) is plausible but weaker value, BACKUP (Safe/Competitive) is optional volume, LOTTERY is a long-shot reach."])


def write_text_report(path, jobs_by_track, *, tracks):
    lines = []

    for track_name, track in tracks.items():
        sections = jobs_by_track.get(track_name, {})
        for section_key, section_label in [
            ("primary", track["label"]),
            ("stretch", f"{track['label']} | STRETCH CYBER"),
            ("overflow", f"{track['label']} | LOW PRIORITY BUT POSSIBLE"),
            ("volume", f"{track['label']} | VOLUME MODE"),
            ("internships", f"{track['label']} | INTERNSHIPS / NEW GRAD SCOUT"),
        ]:
            jobs = sections.get(section_key, [])

            lines.append(f"===== {section_label} =====")
            if not jobs:
                lines.append("No current matches.")
                lines.append("")
                continue

            header = (
                f"{'Dec':<20} {'Final':>5} {'ROI':>5} {'Fresh':<10} {'Fit':>5} {'Acc':>5} {'Exec':>5} {'Traj':>5} {'Story':>5} "
                f"{'Tier':<8} {'Company':<14} {'Title':<42} {'Location':<34}"
            )
            lines.append(header)
            lines.append("-" * len(header))

            for job in jobs:
                lines.append(
                    f"{shorten(job['decision'], 20):<20} "
                    f"{job['final_score']:>5} "
                    f"{job['roi_score']:>5} "
                    f"{shorten(job['freshness_label'], 10):<10} "
                    f"{job['fit_score']:>5} "
                    f"{job['acceptance_score']:>5} "
                    f"{job['execution_score']:>5} "
                    f"{job.get('trajectory_score', ''):>5} "
                    f"{job['narrative_score']:>5} "
                    f"{shorten(job.get('path_tier', ''), 8):<8} "
                    f"{shorten(job['company'], 14):<14} "
                    f"{shorten(job['title'], 42):<42} "
                    f"{shorten(job['location'], 34):<34}"
                )
                lines.append(f"      Link: {job['url']}")
                lines.append(f"      Diff: {job['difficulty_tier']} | Group {job['company_group']} | Source score {job['company_effectiveness_score']} ({job['company_effectiveness_label']})")
                lines.append(f"      App:  {job.get('application_status', 'NEW')} | Applied {job.get('applied_on', '') or '-'} | Follow-up {job.get('follow_up_on', '') or '-'}")
                lines.append(f"      ROI:  {job['roi_score']} | Effort {job['effort_score']}")
                lines.append(f"      Exec: {job['execution_tier']}")
                if job.get("overflow_reason"):
                    lines.append(f"      Lane: {job['overflow_reason']}")
                if job["fit_notes"]:
                    lines.append(f"      Fit:  {job['fit_notes']}")
                if job["acceptance_notes"]:
                    lines.append(f"      Acc:  {job['acceptance_notes']}")
                if job["execution_notes"]:
                    lines.append(f"      Work: {job['execution_notes']}")
                if job.get("trajectory_notes"):
                    lines.append(f"      Move: {job['trajectory_notes']}")
                if job["narrative_notes"]:
                    lines.append(f"      Story:{job['narrative_notes']}")
                if job["risk_notes"]:
                    lines.append(f"      Risk: {job['risk_notes']}")
                lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_markdown_report(
    path,
    jobs_by_track,
    *,
    tracks,
    run_metadata,
    location_mode,
    location_mode_labels,
    format_days_old,
    geo_ambiguous_cyber_leads=None,
):
    lines = [
        "# Job Intelligence Report",
        "",
        f"Last refresh: `{run_metadata['generated_at']}` | Run ID `{run_metadata['run_id']}`.",
        "",
        f"Generated on `{run_metadata['generated_on']}` at `{run_metadata['generated_at']}` | Scrape time `{run_metadata['scrape_duration']}`.",
        f"Location mode: `{location_mode_labels.get(location_mode, location_mode)}`.",
        (f"Pool: `{run_metadata['pool_summary']}`." if run_metadata.get("pool_summary") else ""),
        *[f"- {detail}" for detail in run_metadata.get("pool_details", [])],
        *[f"- Response pulse: {detail}" for detail in run_metadata.get("response_summary", [])],
        "",
        "## Score Guide",
        "",
        "- `Final Score`: Overall priority rank used for sorting. Higher means a stronger combined target after fit, attainability, execution, narrative alignment, and ROI are blended.",
        "- `ROI Score`: Estimated return on your application time. Higher means stronger probability-to-effort balance.",
        "- `Freshness`: How recently the job appears to have been posted. Newer jobs get a strong boost because speed matters.",
        "- `Fit Score`: How well the role matches your resume and target lane based on title relevance plus skill overlap.",
        "- `Acceptance Score`: How attainable the role looks based on seniority, years required, location, and hard requirement penalties.",
        "- `Execution Score`: How confident the tool is that your current evidence maps to actually doing the work and passing the interview loop.",
        "- `Trajectory Score`: How much the role appears to move you toward cyber-relevant work like logs, incidents, systems, tooling, and troubleshooting depth.",
        "- `Entry Viability`: How realistic this role is as an actual way in for you right now, combining attainability, bridge value, trajectory, and whether the title is secretly too senior.",
        "- `Response Likelihood`: Rough practical callback odds for you specifically. This favors local, non-prestige, boring-but-hireable funnels more than shiny roles with worse real response odds.",
        "- `Apply Priority`: Best move right now, not just best-looking role. This leans harder on response likelihood, entry viability, freshness, and speed-to-action.",
        "- `Narrative Score`: How well the role matches the story your resume currently tells. High means it reads like a believable next step for you.",
        "- `Effort Score`: Estimated application and interview burden. Lower is better and helps the ROI score.",
        "- `Path Tier`: `Tier A` is closest to security operations, `Tier B` is the strongest IT/support bridge, and `Tier C` is a selective cyber-adjacent bridge like IAM, access, or risk.",
        "- `Execution Tier`: `Ready now`, `Ramp-up likely`, `Interview risk`, or `Not ready` to anchor what the execution score means.",
        "- `Company Group`: Backward-compatible summary label derived from richer company metadata. Useful for quick scanning, but no longer the whole story.",
        "- `Company Tags`: Multi-tag view of what the company is, like `security`, `mssp`, `tech`, or `saas`.",
        "- `Company Effectiveness`: Learned source score from past runs. High means that company has consistently produced shortlist-worthy roles for you.",
        "- `Difficulty`: Rough company competition tier. High means brand/prestige/applicant volume should make the funnel tougher.",
        "- `Skill Match %`: Weighted overlap between your resume and important skills mentioned in the job post for that lane.",
        "- `Title Fit`: How strongly the job title itself matches the target lane before resume overlap is considered.",
        "- `Years Req`: Highest experience requirement detected in the job text. `0` means none was clearly found.",
        "",
    ]

    geo_ambiguous_cyber_leads = geo_ambiguous_cyber_leads or []
    if geo_ambiguous_cyber_leads:
        lines.extend(["## Geo-Ambiguous Cyber Leads", "", "Cyber-relevant roles that look promising but are blocked from the strict queue because the posting location is fuzzy, like `North America` instead of explicit `US`.", ""])
        for index, job in enumerate(geo_ambiguous_cyber_leads, start=1):
            lines.extend(
                [
                    f"### {index}. [{markdown_escape(job['title'])}]({job['url']})",
                    "",
                    f"- `Company`: {markdown_escape(job['company'])}",
                    f"- `Path Tier`: {job.get('path_tier', '')}",
                    f"- `Resume`: {job.get('resume', '')}",
                    f"- `Original Location`: {markdown_escape(job['location'])}",
                    f"- `Final / Entry Viability / Apply Priority`: {job['final_score']} / {job.get('entry_viability_score', '')} / {job.get('apply_priority_score', '')}",
                    f"- `Why It Is Not In The Queue`: {markdown_escape(job.get('geo_ambiguous_note', 'Geo-ambiguous location'))}",
                    "",
                ]
            )

    for track_name, track in tracks.items():
        sections = jobs_by_track.get(track_name, {})
        lines.append(f"## {track['label']}")
        lines.append("")
        for section_key, section_heading, intro in [
            ("primary", "Main Targets", "Best current shortlist for this lane."),
            ("stretch", "Stretch Cyber", "Cyber roles that are less clean fits but may still be worth a selective shot if you want reach applications."),
            ("overflow", "Low Priority But Possible", "Older or disguised-mid-level roles that may still be worth a selective shot."),
            ("volume", "Volume Mode", "Extra decent targets if you want a bigger application day instead of a tighter shortlist."),
            ("internships", "Internships / New Grad Scout", "Internship and new-grad roles that match the lane, shown with relaxed location rules so they do not disappear from view."),
        ]:
            jobs = sections.get(section_key, [])
            lines.extend([f"### {section_heading}", "", intro, ""])
            if not jobs:
                lines.extend(["_No current matches right now._", ""])
                continue
            for index, job in enumerate(jobs, start=1):
                lines.extend(
                    [
                        f"#### {index}. [{markdown_escape(job['title'])}]({job['url']})",
                        "",
                        f"> **Company:** {markdown_escape(job['company'])}  ",
                        f"> **Decision:** {job['decision']}  ",
                        f"> **Priority:** Final {job['final_score']} | ROI {job['roi_score']} | Freshness {job['freshness_label']} ({format_days_old(job.get('freshness_days_old'))})  ",
                        f"> **Reality Check:** Years {job['years_required']} | Difficulty {job['difficulty_tier']} | Junior+ {'Yes' if job.get('junior_plus') else 'No'} | Competition {job['competition_magnetism']} | Disguised Mid-Level {'Yes' if job.get('disguised_mid_level') else 'No'}",
                        "",
                    ]
                )
                detail_lines = [
                    ("Fit Score", job["fit_score"]),
                    ("Acceptance Score", job["acceptance_score"]),
                    ("Execution Score", job["execution_score"]),
                    ("Trajectory Score", job.get("trajectory_score", "")),
                    ("Entry Viability", job.get("entry_viability_score", "")),
                    ("Response Likelihood", job.get("response_likelihood_score", "")),
                    ("Apply Priority", job.get("apply_priority_score", "")),
                    ("Narrative Score", job["narrative_score"]),
                    ("Effort Score", job["effort_score"]),
                    ("Path Tier", job.get("path_tier", "")),
                    ("Stepping Stone", job.get("stepping_stone_label", "")),
                    ("Execution Tier", job["execution_tier"]),
                    ("Company Group", job["company_group"]),
                    ("Company Tags", ", ".join(job["company_tags"]) if job["company_tags"] else "None"),
                    ("Company Difficulty", job["company_difficulty"]),
                    ("Hiring Pattern", job["company_hiring_pattern"]),
                    ("Industry", job["company_industry"]),
                    ("Competition Magnetism", job["competition_magnetism"]),
                    ("Junior+", "Yes" if job.get("junior_plus") else "No"),
                    ("Company Effectiveness", f"{job['company_effectiveness_score']} ({job['company_effectiveness_label']})"),
                    ("Location", markdown_escape(job["location"])),
                    ("Source Type", job["source_type"]),
                    ("Source", job["source"]),
                    ("Track", job["track"]),
                    ("Resume", job["resume"]),
                    ("Application Status", job.get("application_status", "NEW")),
                    ("Discovery", job.get("discovery_state", "SEEN")),
                    ("Update Reason", markdown_escape(job.get("update_reason", "")) if job.get("update_reason") else "None"),
                    ("Applied On", job.get("applied_on", "") or "Not yet"),
                    ("Follow Up On", job.get("follow_up_on", "") or "Not set"),
                    ("Skill Match %", job["skill_match_score"]),
                    ("Title Fit", job["title_score"]),
                    ("Overflow Reason", job.get("overflow_reason") or "Main shortlist"),
                    ("Junior+ Reasons", markdown_escape(job.get("junior_plus_reasons", "")) if job.get("junior_plus_reasons") else "None"),
                    ("Competition Reasons", markdown_escape(job.get("competition_magnetism_reasons", "")) if job.get("competition_magnetism_reasons") else "None"),
                    ("Disguised Reasons", markdown_escape(job.get("disguised_reasons", "")) if job.get("disguised_reasons") else "None"),
                    ("Fit Notes", markdown_escape(job["fit_notes"]) if job["fit_notes"] else "None"),
                    ("Entry Viability Notes", markdown_escape(job.get("entry_viability_notes", "")) if job.get("entry_viability_notes") else "None"),
                    ("Response Likelihood Notes", markdown_escape(job.get("response_likelihood_notes", "")) if job.get("response_likelihood_notes") else "None"),
                    ("Apply Priority Notes", markdown_escape(job.get("apply_priority_notes", "")) if job.get("apply_priority_notes") else "None"),
                    ("Acceptance Notes", markdown_escape(job["acceptance_notes"]) if job["acceptance_notes"] else "None"),
                    ("Execution Notes", markdown_escape(job["execution_notes"]) if job["execution_notes"] else "None"),
                    ("Trajectory Notes", markdown_escape(job.get("trajectory_notes", "")) if job.get("trajectory_notes") else "None"),
                    ("Narrative Notes", markdown_escape(job["narrative_notes"]) if job["narrative_notes"] else "None"),
                    ("ROI Notes", markdown_escape(job["roi_notes"]) if job["roi_notes"] else "None"),
                    ("Why You Might Get Rejected", markdown_escape(job["risk_notes"]) if job["risk_notes"] else "Low obvious rejection risk"),
                ]
                lines.extend([f"- `{label}`: {value}" for label, value in detail_lines])
                lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_review_csv(path, jobs_by_track, *, tracks):
    candidates = get_review_candidates(jobs_by_track, tracks)

    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.writer(file_handle)
        writer.writerow(
            [
                "Track",
                "Track Label",
                "Rank",
                "Company",
                "Title",
                "Current Decision",
                "Final Score",
                "ROI Score",
                "Fit Score",
                "Acceptance Score",
                "Execution Score",
                "Narrative Score",
                "Effort Score",
                "Difficulty",
                "Years Req",
                "URL",
                "Your Decision",
                "Move",
                "Confidence (1-5)",
                "Notes",
            ]
        )

        for track_name, track_label, index, job in candidates:
            writer.writerow(
                [
                    track_name,
                    track_label,
                    index,
                    job["company"],
                    job["title"],
                    job["decision"],
                    job["final_score"],
                    job["roi_score"],
                    job["fit_score"],
                    job["acceptance_score"],
                    job["execution_score"],
                    job["narrative_score"],
                    job["effort_score"],
                    job["difficulty_tier"],
                    job["years_required"],
                    job["url"],
                    "",
                    "",
                    "",
                    "",
                ]
            )


def write_review_markdown(path, jobs_by_track, *, tracks, today):
    candidates = get_review_candidates(jobs_by_track, tracks)
    lines = [
        "# Ranking Calibration Review",
        "",
        f"Generated on `{today}` from the latest ranked output.",
        "",
        "Use this file or `ranking_review.csv` to mark where your judgment disagrees with the tool.",
        "",
        "## How To Use",
        "",
        "1. Look at the top jobs below.",
        "2. For any role you disagree with, note what the decision should be instead.",
        "3. Note whether it should move `up`, `down`, or stay `same`.",
        "4. Add a short reason like `too optimistic`, `too pessimistic`, `better bridge role`, or `story mismatch`.",
        "",
        "The companion CSV is easier to fill in if you want structured feedback.",
        "",
    ]

    if not candidates:
        lines.extend(["No current ranked jobs were available for calibration.", ""])
    else:
        current_track = None
        for track_name, track_label, index, job in candidates:
            if track_name != current_track:
                lines.append(f"## {track_label}")
                lines.append("")
                current_track = track_name

            lines.extend(
                [
                    f"### {index}. [{markdown_escape(job['title'])}]({job['url']})",
                    "",
                    f"- `Company`: {markdown_escape(job['company'])}",
                    f"- `Current Decision`: {job['decision']}",
                    f"- `Final / ROI`: {job['final_score']} / {job['roi_score']}",
                    f"- `Fit / Acceptance / Execution / Narrative / Effort`: {job['fit_score']} / {job['acceptance_score']} / {job['execution_score']} / {job['narrative_score']} / {job['effort_score']}",
                    f"- `Difficulty`: {job['difficulty_tier']}",
                    f"- `Why The Tool Thinks This`: {markdown_escape(job['fit_notes']) if job['fit_notes'] else 'No fit note'}; {markdown_escape(job['acceptance_notes']) if job['acceptance_notes'] else 'No acceptance note'}; {markdown_escape(job['narrative_notes']) if job['narrative_notes'] else 'No narrative note'}",
                    "- `Your Decision`: ",
                    "- `Move`: ",
                    "- `Reason`: ",
                    "",
                ]
            )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")


def write_html_report(path, jobs_by_track, *, tracks, today, location_mode, location_mode_labels):
    style = """
body {
    margin: 0;
    background: #f6f1e8;
    color: #1f2933;
    font-family: "Trebuchet MS", "Segoe UI", sans-serif;
}
.page {
    max-width: 1500px;
    margin: 0 auto;
    padding: 32px 24px 48px;
}
.hero {
    background: linear-gradient(135deg, #f4d58d, #d6e8db);
    border: 1px solid #d8c9aa;
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 24px;
}
.hero h1 { margin: 0 0 8px; font-size: 30px; }
.hero p { margin: 0; max-width: 900px; line-height: 1.5; }
.section { margin-top: 28px; }
.section h2 { margin: 0 0 12px; font-size: 22px; }
.table-wrap { overflow-x: auto; background: #fffdfa; border: 1px solid #dfd4c2; border-radius: 16px; box-shadow: 0 10px 30px rgba(56, 38, 14, 0.06); }
table { width: 100%; border-collapse: collapse; }
thead th { position: sticky; top: 0; background: #f0e6d7; text-align: left; font-size: 13px; letter-spacing: 0.02em; }
th, td { padding: 12px 14px; border-bottom: 1px solid #ece2d3; vertical-align: top; }
tbody tr:nth-child(even) { background: #fffaf2; }
.score { display: inline-block; min-width: 44px; padding: 4px 8px; border-radius: 999px; text-align: center; font-weight: 700; font-family: Consolas, "Courier New", monospace; }
.score-high { background: #d8f0dc; color: #1f6b36; }
.score-mid { background: #fff0c2; color: #8a5a00; }
.score-low { background: #f6d3cd; color: #8e2f21; }
.decision { display: inline-block; padding: 4px 9px; border-radius: 999px; font-size: 12px; font-weight: 700; letter-spacing: 0.03em; }
.decision-apply { background: #cce7ff; color: #0b5394; }
.decision-maybe { background: #ffe3bf; color: #a45300; }
.decision-backup { background: #e6e6e6; color: #4e5861; }
.decision-lottery { background: #f8d8d8; color: #8a2432; }
.title-link { color: #0d5c63; text-decoration: none; font-weight: 700; }
.title-link:hover { text-decoration: underline; }
.notes { line-height: 1.45; white-space: normal; }
.meta { color: #5a6670; font-size: 13px; }
.guide { margin-top: 28px; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 14px; }
.card { background: #fffdfa; border: 1px solid #dfd4c2; border-radius: 14px; padding: 16px; }
.card h3 { margin: 0 0 8px; font-size: 15px; }
.card p { margin: 0; line-height: 1.45; color: #4c5862; }
"""

    sections = []
    for track_name, track in tracks.items():
        jobs = jobs_by_track.get(track_name, {}).get("primary", [])
        if not jobs:
            continue

        rows = []
        for job in jobs:
            rows.append(
                f"""
                <tr>
                    <td><span class="decision {decision_class(job['decision'])}">{escape_html(job['decision'])}</span></td>
                    <td><span class="score {score_class(job['final_score'])}">{job['final_score']}</span></td>
                    <td><span class="score {score_class(job['roi_score'])}">{job['roi_score']}</span></td>
                    <td>{escape_html(job['freshness_label'])}</td>
                    <td><span class="score {score_class(job['fit_score'])}">{job['fit_score']}</span></td>
                    <td><span class="score {score_class(job['acceptance_score'])}">{job['acceptance_score']}</span></td>
                    <td><span class="score {score_class(job['execution_score'])}">{job['execution_score']}</span></td>
                    <td><span class="score {score_class(job['narrative_score'])}">{job['narrative_score']}</span></td>
                    <td><span class="score {score_class(100 - min(job['effort_score'], 100))}">{job['effort_score']}</span></td>
                    <td>{escape_html(job['company'])}</td>
                    <td>
                        <a class="title-link" href="{escape_html(job['url'])}" target="_blank" rel="noreferrer">{escape_html(job['title'])}</a>
                        <div class="meta">{escape_html(job['source_type'])} | {escape_html(job['source'])} | track {escape_html(job['track'])} | path {escape_html(job.get('path_tier', ''))} | resume {escape_html(job['resume'])} | years {job['years_required']} | difficulty {escape_html(job['difficulty_tier'])} | group {escape_html(job['company_group'])} | source score {job['company_effectiveness_score']} ({escape_html(job['company_effectiveness_label'])}) | status {escape_html(job.get('application_status', 'NEW'))}</div>
                    </td>
                    <td>{escape_html(job['location'])}</td>
                    <td class="notes">{escape_html(job['fit_notes'])}</td>
                    <td class="notes">{escape_html(job['acceptance_notes'])}</td>
                    <td class="notes">{escape_html(job['execution_tier'])} | {escape_html(job['execution_notes'])}</td>
                    <td class="notes">{escape_html(job['narrative_notes'])}</td>
                    <td class="notes">{escape_html(job['roi_notes'])} | effort {job['effort_score']}</td>
                    <td class="notes">{escape_html(job['risk_notes'])}</td>
                    <td><a class="title-link" href="{escape_html(job['url'])}" target="_blank" rel="noreferrer">Open job</a></td>
                </tr>
                """
            )

        sections.append(
            f"""
            <section class="section">
                <h2>{escape_html(track['label'])}</h2>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Decision</th><th>Final</th><th>ROI</th><th>Freshness</th><th>Fit</th><th>Attain</th><th>Exec</th><th>Story</th><th>Effort</th><th>Company</th><th>Title</th><th>Location</th><th>Fit Notes</th><th>Acceptance Notes</th><th>Execution Notes</th><th>Narrative Notes</th><th>ROI Notes</th><th>Risk</th><th>Link</th>
                            </tr>
                        </thead>
                        <tbody>{''.join(rows)}</tbody>
                    </table>
                </div>
            </section>
            """
        )

    guide = """
    <section class="section">
        <h2>Score Guide</h2>
        <div class="guide">
            <div class="card"><h3>Final Score</h3><p>Overall priority rank used for sorting. Higher means a stronger combined target after fit, attainability, execution, narrative alignment, and ROI are blended.</p></div>
            <div class="card"><h3>ROI Score</h3><p>Estimated return on your application time. Higher means stronger probability-to-effort balance.</p></div>
            <div class="card"><h3>Freshness</h3><p>How recently the job appears to have been posted. Newer jobs get a strong boost because early applications matter.</p></div>
            <div class="card"><h3>Fit Score</h3><p>How well the role matches your resume and target lane based on title relevance plus skill overlap.</p></div>
            <div class="card"><h3>Acceptance Score</h3><p>How attainable the role looks based on seniority, years required, location, and hard requirement penalties.</p></div>
            <div class="card"><h3>Execution Score</h3><p>How much confidence the tool has that your current evidence maps to real execution depth and interview performance.</p></div>
            <div class="card"><h3>Narrative Score</h3><p>How well the role fits the story your resume already tells. High means the role reads like a believable next step.</p></div>
            <div class="card"><h3>Difficulty</h3><p>High means prestige and applicant volume should make the company harder to break into even when the posting looks friendly.</p></div>
            <div class="card"><h3>Company Effectiveness</h3><p>Learned source score from earlier runs. Higher means that company has consistently produced shortlist-worthy roles instead of mostly noise.</p></div>
            <div class="card"><h3>Open Job</h3><p>The title and the final link column are both clickable, so you can open the posting directly from the report.</p></div>
        </div>
    </section>
    """

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Job Intelligence Report</title>
    <style>{style}</style>
</head>
<body>
    <div class="page">
        <section class="hero">
            <h1>Job Intelligence Report</h1>
            <p>Aligned view for your daily shortlist with color-coded scores, wrapped titles, and clickable job links. Generated on {escape_html(today)}. Location mode: {escape_html(location_mode_labels.get(location_mode, location_mode))}.</p>
        </section>
        {''.join(sections)}
        {guide}
    </div>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as handle:
        handle.write(document)
