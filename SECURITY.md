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
