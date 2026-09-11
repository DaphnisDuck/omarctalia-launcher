# Omarctalia Launcher

A searchable Omarchy menu and application launcher with optional vi navigation and live theme colors.

Version **1.0.0**. Tested on this machine with the Omarchy **4.0.3-1** package, Quickshell **0.3.1**, and Qt **6.11.2**. This is a local release; nothing has been published to a remote repository.

## Use

```sh
omarchy-shell shell summon omarctalia.launcher '{}'
```

Home presents Omarchy's categories. Typing searches descendants of the current category, with paths and descriptions in the results. Application descriptions come from their desktop entries; menu descriptions live in `MenuDescriptions.js`. Existing explicit menu descriptions take precedence.

| Key | Normal mode | Insert mode |
| --- | --- | --- |
| `j` / `k` | Select down / up | Type text |
| `h` / `l` | Back / open selection | Type text |
| `i` or `/` | Start searching | Type text |
| Up / Down | Select a result | Select a result |
| Enter | Open selection | Open selection |
| Alt+Left | Back | Back |
| Backspace | Back | Edit text |
| Escape | Close | Return to normal mode; keep query |
| `q` | Close | Type text |

Clicking an item opens it. Clicking outside closes the launcher. Opening a category returns to normal mode when vi controls are enabled.

To disable vi controls, set this near the top of the **installed** `Launcher.qml`:

```qml
property bool viModeEnabled: false
```

Typing then searches immediately, and Escape closes directly. The installer preserves this setting. Other source edits are backed up but not automatically merged during upgrades.

## Theme integration

Colors bind to Omarchy's shared `qs.Commons.Color.menu` object. Themes and user `shell.toml` overrides update the card, text, selection, borders, overlay, search field, Back button and scrollbar. App icons retain their own artwork.

## Reliability behavior

- Menu JSONC supports inline/block comments and trailing commas without changing quoted URLs or command strings.
- Partial overrides are merged **before** defaults are applied. Changing a description no longer removes an item's action, provider, or conditions.
- Malformed configuration or invalid parent/target relationships retain the last working menu and show a short status message. If defaults are unavailable at startup, Apps remains available. A missing optional user extension means no overrides.
- The menu-model helper is bundled, with upstream attribution, instead of imported from Omarchy's mutable internal file. Omarchy's menu definitions and theme interface remain external dependencies.
- Provider and availability lookups are bounded to 12 seconds, with a 2-second termination grace period. Failed provider results do not replace working choices; visiting the category again retries. Output is capped. Results from an obsolete configuration are discarded.
- Conditional actions remain hidden until an initial availability check succeeds. A failed subsequent check retains the previous result; an action can still fail if external state has changed.
- Installed icon files provide a fallback when Qt theme lookup fails. The shared icon index is cached for five minutes, invalidated after application-catalog changes, and scanned with a 10-second limit. Failures preserve the previous cache and back off for 30 seconds.
- Commands run through a detached supervisor. Unsuccessful exits produce a desktop notification and a journal entry tagged `omarctalia-launcher`. Interrupt/termination exits are treated as cancellation. Actions are not timed out: installers and applications may legitimately run for a long time.
- An application's successful launch request does **not** prove its window appeared. The supervisor reports command exit failures; it cannot detect every later application crash. Arbitrary menu actions remain trusted shell commands, just as in Omarchy's menu.

## Install or upgrade

Requires Python 3.9+, Quickshell, Bash, coreutils `timeout`, `find`, `uwsm-app`, `gtk-launch`, `notify-send`, `logger`, and the Omarchy theme interface. Testing also needs Node.js and QtTest.

From this source folder:

```sh
python3 install.py --check
python3 tests/run.py
python3 install.py
```

Default destination: `~/.config/omarchy/plugins/omarctalia.launcher/`.

The installer copies only runtime files, preserves the vi switch, publishes complete files by rename, and verifies their contents. Existing unrelated files are left alone. Backups are stored outside the watched plugin folder at `${XDG_STATE_HOME:-~/.local/state}/omarctalia-launcher/backups/`. An installation failure triggers rollback.

For a new installation, enable the plugin through Omarchy's plugin menu. Existing enabled installations reload their saved code automatically. If necessary, run `omarchy-shell shell rescanPlugins`.

## Roll back

The installer prints the exact snapshot directory. Restore it from this source folder:

```sh
python3 install.py --restore /absolute/path/to/snapshot
```

Restore validates the backup and refuses to overwrite files edited after the installation. Save those edits before using `--force`. Legacy timestamped backups from earlier development remain in the installed folder.

## Tests and maintenance

`python3 tests/run.py` checks:

- Partial overrides, JSONC edge cases, invalid schemas/hierarchy, quoted guard IDs, dynamic rows, and description coverage against the installed menu.
- Actual QML controls and key events in an offscreen window: categories, search, history, launching dispatch, vi enabled/disabled, and live color changes.
- Configuration recovery, failed and timed-out providers, successful retries, and guard timeout recovery.
- Chromium/Discord icon decoding, caching, invalidation, and preservation after a real filesystem-scan error.
- Detached command success/failure/cancellation, plus installation, settings preservation and rollback conflict protection.
- A deliberately failing QtTest assertion to ensure failures cannot silently pass the runner.

No real applications or menu actions are launched by these tests. Availability fixtures may execute harmless shell checks. Temporary files and installations live under a temporary directory.

Live Wayland focus, multiple displays, suspend/resume, and login-session behavior still need normal desktop use. Keep the stock Omarchy menu reachable, and rerun the suite after major Omarchy/Quickshell upgrades. The dependency check catches missing interfaces; it is not a guarantee of compatibility with future releases.

## Source layout

- `Launcher.qml`: UI, keyboard handling and dispatch.
- `MenuCatalog.qml`: menu files, app catalog and dynamic providers.
- `MenuModel.js`: bundled parser/model with local fixes.
- `MenuDescriptions.js`: editable menu descriptions.
- `IconResolver.qml`: icon lookup and cached fallback.
- `run-action.sh`: detached exit-status reporting.
- `install.py` and `tests/`: repeatable installation, rollback and validation.

See `UPSTREAM.md` and `LICENSE-OMARCHY` for the Omarchy-derived code's provenance and license.
