# TODO — audiobooker

## Open issues

- [ ] #6 Dependency Dashboard (Renovate bot meta-issue, not actionable)

## Gaps

- [ ] `pyproject.toml` `Homepage` and `Repository` point at `https://github.com/OpenJarbas/audiobooker`; update to the canonical `TigreGotico/audiobooker` remote.
- [ ] Stated repo description lists "Anna's Archive" as a source, but no Anna's Archive scraper exists in `audiobooker/scrappers/` and it is not referenced in README/docs — either implement it or correct the description.
- [ ] No type checker (mypy/pyright) configured; only ruff lint runs. Core dataclasses are untyped at the dict boundaries (`external_ids`, `extra`).
- [ ] `_worker` in `search.py` swallows every source exception with a bare `except Exception: pass`, hiding parser breakage outside the nightly-live job.

(Tests present: ~375 test functions across 23 modules with VCR cassettes. Full gh-automations CI present: build-tests, coverage, license_check, lint, release_workflow/publish-alpha, publish_stable, plus nightly-live, conventional-label, pip_audit, release-preview, repo-health.)

## Code TODOs

None found.
