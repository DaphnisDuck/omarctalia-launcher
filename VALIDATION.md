# Release validation — 1.0.0

Validated locally on 2026-09-11 with Omarchy package 4.0.3-1, Quickshell 0.3.1 and Qt 6.11.2.

- Seven pure-model tests passed: partial overrides, JSONC handling, schema/hierarchy errors, installed-description coverage, guard-ID quoting, dynamic-row replacement, and linked-menu visibility.
- QML suites passed for configuration/provider/guard recovery, icon decoding/cache behavior, icon failure preservation, and actual launcher keyboard/navigation/theme behavior.
- The runner detected an intentionally failing QtTest assertion; missing completion markers and nonzero process exits also fail the run.
- Detached action success, nonzero-exit notification, and cancellation behavior passed with mocked desktop notifications.
- Installation, vi-setting preservation, rollback, and protection against overwriting later edits passed in temporary directories.
- A full offscreen load using the real installed menu, availability checks, and icon directories loaded 10 root items, 152 condition results, and 9,986 icon names without menu/icon status errors. It did not launch a menu action.
- Python compilation, shell syntax, QML parsing, and whitespace checks passed.

The offscreen tests substitute only the Wayland surface for a plain item; UI tests suppress external actions and availability probes. Recovery tests exercise real subprocess success/failure/timeouts. Desktop focus, multi-monitor behavior, suspend/resume and future upstream versions are not certified by these checks.

Repeat the automated suite with `python3 tests/run.py`.
