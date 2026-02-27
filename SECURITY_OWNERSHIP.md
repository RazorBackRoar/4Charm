# Security Ownership

Updated: 2026-02-27

## Sensitive Hotspots
- `src/four_charm/core/scraper.py` (`network_boundary`)

## Current Risk
- Bus factor is `1` for network ingestion and parsing code.

## Mitigations Applied
- Added explicit hotspot coverage in `.github/CODEOWNERS`.
- Existing scraper tests retained as required baseline:
  - `tests/test_scraper_logic.py`
  - `tests/test_scraper_utils.py`

## Required to Fully Close Risk
1. Add at least one additional human maintainer for `core/scraper.py`.
2. Enforce code-owner review requirement in branch protection.
3. Rotate secondary maintainer through monthly scraper changes.
