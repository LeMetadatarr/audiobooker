# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `loyalbooks.py`: hours-to-seconds multiplier was 120, now correctly 3600
- `thoughtaudio.py`: fallback image was a Tag object instead of its `src` string
- `base.py`: removed unused exception imports

### Changed
- Packaging migrated from `setup.py` to `pyproject.toml`
- CI: updated to `actions/checkout@v4`, `actions/setup-python@v5`, Python 3.11
- CI: replaced deprecated `setup.py bdist_wheel` with `python -m build`
- CI: build tests now also run the unit test suite
- README rewritten to document the current scraper API
- `LoyalBooks.search_by_narrator` now returns an empty iterator (consistent with generator protocol)

## [0.2.6]  - 2019-12-12

### Changed

- Transfered ownership to [OpenJarbas](https://github.com/OpenJarbas)
- Made a changelog
- Added deprecation warning for broken HPPodcraft scrapper

[unreleased]: https://github.com/OpenJarbas/audiobooker/tree/dev
[0.5.2]: https://github.com/OpenJarbas/audiobooker/tree/0.5.2
