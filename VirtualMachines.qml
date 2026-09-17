import QtQuick
import Quickshell.Io

Item {
    id: root
    // Only local system/session connections are supported. Empty disables VM search.
    property string connectionUri: "qemu:///system"
    property var rows: []
    property double lastRefresh: 0
    readonly property string broker: decodeURIComponent(Qt.resolvedUrl("command-broker.py").toString().replace(/^file:\/\//, ""))
    signal changed()
    function refresh() {
        if (query.running || Date.now() - lastRefresh < 10000) return
        if (!connectionUri) { rows = []; changed(); return }
        query.output = ""
        query.overflow = false
        query.running = true
    }
    Process {
        id: query
        command: ["/usr/bin/timeout", "--kill-after=1s", "5s", "/usr/bin/python3", "-I", root.broker, "vm-list", root.connectionUri]
        property string output: ""
        property bool overflow: false
        stdout: SplitParser {
            onRead: function(data) {
                if (query.overflow) return
                if (query.output.length + data.length > 65536) {
                    query.overflow = true
                    query.signal(15)
                } else query.output += data
            }
        }
        onExited: function(code, status) {
            root.lastRefresh = Date.now()
            var next = []
            if (code === 0 && status === 0 && !overflow) {
                try {
                    var parsed = JSON.parse(output)
                    if (!Array.isArray(parsed) || parsed.length > 128) throw new Error("Invalid VM catalog")
                    for (var row of parsed) {
                        if (row.kind !== "vm" || typeof row.name !== "string" || row.name.length > 256 ||
                            !/^[0-9a-f-]{36}$/.test(row.uuid) || row.uri !== root.connectionUri) throw new Error("Invalid VM row")
                    }
                    next = parsed
                } catch (error) { }
            }
            root.rows = next
            root.changed()
        }
    }
}
