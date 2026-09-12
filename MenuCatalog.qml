// Data adapter for the installed Omarchy menu model. No windows or action execution.
import QtQuick
import Quickshell
import Quickshell.Io
import "MenuModel.js" as MenuModel
import "CommandPolicy.js" as Policy

Item {
  id: root
  property string omarchyPath: "/usr/share/omarchy"
  property var appLibrary: null
  property bool opened: false
  property string activeMenu: "root"
  property string filterText: ""
  readonly property bool dmenuActive: false
  property var defaultMenuItems: [{id: "apps", label: "Apps", provider: "apps"}]
  property bool defaultReady: false
  property bool userReady: false
  property var issues: ({})
  readonly property string statusMessage: Object.keys(issues).map(function(k) { return root.issues[k] }).join(" · ")
  property int lookupTimeoutSeconds: 12
  property bool autoLoad: true

  function setIssue(key, message) {
    if ((issues[key] || "") === message) return
    var next = Object.assign({}, issues)
    if (message) { next[key] = message; console.warn("Omarctalia Launcher:", message) }
    else delete next[key]
    issues = next
  }

  function acceptSource(raw, user) {
    var key = user ? "user-menu" : "default-menu"
    var previous = user ? userMenuItems : defaultMenuItems
    if (user) userReady = true
    else defaultReady = true
    try {
      var parsed = MenuModel.parseMenuJsonc(raw)
      if (!user && !parsed.length) throw new Error("Default menu is empty")
      if (user) userMenuItems = parsed
      else defaultMenuItems = parsed
      if (defaultReady && userReady) rebuildItemsFromSources()
      setIssue(key, "")
      return true
    } catch (error) {
      if (user) userMenuItems = previous
      else defaultMenuItems = previous
      console.warn("Omarctalia menu parse:", String(error))
      setIssue(key, "Could not load " + (user ? "custom" : "default") + " menu changes; keeping the working menu.")
      if (!rowsLoaded && defaultReady && userReady) {
        try { rebuildItemsFromSources() } catch (fallbackError) {
          userMenuItems = []
          rebuildItemsFromSources()
          setIssue("user-menu", "Custom menu could not be loaded; showing the default menu.")
        }
      }
      return false
    }
  }

  function sourceUnavailable(user, error) {
    if (user && error === FileViewError.FileNotFound) { acceptSource("{}", true); return }
    if (user) userReady = true
    else defaultReady = true
    setIssue(user ? "user-menu" : "default-menu", "Could not read " + (user ? "custom" : "default") + " menu; keeping the working menu.")
    if (!rowsLoaded && defaultReady && userReady) {
        try { rebuildItemsFromSources() } catch (fallbackError) {
          userMenuItems = []
          rebuildItemsFromSources()
          setIssue("user-menu", "Custom menu could not be loaded; showing the default menu.")
        }
      }
  }
  property var userMenuItems: []
  property var items: ({})
  property var itemOrder: []
  property bool rowsLoaded: false
  property int providerRevision: 0
  property var providersLoaded: ({})
  property var providerQueue: []
  property string defaultMenuPath: omarchyPath + "/default/omarchy/omarchy-menu.jsonc"
  property string userMenuPath: Quickshell.env("HOME") + "/.config/omarchy/extensions/omarchy-menu.jsonc"
  signal changed()
  function rebuildDisplay() { changed() }
  readonly property string broker: decodeURIComponent(Qt.resolvedUrl("command-broker.py").toString().replace(/^file:\/\//, ""))
  function prepare() {
    evaluateGuards()
    loadProviderForMenu("apps")
    loadProviderForMenu(activeMenu)
  }
  function item(id) {
    return root.items[id] || null
  }

  // ------------------------------------------------------------------
  // JSONC → normalized item array. Mirrors the bash bin's jq pipeline so
  // the on-disk authoring format stays untouched.
  // ------------------------------------------------------------------

  function stripJsonc(raw) {
    return MenuModel.stripJsonc(raw)
  }

  function normalizeAliases(value) {
    return MenuModel.normalizeAliases(value)
  }

  function normalizeItem(id, raw) {
    return MenuModel.normalizeItem(id, raw)
  }

  function parseMenuJsonc(raw) {
    return MenuModel.parseMenuJsonc(raw)
  }

  // Merge defaults + user extension. Later entries override earlier ones
  // on a per-key basis (so the user can tweak label/icon/action without
  // re-declaring the whole row).
  function rebuildItemsFromSources() {
    var mergedMenu = MenuModel.mergeMenuSources(root.defaultMenuItems, root.userMenuItems)
    root.whenResults = ({})
    root.checkedResults = ({})
    root.providerRevision += 1
    root.providersLoaded = ({})
    root.providerQueue = []
    var blocked = 0
    for (var id in mergedMenu.items) {
      var row = mergedMenu.items[id]
      var policy = Policy.entries[id]
      row.policyBlocked = Boolean((row.action || row.when || row.checked || row.provider) &&
          (!policy || row.action !== policy.actionText || row.when !== policy.whenText ||
           row.checked !== policy.checkedText || row.provider !== policy.provider ||
           (row.action && !policy.argv)))
      if (row.policyBlocked) blocked++
    }
    root.setIssue("policy", "")
    root.items = mergedMenu.items
    root.itemOrder = mergedMenu.itemOrder
    root.rowsLoaded = true
    if (root.opened) root.loadProviderForMenu("apps")
    root.evaluateGuards()
    if (root.opened) {
      root.rebuildDisplay()
      if (!root.dmenuActive) {
        if (root.filterText.trim()) root.loadProvidersForSearch()
        else root.loadProviderForMenu(root.activeMenu)
      }
    }
  }

  // Only these typed providers may enumerate dynamic rows.
  readonly property var providers: ({
    "fonts": {icon: "", volatile: true, actionFor: function(value) { return "fonts:" + value }},
    "power-profiles": {icon: "󱐋", actionFor: function(value) { return "power-profiles:" + value }}
  })

  function slugify(value) {
    return MenuModel.slugify(value)
  }

  // The apps provider is QML-native: rows come from the shared AppLibrary
  // (DesktopEntries) instead of a bash enumeration, so they carry image
  // icons, launch feedback, and uninstall support like the launcher.
  function mergeAppRows() {
    var rows = root.appLibrary && typeof root.appLibrary.sortedEntries === "function" ? root.appLibrary.sortedEntries("") :
      (DesktopEntries.applications.values || []).filter(function(e) { return !e.noDisplay }).map(function(e) { return {entry: e} })
    var appRows = []
    for (var j = 0; j < rows.length; j++) {
      var entry = rows[j].entry
      var appId = String(entry.id || "")
      if (!appId) continue
      var subtext = (entry.genericName || "")
      var aliases = subtext ? [subtext] : []
      try {
        if (entry.keywords && typeof entry.keywords.join === "function") aliases = aliases.concat(entry.keywords)
      } catch (e) { }
      appRows.push({
        id: "apps." + appId,
        parent: "apps",
        kind: "app",
        icon: "",
        appIcon: String(entry.icon || ""),
        appId: appId,
        label: (entry.name || entry.id),
        title: "",
        target: "",
        description: entry.comment || subtext,
        action: "",
        provider: "",
        aliases: aliases,
        when: "",
        checked: "",
        order: 0
      })
    }

    var merged = MenuModel.mergeAppRows(root.items, root.itemOrder, appRows)
    root.items = merged.items
    root.itemOrder = merged.itemOrder
    if (root.opened) root.rebuildDisplay()
  }

  function startProviderForMenu(id) {
    var entry = root.item(id)
    if (!entry || entry.policyBlocked || !entry.provider || root.providersLoaded[id]) return
    if (entry.provider === "apps") {
      root.providersLoaded[id] = true
      root.mergeAppRows()
      return
    }
    var spec = root.providers[entry.provider]
    if (!spec) {
      root.setIssue("provider:" + id, "This menu provider is not supported: " + entry.provider)
      return
    }

    root.providersLoaded[id] = true
    providerProc.menuId = id
    providerProc.providerKey = entry.provider
    providerProc.revision = root.providerRevision
    providerProc.collected = ""
    providerProc.overflow = false
    providerProc.command = ["/usr/bin/timeout", "--kill-after=2s", root.lookupTimeoutSeconds + "s", "/usr/bin/python3", "-I", root.broker, "provider", entry.provider]
    providerProc.running = true
  }

  function mergeProviderRows(rows, menuId, providerKey) {
    var spec = root.providers[providerKey]
    if (!spec) return
    var lines = String(rows || "").split("\n")
    var providerRows = []
    var takenIds = ({})
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i].trim()
      if (!line) continue
      var parts = line.split("\t")
      var label = parts[0] || ""
      var value = parts[1] || parts[0] || ""
      var current = parts[2] || ""
      if (!label) continue
      // Distinct values can slugify alike — Fira Code and Fira-Code both give
      // fira-code — and a repeated id is dropped, which would silently lose a
      // row from the list. Nudge it until it is the row's own.
      var rowId = menuId + "." + root.slugify(value)
      while (takenIds[rowId]) rowId += "-"
      takenIds[rowId] = true

      providerRows.push({
        id: rowId,
        parent: menuId,
        kind: "action",
        icon: (value === current) ? "✓" : (spec.icon || ""),
        label: label,
        title: "",
        target: "",
        description: "",
        action: spec.actionFor(value),
        provider: "",
        aliases: [],
        when: "",
        checked: "",
        order: 0
      })
    }
    var merged = MenuModel.swapProviderRows(root.items, root.itemOrder, menuId, providerRows)
    root.items = merged.items
    root.itemOrder = merged.itemOrder
    if (root.opened) root.rebuildDisplay()
  }

  function startNextProvider() {
    if (providerProc.running) return

    while (root.providerQueue.length > 0) {
      var id = root.providerQueue.shift()
      var entry = root.item(id)
      if (!entry || !entry.provider || root.providersLoaded[id]) continue

      root.startProviderForMenu(id)
      return
    }
  }

  // Entering a submenu is the one moment a volatile list is worth paying for
  // again: it may have been reshaped by the last pick from it. Search doesn't
  // invalidate, or every keystroke would restart the same enumeration.
  function invalidateVolatileProvider(id) {
    var entry = root.item(id)
    var spec = entry && entry.provider ? root.providers[entry.provider] : null
    if (spec && spec.volatile) root.providersLoaded[id] = false
  }

  function loadProviderForMenu(id) {
    var entry = root.item(id)
    if (!entry || entry.policyBlocked || !entry.provider || root.providersLoaded[id]) return

    // Native providers don't touch providerProc, so they never need to queue.
    if (entry.provider === "apps") {
      root.startProviderForMenu(id)
      return
    }

    if (providerProc.running) {
      if (root.providerQueue.indexOf(id) < 0) root.providerQueue = root.providerQueue.concat([id])
      return
    }

    root.startProviderForMenu(id)
  }

  function loadProvidersForSearch() {
    var active = root.item(root.activeMenu) ? root.activeMenu : "root"

    for (var i = 0; i < root.itemOrder.length; i++) {
      var entry = root.item(root.itemOrder[i])
      if (!entry || !entry.provider || root.providersLoaded[entry.id]) continue
      if (active !== "root" && entry.id !== active && !root.isDescendantOf(entry.id, active)) continue

      root.loadProviderForMenu(entry.id)
    }
  }

  function depthFor(id) {
    return MenuModel.depthFor(root.items, id)
  }

  function pathFor(id) {
    return MenuModel.pathFor(root.items, id)
  }

  function parentPathFor(id) {
    return MenuModel.parentPathFor(root.items, id)
  }

  function isDescendantOf(id, ancestorId) {
    return MenuModel.isDescendantOf(root.items, id, ancestorId)
  }

  function childCount(id) {
    return MenuModel.childCount(root.items, root.itemOrder, id)
  }

  // Guarded items are hidden when their `when:` evaluates false. Static
  // submenus are also hidden when none of their descendants are visible;
  // provider-backed menus stay visible because their rows load on demand.
  function isVisible(entry) {
    return !entry.policyBlocked && MenuModel.isVisible(root.items, root.itemOrder, root.whenResults, entry)
  }

  // Label with the ✓ marker baked in when `checked:` evaluated truthy.
  function labelFor(entry) {
    return MenuModel.labelFor(entry, root.checkedResults)
  }

  Process {
    id: providerProc
    property string menuId: ""
    property string providerKey: ""
    property string collected: ""
    property int revision: 0
    property bool overflow: false
    stdout: SplitParser {
      onRead: function(data) {
        if (providerProc.collected.length + data.length < 1048576) providerProc.collected += data + "\n"
        else providerProc.overflow = true
      }
    }
    onExited: function(exitCode, exitStatus) {
      if (providerProc.revision === root.providerRevision) {
        if (exitCode === 0 && exitStatus === 0 && !providerProc.overflow) {
          root.mergeProviderRows(providerProc.collected, providerProc.menuId, providerProc.providerKey)
          root.setIssue("provider:" + providerProc.menuId, "")
        } else {
          var next = Object.assign({}, root.providersLoaded)
          next[providerProc.menuId] = false
          root.providersLoaded = next
          root.setIssue("provider:" + providerProc.menuId, "Could not refresh menu choices; reopen this category to retry.")
        }
      }
      // Do not retry failures in a loop; the next user visit can request a retry.
      Qt.callLater(function() { root.startNextProvider() })
    }
  }

  Connections {
    target: DesktopEntries.applications
    function onValuesChanged() { if (root.providersLoaded["apps"]) root.mergeAppRows() }
  }
  Connections {
    target: root.appLibrary
    function onAppsChanged() {
      if (root.providersLoaded["apps"]) root.mergeAppRows()
    }
  }

  // The JSONC sources are watched so live edits to the default file (or the
  // user extension at ~/.config/omarchy/extensions/omarchy-menu.jsonc) take
  // effect without restarting the shell.
  FileView {
    id: defaultMenuFile
    path: root.autoLoad ? root.defaultMenuPath : ""
    watchChanges: true
    printErrors: false
    onLoaded: if (root.autoLoad) root.acceptSource(text(), false)
    onLoadFailed: function(error) { if (root.autoLoad) root.sourceUnavailable(false, error) }
    onFileChanged: reload()
  }

  FileView {
    id: userMenuFile
    path: root.autoLoad ? root.userMenuPath : ""
    watchChanges: true
    printErrors: false
    onLoaded: if (root.autoLoad) root.acceptSource(text(), true)
    onLoadFailed: function(error) { if (root.autoLoad) root.sourceUnavailable(true, error) }
    onFileChanged: reload()
  }

  // ---------------------------------------------------------------- guards
  //
  // The broker evaluates fixed typed checks from its bundled policy.
  // Shared menu expressions are never passed to this process.

  property var whenResults: ({})       // id → true|false (allow visibility)
  property var checkedResults: ({})    // id → true|false (show ✓)
  property bool guardsPending: false

  function evaluateGuards() {
    // Process ignores a command change while it is running, and `collected`
    // belongs to the run in flight, so a second evaluation cannot overwrite
    // the first: it would throw away the lines already read and never start.
    // The surviving tail then lands as the whole answer, and every id lost
    // with it goes back to showing, since a `when:` only hides on an explicit
    // false. Wait for the run in flight and evaluate once it lands instead.
    if (guardProc.running) {
      root.guardsPending = true
      return
    }
    root.guardsPending = false

    guardProc.collected = ""
    guardProc.revision = root.providerRevision
    guardProc.overflow = false
    guardProc.command = ["/usr/bin/timeout", "--kill-after=2s", root.lookupTimeoutSeconds + "s", "/usr/bin/python3", "-I", root.broker, "guards"]
    guardProc.running = true
  }

  Process {
    id: guardProc
    property string collected: ""
    property int revision: 0
    property bool overflow: false
    stdout: SplitParser {
      onRead: function(data) {
        if (guardProc.collected.length + data.length < 1048576) guardProc.collected += data + "\n"
        else guardProc.overflow = true
      }
    }
    onExited: function(exitCode, exitStatus) {
      // A batch that was killed rather than finished has only told us about
      // the rows it reached, and a row whose `when:` went unanswered shows.
      // Keep the last complete set rather than let a half-read one through.
      // A signal leaves the exit code at 0, so the status is what tells us.
      if (guardProc.revision !== root.providerRevision) {
        Qt.callLater(function() { root.evaluateGuards() })
        return
      }
      if (exitCode !== 0 || exitStatus !== 0 || guardProc.overflow) {
        root.setIssue("guards", "Some menu availability checks failed; reopen to retry.")
        if (root.guardsPending) Qt.callLater(function() { root.evaluateGuards() })
        return
      }

      var nextWhen = ({})
      var nextChecked = ({})
      var lines = guardProc.collected.split("\n")
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim()
        if (!line) continue
        var colon = line.lastIndexOf(":")
        if (colon < 0) continue
        var value = line.substring(colon + 1) === "1"
        var rest = line.substring(0, colon)
        var tagAt = rest.lastIndexOf(":")
        if (tagAt < 0) continue
        var id = rest.substring(0, tagAt)
        var tag = rest.substring(tagAt + 1)
        if (tag === "w") nextWhen[id] = value
        else if (tag === "c") nextChecked[id] = value
      }
      root.setIssue("guards", "")
      root.whenResults = nextWhen
      root.checkedResults = nextChecked
      if (root.opened) root.rebuildDisplay()
      // Run the evaluation that had to stand aside. Deferred by a turn so the
      // process is settled before its command is set again.
      if (root.guardsPending) Qt.callLater(function() { root.evaluateGuards() })
    }
  }
}
