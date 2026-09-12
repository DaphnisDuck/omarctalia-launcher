# Execution boundary

The marketplace review for submission #6377 identified automatic shell evaluation of shared menu data, ambient executable lookup, and arbitrary selected action strings. Version 1.1.0 removes these paths.

`CommandPolicy.json` contains fixed executable/argument lists and typed guards derived from the installed Omarchy 4.0.3 menu snapshot. `CommandPolicy.js` is the matching QML-side compatibility snapshot. Incoming executable fields must exactly match the policy for their item ID; no tokenization or shell interpretation of incoming menu data occurs. Presentation-only overrides remain supported. Neither runtime file is regenerated from shared menu input.

The broker accepts operation names and identifiers, not command strings. It looks up fixed argument lists itself. Only known fonts and power-profile choices can parameterize those operations; values must appear in a freshly queried list and cannot start with an option prefix or contain control characters. Desktop application IDs are checked for option/path/control-character abuse and only launch after selection.

QML invokes `/usr/bin/python3 -I` and `/usr/bin/timeout`. The broker invokes absolute `/usr/bin` executables with PATH fixed to `/usr/bin` and shell/Python startup hooks removed from the child environment. Some installed Omarchy commands internally use shells or request privileges; those remain trusted system programs and are only selected through the fixed policy. Terminal-wrapper command arguments are fixed, quoted strings from the policy, not shared menu text. This is not a sandbox for system commands or installed desktop applications.

Only read-only, typed availability operations run automatically. Unsupported checks return false. Query failures do not run a fallback shell expression. The broker and policy are part of the plugin's trusted code; another process able to modify the plugin itself is outside this boundary.

## Compatibility limits

These compound actions are currently hidden pending explicit typed implementations:

- Color picker (`trigger.capture.color`)
- Theme, background, and unlock selectors (`style.theme`, `style.background`, `style.unlock`)
- Night-light and XCompose config/edit-and-restart flows (`setup.config.hyprsunset`, `setup.config.xcompose`)
- Ollama hardware-dependent installer (`install.ai.ollama`)

Unsupported guards also hide touchpad haptics, Wi-Fi QR, plugin removal, Btrfs reset, Chromium account setup, Phoenix installation, and webapp/TUI removal entries. Use the stock Omarchy menu for these. Missing checked-state support only omits the checkmark.

Future command/guard changes require an explicit reviewed policy update. Do not resolve incompatibilities by restoring evaluation of menu strings. Tests cover malicious executable-field overrides and typed dispatch; real applications are not launched during tests.

## Filesystem and resource limits (1.1.1)

No menu or desktop-entry path/URL is returned directly to Qt. The broker enumerates only configured icon/pixmap roots, rejects symlinked root components, opens descendants relative to directory descriptors with O_NOFOLLOW, and accepts only regular PNG files. Approved roots must match their realpath; descriptor-relative traversal prevents symlink replacement races. Files are read through the validated descriptor and sent as data:image/png snapshots, so later path changes cannot redirect image loading. SVG/XPM and arbitrary file/image/qrc URLs are not loaded. Missing images use the placeholder.

Each scan accepts at most 512 requested names, visits at most 65,536 entries with depth 16 and an eight-second traversal deadline, reads at most 128 KiB per image, and accepts PNG dimensions up to 512x512. Total emitted JSON is capped at 2 MiB and 512 records. Overflow exits the producer immediately. QML independently caps records/bytes and kills the direct scan process on overflow; Quickshell reaps it on exit. The scan has no subprocess descendants.

Guard/provider helpers read stdout and stderr incrementally with a combined 64 KiB budget and an eight-second timeout. Cleanup kills their process group, waits for the direct child, and reaps adopted descendants using Linux subreaper semantics. SIGTERM from the outer query deadline also enters this cleanup. No helper capture_output buffering remains.

The unsupported-menu notice was removed from the UI. Unsupported commands remain blocked.
