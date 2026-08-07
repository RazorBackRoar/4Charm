# Contributing to 4Charm

Thanks for your interest in contributing to **4Charm**
([RazorBackRoar/4Charm](https://github.com/RazorBackRoar/4Charm)).

This guide matches the RazorBackRoar organization standard. Project-specific
build details live in [BUILD_AND_RELEASE.md](BUILD_AND_RELEASE.md).

## Code of Conduct

Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
By contributing, you agree to uphold it.

## Security

Do **not** file public issues for vulnerabilities. See [SECURITY.md](SECURITY.md).

## How to Contribute

1. Prefer a focused change (one intent per PR).
2. Open a Pull Request against `main`.
3. Keep CI green. Do not force-push to `main`.
4. Use Conventional Commits when writing commit messages
   (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `ci:`).

Agent note: automated agents must not create branches, commit, push, open PRs,
or delete branches unless the user explicitly asks for that Git action. In this
workspace, `razor-autosync` may commit locally; publishing uses
`RAZORCORE_AUTO_PUSH=1`.

## Development Setup

See [BUILD_AND_RELEASE.md](BUILD_AND_RELEASE.md) for prerequisites, build,
packaging, and release steps for this repository.

Architecture, module seams, and testing patterns are documented in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Testing

Run the full suite from the repository root:

```bash
uv run ruff check .
uv run ty check src --python-version 3.14
uv run pytest tests/ -q
```

Focused areas when touching specific subsystems:

| Subsystem | Tests |
|-----------|-------|
| Scraper, paths, dedup | `tests/test_scraper_utils.py`, `tests/test_paths.py`, `tests/test_scraper_logic.py` |
| Workers, cancel | `tests/test_workers.py`, `tests/test_cancel_reset.py` |
| HTTP / redirects | `tests/test_session.py` |
| GUI | `tests/test_gui.py` (sets `QT_QPA_PLATFORM=offscreen`) |

Prefer injecting a `FakeBoardApi` into `FourChanScraper(board_api=…)` over
monkeypatching `safe_get` at the module level. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#testing-without-live-4chan) for
examples.

CI covers lint, types, and unit tests. It does **not** exercise live 4chan
downloads or packaged-app behavior on macOS.

## Pull Requests

- Describe **why** the change is needed.
- Link related issues when applicable.
- Include screenshots for UI changes when helpful.
- Keep diffs minimal — avoid unrelated refactors.

## License

By contributing, you agree that your contributions are licensed under the same
terms as this repository (see [LICENSE](LICENSE)).
