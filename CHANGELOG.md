# 1.3.0 — Virtual machine search

- Find local libvirt VMs by name or `vm`, with their current status shown.
- Start stopped guests, resume paused guests, and open running guests in virt-manager without restarting.
- Bound read-only discovery and validate local connection URIs and domain UUIDs before explicit launch actions.

# 1.2.1 — Dotfiles custom-menu support

- Allow an explicit real custom-menu path without following symlinks or relaxing file checks.
- Preserve this preference during local-installer upgrades.

# 1.2.0 — Search calculator

- Show arithmetic answers directly in search, including powers, percentages, parentheses, sqrt and abs.
- Enter or click copies the answer using Qt's clipboard and closes the launcher.
- Use a bounded arithmetic parser with no eval or shell execution; preserve ordinary application searches.

# 1.1.3 — Application search priority

- Rank matching applications before menu commands and categories, so searching Chromium puts the application before default-browser settings.

# 1.1.2 — Menu input and installer filesystem boundaries

- Read shared menus through a bounded no-follow helper with owner/type checks and a hard deadline.
- Replace FileView reads with periodic refresh requests, preserving last-good menus.
- Retain directory descriptors throughout installation, snapshots and restore; bound file reads and fsync publication.
- Add symlink, FIFO, file-growth, deadline, target-swap and backup-swap regression tests.

# 1.1.1 — Filesystem and resource boundaries

- Validate icon files beneath approved roots without following symlinks; pass bounded PNG snapshots to Qt.
- Cap scan bytes, records, visits, depth and image size; stop producers on overflow.
- Bound combined helper output and kill/reap process groups on overflow or timeout.
- Remove the hidden-menu-items warning while retaining command restrictions.

# 1.1.0 — Marketplace security review

- Stop evaluating shared menu strings as shell programs.
- Add a fixed command policy and typed Python broker; pin executable paths and sanitize child environment.
- Replace shell icon scanning with filesystem APIs.
- Hide unsupported or modified executable menu entries (see SECURITY.md).
- Add regression checks for menu injection and ambient PATH/startup hooks.

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
