import QtQuick
import Quickshell
import Quickshell.Io

// Local file fallback for Qt icon-theme lookup failures. The index is shared
// by all rows and refreshed on summon / desktop-entry changes, not per icon.
Item {
    id: root
    property var files: ({})
    property var pendingFiles: ({})
    property var pendingScores: ({})
    property bool refreshPending: false
    readonly property bool scanning: scan.running
    property bool dirty: true
    property double lastRefresh: 0
    property double retryAfter: 0
    property int cacheLifetimeMs: 300000
    property int scanTimeoutSeconds: 10
    property int scanCount: 0
    property bool overflow: false
    property int scannedLines: 0
    property int scannedBytes: 0
    property string statusMessage: ""

    function invalidate() {
        dirty = true
        debounce.restart()
    }
    Timer {
        id: debounce
        interval: 500
        onTriggered: root.refresh()
    }

    function fileUrl(path) {
        return "file://" + String(path).split("/").map(encodeURIComponent).join("/")
    }

    function resolve(icon, preferred, fileOnly) {
        var name = String(icon || "")
        if (name.indexOf("file:") === 0) {
            try { name = decodeURIComponent(name.replace(/^file:\/\//, "")) } catch (e) { return "" }
        }
        // Only bounded PNG snapshots returned by the broker are image sources.
        var source = Object.prototype.hasOwnProperty.call(root.files, name) ? root.files[name] : ""
        return typeof source === "string" && source.startsWith("data:image/png;base64,") ? source : ""
    }

    function refresh(force) {
        var now = Date.now()
        if (scan.running) { if (dirty || force) refreshPending = true; return }
        if (!force && now < retryAfter) return
        if (!force && !dirty && now - lastRefresh < cacheLifetimeMs) return
        var requested = ["chromium", "omarchy-discord"]
        for (var app of (DesktopEntries.applications.values || [])) {
            var name = String(app.icon || "")
            if (name.indexOf("file://") === 0) {
                try { name = decodeURIComponent(name.substring(7)) } catch (e) { continue }
            }
            if (name && name.length <= 1024 && requested.indexOf(name) < 0 && requested.length < 512) requested.push(name)
        }
        pendingFiles = ({})
        pendingScores = ({})
        refreshPending = false
        dirty = false
        overflow = false
        scannedLines = 0
        scannedBytes = 0
        scanCount++
        // Paths are separate arguments, never interpolated into the shell script.
        var broker = decodeURIComponent(Qt.resolvedUrl("command-broker.py").toString().replace(/^file:\/\//, ""))
        scan.command = ["/usr/bin/timeout", "--kill-after=1s", "12s", "/usr/bin/python3", "-I", broker, "icons"].concat(requested)
        scan.running = true
    }

    Process {
        id: scan
        stdout: SplitParser {
            onRead: function(data) {
                if (root.overflow) return
                root.scannedLines++
                root.scannedBytes += data.length + 1
                if (root.scannedLines > 512 || root.scannedBytes > 2097152 || data.length > 180000) {
                    root.overflow = true
                    scan.signal(9)
                    return
                }
                try {
                    var row = JSON.parse(data)
                    if (typeof row.name !== "string" || row.name.length > 1024 ||
                        typeof row.source !== "string" || !row.source.startsWith("data:image/png;base64,")) throw new Error("Invalid icon record")
                    root.pendingFiles[row.name] = row.source
                } catch (e) { root.overflow = true; scan.signal(9) }
            }
        }
        onExited: function(exitCode, exitStatus) {
            if (exitCode === 0 && exitStatus === 0 && !root.overflow) {
                root.files = root.pendingFiles
                root.lastRefresh = Date.now()
                root.retryAfter = 0
                root.statusMessage = ""
            } else {
                root.dirty = true
                root.retryAfter = Date.now() + 30000
                root.statusMessage = "Icon refresh failed; keeping previously loaded icons."
                console.warn("Omarctalia Launcher:", root.statusMessage)
            }
            if (root.refreshPending) Qt.callLater(function() { root.refresh() })
        }
    }
}
