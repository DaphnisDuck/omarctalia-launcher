# Version 1.1.0 validation

## 1.4.1 checks

Full regression suite and Omarchy manifest validation pass. Added actual result-delegate checks for literal markup in names and descriptions, upgrade tests for disabled/session VM connections, and restore tests for all three historical runtime file sets. Historical restore preserves newer files and rejects unknown file lists. Icon discovery now uses an external timeout.

Validated on 2026-09-11 with Omarchy 4.0.3-1 and Quickshell 0.3.1.

- Omarchy manifest validation passes.
- Six model tests pass, including JSONC parsing, partial overrides, and linked-menu visibility.
- Catalog QML tests pass for recovery, presentation overrides, and rejection of altered action/when/checked/provider fields.
- Broker tests reject unknown commands, option/path injection, and invalid dynamic choices. Shell metacharacters remain literal arguments. Poisoned PATH and shell startup-hook tests pass.
- Real QML icon decoding/cache/error-preservation and UI keyboard/search/theme tests pass offscreen. Action dispatch is mocked; no selected applications or administrative commands run in tests.
- Installer, vi preference preservation, rollback, and edit-conflict protection tests pass.
- Read-only broker guard enumeration completed against the installed system.

The former generated-shell guard and arbitrary shell-supervisor tests were removed together with those execution paths. This is not a security audit. Live Wayland focus, multiple displays and suspend/resume are not exhaustively tested. See SECURITY.md for intentionally unsupported menu operations.

## 1.1.1 checks

Added checks for linked roots/files/directories, named pipes, icon entry/byte/traversal budgets, immutable image snapshots, helper output overflow, timeout, and descendant process cleanup. Real QML PNG decoding, cache preservation after budget failure, and navigation/theme tests are rerun for this version.

## 1.1.2 checks

Added menu owner/type/mode/size, symlink/FIFO, growth-during-read and hard-deadline tests. Installer tests now cover linked target/backup/snapshot paths, linked files, FIFOs, oversized existing files, target-directory replacement during publication and backup-directory replacement during snapshot creation. Writes remain on retained descriptors and outside sentinel files stay unchanged. The actual installed default and custom menus both pass the broker checks. Full QML and existing regression suites are rerun.

## 1.3.0 checks

Read-only discovery found the user's running VM on qemu:///system. Added mocked broker checks for stopped/running/paused/transitional states, rejected UUIDs and remote URIs, catalog limits, and fixed console argv. UI tests cover VM-name/alias search, category scope, status text, and dispatch. No real VM was started, resumed, or restarted by tests.

## 1.4.0 checks

Added URL recognition, limits and rejection tests plus mocked broker/UI dispatch checks. Query strings, fragments and shell-like URL text remain a single argument. The complete suite passes; no real browser navigation is performed by tests.
