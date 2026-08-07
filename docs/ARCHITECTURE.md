# Architecture — 4Charm

Developer-oriented map of how 4Charm downloads media, where the seams are,
and how to test without live 4chan access.

For build and release steps see [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md).
For security hardening in v2.0.1 see [CHANGELOG.md](../CHANGELOG.md#201---2026-07-12).

## Package layout

| Path | Role |
|------|------|
| `src/four_charm/main.py` | App entry, startup banner, About |
| `src/four_charm/gui/main_window.py` | PySide6 UI, URL editor, progress log |
| `src/four_charm/gui/workers.py` | `QObject` download workers + `ThreadPoolExecutor` |
| `src/four_charm/core/scraper.py` | `FourChanScraper` — orchestration, queue, downloads |
| `src/four_charm/transport/api.py` | `BoardApi` protocol + `LiveBoardApi` adapter |
| `src/four_charm/transport/session.py` | `create_session`, `safe_get` (redirect allowlisting) |
| `src/four_charm/core/paths.py` | `PathBuilder`, filename/folder sanitization |
| `src/four_charm/core/signals.py` | `DownloadTask` progress payload |
| `src/four_charm/config.py` | Defaults + persisted user settings (`~/.4charm/config.json`) |

Supporting modules extracted from the scraper for focused testing:

- `core/retry.py` — `RetryPolicy` (exponential backoff + adaptive rate limit)
- `core/chunking.py` — `ChunkSelector` (8 KB / 64 KB / 256 KB by file size)
- `core/error_format.py` — `ErrorFormatter` (user-facing messages + categories)
- `core/dedup.py` — SHA-256 duplicate suppression (mutex-protected)
- `core/urls.py` — paste parsing, host allowlists, queue dedupe

## End-to-end download flow

```text
MainWindow
  └─ DownloadWorker / MultiUrlDownloadWorker  (gui/workers.py)
       └─ FourChanScraper                       (core/scraper.py)
            ├─ BoardApi.fetch_thread / fetch_catalog / stream_range
            │    └─ LiveBoardApi → safe_get     (transport/)
            ├─ RetryPolicy.adaptive_delay       (rate limit between fetches)
            ├─ PathBuilder.build                (folder + WEBM routing)
            ├─ DedupTracker                     (skip known SHA-256 hashes)
            └─ ChunkSelector + BandwidthMonitor   (streaming + ETA)
```

1. The GUI parses pasted URLs (`core/urls.py`), caps the queue, and starts a
   worker on a `QThread`.
2. The worker scrapes each URL (thread, catalog, board, or direct media) via
   `BoardApi`, builds a `MediaFile` list, and downloads concurrently through
   `ThreadPoolExecutor` (size from `config.MAX_WORKERS`).
3. Each file streams through `BoardApi.stream_range` with adaptive chunk sizes,
   optional MD5 verification, and resume via HTTP `Range` when a partial file
   exists on disk.
4. Progress crosses the thread boundary as a single `DownloadTask` object
   (`Signal(object)`), not a positional tuple.

## Transport seam (`BoardApi`)

The scraper depends on the `BoardApi` protocol; production uses `LiveBoardApi`,
which is the only code path that calls `safe_get`.

```python
# Production (default)
scraper = FourChanScraper()

# Tests — inject a fake that returns canned responses
scraper = FourChanScraper(board_api=FakeBoardApi())
```

`safe_get` follows redirects manually (max 5 hops) and rejects any hop whose
host is not in the fetch allowlist (`core/urls.is_allowed_fetch_host`). This
applies to API JSON and media downloads alike.

Allowed fetch suffixes: `.4chan.org`, `.4channel.org`, `.4cdn.org`, plus exact
hosts such as `a.4cdn.org` and `i.4cdn.org`. Pasted URLs are filtered with the
narrower board-host list (`is_allowed_4chan_host`) before they enter the queue.

See [ADR-0001](adr/0001-board-api-seam.md) for the decision record.

## Path safety (`PathBuilder`)

All writes go under the user-chosen download root:

- Folder names come from thread titles or `board-thread_id` patterns, sanitized
  and length-capped (`MAX_FOLDER_NAME_LENGTH`, default 40).
- `.webm` files land in a `WEBM/` subfolder per thread directory.
- `within_download_dir` resolves paths and raises `ValueError` if a sanitized
  name would escape the download root.

Filenames are sanitized through `razorcore.filesystem.sanitize_filename` with
`config.MAX_FILENAME_LENGTH` (default 200).

## Progress payload (`DownloadTask`)

Workers emit `progress = Signal(object)` carrying a frozen `DownloadTask`
dataclass (`core/signals.py`):

| Field | Meaning |
|-------|---------|
| `completed` | Files finished in this run |
| `total` | Files scheduled |
| `filename` | Most recently completed file |
| `speed_mb_s` | Rolling average MB/s |
| `thread_title` | Display label for multi-URL runs |
| `thread_index` | 1-based thread index (0 for single-URL) |
| `eta_s` | Estimated seconds remaining |

ETA formatting lives in `BandwidthMonitor.format_eta`; the GUI reads named
attributes instead of positional tuple slots.

See [ADR-0002](adr/0002-downloadtask-progress-schema.md) for the decision record.

## Workers and cancel

Download workers intentionally stay as `QObject` + `moveToThread`, not
`razorcore.threading.BaseWorker`. BaseWorker exposes a 3-arg progress shape that
does not fit scraper cancel semantics or the seven-field ETA surface.

- **Cancel:** `worker.cancel()` → `scraper.cancel_downloads()` (shared flag;
  reset before each new run).
- **Concurrency:** pool size follows `config.MAX_WORKERS` (default
  `min(5, cpu_count())`, user-tunable up to 20).

## Retry and rate limiting

`RetryPolicy` owns two related behaviors:

1. **Per-request adaptive delay** — `adaptive_delay(success=…)` sleeps
   `current_delay`, shrinking on success and growing on failure (capped by
   `MAX_DELAY`).
2. **Per-download retry backoff** — `calculate_retry_delay(attempt)` uses
   exponential growth with 0–1 s jitter, capped at `MAX_RETRY_DELAY` (60 s).

All 4chan fetches must stay inside this flow. Do not bypass throttling or call
`requests` directly from the scraper.

## Configuration

Runtime defaults live in `config.py`. User overrides persist to
`~/.4charm/config.json` (created on first save). Notable defaults:

| Key | Default | Notes |
|-----|---------|-------|
| `MAX_WORKERS` | `min(5, cpu_count())` | Concurrent download threads |
| `POOL_CONNECTIONS_MULTIPLIER` | 4 | Session pool = workers × multiplier |
| `MAX_RETRIES` | 3 | Per-file download attempts |
| `ADAPTIVE_CHUNK_THRESHOLDS` | 10 MB, 100 MB | Chunk size bucket boundaries |
| `CHUNK_SIZES` | 8 KB, 64 KB, 256 KB | Streaming read sizes |

## Testing without live 4chan

| Area | Where to look | Pattern |
|------|---------------|---------|
| Scraper / paths | `tests/test_scraper_utils.py`, `tests/test_paths.py` | Inject `FakeBoardApi`; set `scraper.download_dir` to `tmp_path` |
| Workers / cancel | `tests/test_workers.py`, `tests/test_cancel_reset.py` | Mock scraper methods; assert cancel flag reset |
| GUI | `tests/test_gui.py` | `QT_QPA_PLATFORM=offscreen`; reuse `QApplication.instance()` |
| Transport / redirects | `tests/test_session.py` | Assert blocked hops outside allowlist |
| URLs | `tests/test_urls.py` | Host filter and paste token extraction |

CI runs lint, type-check, and unit tests only — it does **not** prove live
4chan behavior, Safari-free network conditions, or packaged-app launches.

### Minimal `FakeBoardApi` example

```python
class FakeBoardApi:
    def stream_range(self, url, *, headers=None, timeout=None):
        return FakeResponse()  # .status_code, .headers, .iter_content()

    def fetch_thread(self, board, thread_id):
        raise NotImplementedError

    def fetch_catalog(self, board):
        raise NotImplementedError

scraper = FourChanScraper(board_api=FakeBoardApi())
scraper.download_dir = tmp_path
```

## Related docs

- [ADR-0001 — BoardApi transport seam](adr/0001-board-api-seam.md)
- [ADR-0002 — DownloadTask progress schema](adr/0002-downloadtask-progress-schema.md)
- [DMG build notes](DMG_BUILD_README.md)
- [CI vendored razorcore](../ci/vendor/README.md)
- [AGENTS.md](../AGENTS.md) — agent entry points and verification commands
