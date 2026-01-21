# 4Charm Codebase Suggestions

Based on a comprehensive review of the codebase, here are suggested improvements to enhance quality, maintainability, and reliability.

## 1. Testing Coverage (High Priority)
The current test suite (`tests/test_scraper_utils.py`) is minimal.
- **Unit Tests**: Add tests for core logic in `FourChanScraper`:
  - `extract_media_from_posts`: Verify it correctly filters and creates `MediaFile` objects.
  - `sanitize_filename`: Ensure all edge cases (reserved names, long filenames) are handled.
  - `download_file`: Mock the network and file system to test retry logic and resume capability.
- **Mocking**: Use `unittest.mock` or `pytest-mock` to simulate 4chan API responses. avoiding reliance on live network calls during tests.

## 2. Refactoring & Architecture
- **Separation of Concerns**: Split `FourChanScraper` into two classes:
  - `FourChanAPI`: Handles all network requests, JSON parsing, and rate limiting.
  - `Downloader`: Handles file I/O, disk space checks, and resume logic.
- **Dependency Injection**: Inject the `scraper` instance into `MainWindow` and `workers` instead of instantiating it directly. This makes it easier to pass a mock scraper for GUI testing.

## 3. Error Handling & Robustness
- **Specific Exceptions**: Replace broad `except Exception` blocks (e.g., in `scraper.py`) with specific exceptions (`requests.ConnectionError`, `OSError`, `json.JSONDecodeError`). This prevents masking legitimate bugs.
- **Validation**: Add stricter validation for download paths and user inputs.

## 4. Code Style & Documentation
- **Type Hints**: Complete type hinting for all method signatures, especially in `FourChanScraper`.
- **Docstrings**: Add docstrings to `MultiUrlDownloadWorker` and other complex classes explaining their lifecycle and signals.

## 5. Performance (Future Consideration)
- **Async I/O**: The current threading model works well, but migrating to `asyncio` and `aiohttp` could offer better resource usage for high-concurrency downloading scenarios.

## 6. Configuration Management
- **External Config**: Move constants from `config.py` (like `USER_AGENT`) to an external configuration file or environment variables to allow easier updates without code changes.
