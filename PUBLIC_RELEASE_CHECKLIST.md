# Public Release Checklist

Use this before creating a public version of the project.

## Do Not Publish

- Real resume files: `resume_cyber.txt`, `resume_it_support.txt`
- Real tracker files under `results/tracker/`
- Generated outputs under `results/current/`
- Diagnostics and archives under `results/diagnostics/` and `results/archive/`
- Scrape cache: `jobs_cache.json`
- Virtual environment: `.venv/`
- Python cache files: `__pycache__/`, `*.pyc`

## Safe To Publish

- Source code under `intake/`, `pipeline/`, `shared/`, and `sources/`
- `main.py`
- `requirements.txt`
- `CODEBASE_GUIDE.md`
- Example resume templates ending in `.example.txt`
- Example tracker files ending in `.example.md`
- GitHub Actions workflow under `.github/`
- This checklist

## Public Repo Process

1. Start from a clean copy of the private repo.
2. Delete private/generated files listed above.
3. Confirm `.gitignore` blocks private/generated files.
4. Replace personal docs with example/template docs.
5. Run the app with example data or document that real resume files are required.
6. Run `python scripts\smoke_test.py` to rebuild the public copy and run the safety checks.
7. Run `python scripts\check_release_safety.py --skip-git` if Git is not available in the terminal.
8. Review `git status` or GitHub Desktop before the first public commit.

Default public-copy folder: `../job_tool_public`
