# Version 1.1.0 validation

Validated on 2026-09-11 with Omarchy 4.0.3-1 and Quickshell 0.3.1.

- Omarchy manifest validation passes.
- Six model tests pass, including JSONC parsing, partial overrides, and linked-menu visibility.
- Catalog QML tests pass for recovery, presentation overrides, and rejection of altered action/when/checked/provider fields.
- Broker tests reject unknown commands, option/path injection, and invalid dynamic choices. Shell metacharacters remain literal arguments. Poisoned PATH and shell startup-hook tests pass.
- Real QML icon decoding/cache/error-preservation and UI keyboard/search/theme tests pass offscreen. Action dispatch is mocked; no selected applications or administrative commands run in tests.
- Installer, vi preference preservation, rollback, and edit-conflict protection tests pass.
- Read-only broker guard enumeration completed against the installed system.

The former generated-shell guard and arbitrary shell-supervisor tests were removed together with those execution paths. This is not a security audit. Live Wayland focus, multiple displays and suspend/resume are not exhaustively tested. See SECURITY.md for intentionally unsupported menu operations.
