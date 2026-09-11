# Upstream code

MenuModel.js and MenuCatalog.qml derive from the installed Omarchy menu implementation (package 4.0.3-1). MenuModel.js is bundled rather than imported from a mutable system path. It has local fixes for JSONC parsing, partial overrides, validation, and quoted guard IDs.

Original MenuModel.js SHA-256: `ff6b265ca477d0d04297b0d9a5d9715960069db6da44603160d329e087e55fd8`.

Source: https://github.com/basecamp/omarchy/tree/master/shell/plugins/menu
License: MIT; see LICENSE-OMARCHY.
