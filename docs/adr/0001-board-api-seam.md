# ADR-0001 — BoardApi as the scraper's transport seam

Status: accepted (2026-07-12)

## Context

The 4ChanScraper historically imported `safe_get` from
`four_charm.transport.session` and called it directly in three places
(`get_thread_data`, `get_catalog_data`, `download_file`). Rate-limit
handling, redirect policy, and per-hop host allowlisting each lived in
two places (the session and the call site), so changing one without
the other silently desynced them.

The transport layer had exactly one adapter (`requests.Session`), which
made the seam hypothetical per the architecture review glossary: "one
adapter = hypothetical seam, two adapters = real seam."

## Decision

Introduce a `BoardApi` Protocol with three fetch primitives
(`fetch_thread`, `fetch_catalog`, `stream_range`) and a single
`LiveBoardApi` concrete adapter that wraps `safe_get` + the configured
`requests.Session`. The scraper takes a `BoardApi | None` in its
constructor and defaults to a `LiveBoardApi(session)`.

Tests that previously monkeypatched `four_charm.core.scraper.safe_get`
now inject a `FakeBoardApi` instead. The seam is now real because
production runs and tests run different code paths.

## Consequences

- 4chan fetch paths stay inside the rate-limited flow (the protocol
  guarantees `LiveBoardApi` is the only thing calling `safe_get`).
- The scraper no longer names `requests` in its public surface.
- Cross-concerns (rate limit, redirect policy, retry policy) live
  behind one interface; future adapters (e.g. a recording fake for
  integration tests, a mock for offline CI) drop in without changing
  the scraper.
- Tests can target a 3-method fake instead of patching module-level
  `safe_get` references.

## Invariant preserved

4chan fetch paths must remain inside the rate-limited flow. Any
new `BoardApi` adapter must call `RetryPolicy.adaptive_delay` (or
document why it does not need to). The default `LiveBoardApi` honours
this; non-default adapters must do so explicitly.
