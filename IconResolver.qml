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
        if (name.charAt(0) === "/") return fileUrl(name)
        if (/^(file:|image:|qrc:)/.test(name)) return name
        if (!fileOnly) {
            // The boolean overload checks existence. The string fallback overload
            // generates a URL this installed image provider cannot resolve.
            var themed = name ? Quickshell.iconPath(name, true) : ""
            if (themed) return themed
            if (String(preferred || "").indexOf("file:") === 0) return preferred
        }
        var found = root.files[name]
        if (found) return fileUrl(found)
        if (!fileOnly && preferred && String(preferred).indexOf("?fallback=") < 0) return preferred
        // Leave unknown icons empty so the row's letter fallback remains visible.
        return ""
    }

    function addFile(path) {
        var name = path.slice(path.lastIndexOf("/") + 1).replace(/\.(svg|png|xpm)$/i, "")
        var size = path.match(/\/(\d+)x\d+\//)
        var score = /\.svg$/i.test(path) ? 0 : (size ? 10 + Math.abs(Number(size[1]) - 48) : 1000)
        // Equal-quality results keep the earlier XDG directory's icon.
        if (root.pendingScores[name] === undefined || score < root.pendingScores[name]) {
            root.pendingFiles[name] = path
            root.pendingScores[name] = score
        }
    }

    function refresh(force) {
        var now = Date.now()
        if (scan.running) { if (dirty || force) refreshPending = true; return }
        if (!force && now < retryAfter) return
        if (!force && !dirty && now - lastRefresh < cacheLifetimeMs) return
        var home = Quickshell.env("HOME")
        var dataHome = Quickshell.env("XDG_DATA_HOME") || home + "/.local/share"
        var dataDirs = (Quickshell.env("XDG_DATA_DIRS") || "/usr/local/share:/usr/share").split(":")
        var directories = [home + "/.icons", dataHome + "/icons", dataHome + "/pixmaps"]
        for (var i = 0; i < dataDirs.length; i++) {
            if (!dataDirs[i]) continue
            directories.push(dataDirs[i] + "/icons", dataDirs[i] + "/pixmaps")
        }
        pendingFiles = ({})
        pendingScores = ({})
        refreshPending = false
        dirty = false
        overflow = false
        scannedLines = 0
        scanCount++
        // Paths are separate arguments, never interpolated into the shell script.
        scan.command = ["timeout", "--kill-after=2s", root.scanTimeoutSeconds + "s", "bash", "-c",
            'status=0; for dir in "$@"; do [ -d "$dir" ] || continue; find -L "$dir" -type f \\( -iname "*.svg" -o -iname "*.png" -o -iname "*.xpm" \\) -print 2>/dev/null || status=1; done; exit "$status"',
            "omarctalia-icons"].concat(directories)
        scan.running = true
    }

    Process {
        id: scan
        stdout: SplitParser {
            onRead: function(line) {
                root.scannedLines++
                if (root.scannedLines < 200000 && line.length < 8192) root.addFile(line)
                else root.overflow = true
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
