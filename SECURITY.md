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

## Menu and installer boundaries (1.1.2)

FileView no longer loads menu files. A periodic timer requests an isolated broker read instead. The broker traverses directory components without following links and opens the final file with O_NOFOLLOW and O_NONBLOCK. Only regular, single-link files with the expected owner and no group/world write permission are accepted. Each read is capped at 128 KiB, including growth after fstat. The default menu must have the installed system tree's owner; the custom menu must have the current user's UID. A 1.5-second alarm and a two-second external deadline (one-second kill grace) bound filesystem stalls. QML only parses bounded broker records; rejected input keeps the working menu. Missing custom files mean empty overrides.

The optional installer uses lexical paths, never target resolve(). It retains no-follow directory descriptors for source, target and snapshots. All file reads, exclusive temporary creation, rename and unlink operations are relative to those descriptors. Existing reads are limited to 2 MiB and require regular, single-link, current-user-owned files without group/world write bits. Destination/snapshot directories must be owned by the user and not group/world writable. Published files and directories are fsynced. Restore validates the complete bounded snapshot into memory before mutation and, for new snapshots, verifies the recorded target directory identity. Automatic rollback uses the same retained destination descriptor.

A directory renamed after opening remains the same filesystem object; writes stay on that retained object rather than following a replacement pathname. This does not protect against an actor who can directly modify the plugin's own trusted code or the contents of the retained directories as the same user.

## Calculator (1.2.0)

Calculator.js parses only a fixed arithmetic grammar, capped at 256 characters, 128 tokens and 32 nested operations. It cannot access JavaScript objects, evaluate code, or invoke processes. Results must be finite. Clipboard writes occur only on selection, through Qt TextEdit.copy(), and contain only the formatted numeric result.

## Explicit menu source (1.2.1)

The trusted plugin setting customMenuPath can select an absolute real custom-menu file. It is passed as a separate broker argument, never as code, and cannot contain parent traversal. Owner/type/mode/link/size and deadline checks are unchanged. The default menu source is unchanged. The launcher does not discover or follow a symlink's target automatically.

## Virtual machines (1.3.0)

Automatic discovery uses a read-only libvirt connection in the broker, limited to qemu:///system or qemu:///session. QML enforces a five-second discovery deadline with one-second kill grace. Results are capped at 128 guests and 64 KiB; display names are length/control-character checked. Starting/resuming occurs only after selection, using a canonical UUID and a fresh domain-state check. Console launch uses fixed absolute virt-manager argv; names never become shell text. No sudo or remote connection is used. Tests mock all start/resume/console effects.

## Web URLs (1.4.0)

Only explicit HTTP/HTTPS URLs (or www. addresses normalized to HTTPS) produce a browser result. The UI and broker reject whitespace/control characters, backslashes, embedded credentials and oversized URLs. The broker independently checks scheme, host and port and passes the original normalized URL as one argument to /usr/bin/xdg-open. No shell evaluation is used. Navigation occurs only after selection; typing does not contact the website.
