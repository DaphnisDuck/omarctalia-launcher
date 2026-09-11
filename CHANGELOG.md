# Changes

## 1.0.0

- Display the title “Omarctalia Launcher”.
- Bundle the menu model and fix description-only overrides, JSONC parsing, schema validation, and menu hierarchy validation.
- Keep the working menu on configuration errors; show status messages for failed loads/lookups.
- Bound provider, availability and icon scans; preserve working data, reject obsolete results, and support retries.
- Cache and debounce icon scans instead of scanning on every summon.
- Report unsuccessful command exits through a detached supervisor.
- Add repeatable model, QML/key-event, failure-recovery, installer and rollback tests, including test-runner failure detection.
- Add a dependency check, setting-preserving installer, verified backups, and rollback conflict protection.

## 0.2.4

Working development baseline: category navigation, descriptions and search, optional vi controls, live theme colors, and installed-icon fallback.
