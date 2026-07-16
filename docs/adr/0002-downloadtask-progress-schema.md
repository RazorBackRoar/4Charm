# ADR-0002 — DownloadTask replaces the 7-arg progress Signal

Status: accepted (2026-07-12)

## Context

The workers' `progress` signal was declared as
`Signal(int, int, str, float, str, int, float)`. Every call site
(worker emit, GUI receive, test) had to know the positional order, and
the AGENTS.md note explicitly recorded the schema as intentional
because `razorcore.threading.BaseWorker` exposes a 3-arg progress
shape that does not fit the cancel/progress surface here.

The 7-tuple contract was the test surface, so adding/removing a field
touched four files. ETA formatting was also duplicated between
`BandwidthMonitor.format_eta` and the inline logic in
`main_window.update_progress`.

## Decision

Replace the 7-arg Signal with `Signal(object)` carrying a frozen
`DownloadTask` dataclass. The dataclass owns the seven fields the GUI
needs (count, total, filename, speed, thread title, thread index,
ETA) and concentrates tuple-construction in one factory.

The 7-arg schema persists as data inside the dataclass, not as the
Signal signature. The PySide6 thread-boundary contract is unchanged
(single object). `BandwidthMonitor.format_eta` is reused for the ETA
string so the format rules live in one place.

## Consequences

- Adding/removing a field touches the dataclass and the worker emit
  site only; the GUI and tests see named attributes.
- ETA formatting rules live in `BandwidthMonitor`, not in the GUI.
- The intentional 7-field schema is preserved on the wire as a single
  structured payload; the AGENTS.md note is still accurate.
- `Signal(object)` is well-supported by PySide6 and threads safely.

## Wire format

`progress` carries a single `DownloadTask` per emission. Receivers
access typed attributes (`task.completed`, `task.total`, etc.). The
prior positional 7-tuple is not preserved on the wire.
