pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import Quickshell
import "MenuDescriptions.js" as MenuDescriptions
import "Calculator.js" as Calculator
import qs.Commons
import Quickshell.Wayland

Item {
    id: root

    property string omarchyPath: Quickshell.env("OMARCHY_PATH")
    property var shell: null
    property var manifest: null
    property var pluginRegistry: null

    // USER SETTING: set false for immediate typing and ordinary keyboard navigation.
    property bool viModeEnabled: true

    readonly property bool searchEditable: !viModeEnabled || insertMode
    readonly property color secondaryText: Util.alpha(Color.menu.text, 0.65)
    readonly property color inputBackground: Util.alpha(Color.menu.text, 0.05)
    readonly property color hoverBackground: Util.alpha(Color.menu.text, 0.08)
    onViModeEnabledChanged: {
        insertMode = false
        if (opened) searchField.forceActiveFocus()
    }

    property bool opened: false
    property bool insertMode: false

    function setInsertMode(enabled) {
        insertMode = enabled
        searchField.deselect()
        searchField.forceActiveFocus()
        if (enabled) searchField.cursorPosition = searchField.text.length
    }

    function handleKey(event) {
        if (!opened) return
        if (event.key === Qt.Key_Escape) {
            if (!event.isAutoRepeat) {
                if (viModeEnabled && insertMode) setInsertMode(false)
                else close()
            }
        } else if (event.key === Qt.Key_Up) {
            moveSelection(-1)
        } else if (event.key === Qt.Key_Down) {
            moveSelection(1)
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (!event.isAutoRepeat) launch(appList.currentIndex)
        } else if (event.key === Qt.Key_Left && (event.modifiers & Qt.AltModifier)) {
            goBack()
        } else if (searchEditable) {
            // Text editing, including h/j/k/l/q and Backspace, belongs to TextField.
            return
        } else {
            var plain = !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))
            if (plain && (event.text === "i" || event.text === "/")) {
                if (!event.isAutoRepeat) setInsertMode(true)
            } else if (plain && event.text === "j") {
                moveSelection(1)
            } else if (plain && event.text === "k") {
                moveSelection(-1)
            } else if (plain && (event.text === "h" || event.key === Qt.Key_Left || event.key === Qt.Key_Backspace)) {
                goBack()
            } else if (plain && (event.text === "l" || event.key === Qt.Key_Right)) {
                if (!event.isAutoRepeat) launch(appList.currentIndex)
            } else if (plain && event.text === "q") {
                close()
            }
            // Consume other keys in normal mode: typing and pasting require insert mode.
        }
        event.accepted = true
    }

    property var results: []
    readonly property var appLibrary: shell ? shell.appLibrary : null

    property string activeMenu: "root"
    property var history: []
    MenuCatalog {
        id: catalog
        appLibrary: root.appLibrary
        opened: root.opened
        activeMenu: root.activeMenu
        filterText: searchField.text
        onChanged: root.rebuild(false)
    }

    function rebuild(resetSelection) {
        if (catalog.rowsLoaded && activeMenu !== "root" && !catalog.item(activeMenu)) {
            activeMenu = "root"
            history = []
        }
        var previous = results[appList.currentIndex]
        var selectedId = previous ? previous.id : ""
        var query = searchField.text.toLowerCase().trim()
        var terms = query.split(/\s+/)
        var next = []
        for (var i = 0; i < catalog.itemOrder.length; i++) {
            var entry = catalog.item(catalog.itemOrder[i])
            if (!entry || entry.id === "root" || !catalog.isVisible(entry)) continue
            // Hidden ancestors must also hide their descendants in search.
            var parent = catalog.item(entry.parent)
            var visible = true
            for (var depth = 0; parent && parent.id !== "root" && depth < 32; depth++) {
                if (!catalog.isVisible(parent)) { visible = false; break }
                parent = catalog.item(parent.parent)
            }
            if (!visible) continue
            if (!query && entry.parent !== activeMenu) continue
            if (query && !catalog.isDescendantOf(entry.id, activeMenu)) continue
            var description = MenuDescriptions.describe(entry)
            var path = catalog.parentPathFor(entry.id)
            var haystack = [entry.label, description, entry.id, path,
                            (entry.aliases || []).join(" ")].join(" ").toLowerCase()
            if (query && !terms.every(function(term) { return haystack.indexOf(term) !== -1 })) continue
            next.push({id: entry.id, name: catalog.labelFor(entry), kind: entry.kind,
                       target: entry.target, appId: entry.appId || "", action: entry.action,
                       icon: entry.appIcon || "", glyph: entry.icon || "", iconFont: entry.iconFont || "",
                       comment: query ? [path, description].filter(function(v) { return v }).join(" · ") : description,
                       order: entry.order || 0})
        }
        next.sort(function(a, b) {
            if (query) {
                if ((a.kind === "app") !== (b.kind === "app")) return a.kind === "app" ? -1 : 1
                var aStarts = a.name.toLowerCase().indexOf(query) === 0
                var bStarts = b.name.toLowerCase().indexOf(query) === 0
                if (aStarts !== bStarts) return aStarts ? -1 : 1
            }
            if (a.kind === "app" && b.kind === "app") return a.name.localeCompare(b.name) || a.id.localeCompare(b.id)
            return a.order - b.order
        })
        var calculation = Calculator.calculate(searchField.text)
        if (calculation) next.unshift({id: "calculator-result", kind: calculation.error ? "calculator-error" : "calculator",
            name: calculation.error || calculation.value, value: calculation.value || "", glyph: "=",
            comment: calculation.error ? "Calculator · + − × / ^ % and parentheses" : "Calculator · Enter or click to copy"})
        results = next
        var index = resetSelection ? -1 : next.findIndex(function(entry) { return entry.id === selectedId })
        appList.currentIndex = next.length ? Math.max(0, index) : -1
        if (appList.currentIndex >= 0) appList.positionViewAtIndex(appList.currentIndex, ListView.Contain)
    }

    function enterMenu(id) {
        var entry = catalog.item(id)
        var visited = ({})
        while (entry && entry.kind === "link" && !visited[entry.id]) {
            visited[entry.id] = true
            entry = catalog.item(entry.target)
        }
        if (!entry || entry.kind !== "menu") return
        id = entry.id
        history = history.concat([{menu: activeMenu, query: searchField.text, selected: results[appList.currentIndex] ? results[appList.currentIndex].id : ""}])
        insertMode = false
        activeMenu = id
        searchField.text = ""
        catalog.invalidateVolatileProvider(id)
        catalog.loadProviderForMenu(id)
        rebuild(true)
        searchField.forceActiveFocus()
    }

    function goBack() {
        if (activeMenu === "root") return
        var previous = history.length ? history[history.length - 1] : {menu: "root", query: "", selected: ""}
        history = history.slice(0, -1)
        insertMode = false
        activeMenu = previous.menu
        searchField.text = previous.query
        rebuild(true)
        var index = results.findIndex(function(e) { return e.id === previous.selected })
        if (index >= 0) { appList.currentIndex = index; appList.positionViewAtIndex(index, ListView.Contain) }
        searchField.forceActiveFocus()
    }

    function moveSelection(delta) {
        if (!results.length) return
        appList.currentIndex = Math.max(0, Math.min(results.length - 1, appList.currentIndex + delta))
        appList.positionViewAtIndex(appList.currentIndex, ListView.Contain)
    }

    function launch(index) {
        if (!opened || index < 0 || index >= results.length) return
        var entry = results[index]
        if (entry.kind === "calculator-error") return
        if (entry.kind === "calculator") {
            calculatorClipboard.text = entry.value
            calculatorClipboard.selectAll()
            calculatorClipboard.copy()
            close()
            return
        }
        if (entry.kind === "menu" || entry.kind === "link") {
            enterMenu(entry.target || entry.id)
            return
        }
        var mode = entry.kind === "app" ? "app" : "action"
        var value = entry.kind === "app" ? entry.appId : entry.id
        if (entry.action && /^(fonts|power-profiles):/.test(entry.action)) {
            mode = entry.action.split(":")[0]
            value = entry.action.substring(mode.length + 1)
        }
        var broker = decodeURIComponent(Qt.resolvedUrl("command-broker.py").toString().replace(/^file:\/\//, ""))
        close()
        Quickshell.execDetached(["/usr/bin/python3", "-I", broker, mode, value])
    }

    TextEdit { id: calculatorClipboard; visible: false; textFormat: TextEdit.PlainText }

    IconResolver { id: iconResolver }

    function iconSource(entry, fileOnly) {
        if (entry.kind !== "app") return ""
        var preferred = !fileOnly && appLibrary ? appLibrary.iconSource(entry.icon) : ""
        return iconResolver.resolve(entry.icon, preferred, fileOnly)
    }

    function open(payloadJson) {
        insertMode = false
        history = []
        activeMenu = "root"
        searchField.text = ""
        iconResolver.refresh()
        catalog.prepare()
        rebuild(true)

        opened = true
        Qt.callLater(function() { if (root.opened) searchField.forceActiveFocus() })
    }

    function close() { opened = false }

    Connections {
        target: DesktopEntries.applications
        function onValuesChanged() { iconResolver.invalidate(); root.rebuild(false) }
    }
    Connections {
        target: root.appLibrary
        function onAppsChanged() { root.rebuild(false) }
    }

    PanelWindow {
        id: window

        visible: root.opened

        anchors {
            top: true
            bottom: true
            left: true
            right: true
        }

        color: "transparent"

        WlrLayershell.namespace: "omarctalia-launcher"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive

        exclusionMode: ExclusionMode.Ignore

        Rectangle {
            anchors.fill: parent
            color: Color.menu.scrim

            MouseArea {
                anchors.fill: parent
                onClicked: root.close()
            }
        }

        Rectangle {
            id: card

            width: Math.min(680, parent.width - 32)
            height: Math.min(560, parent.height - 32)

            anchors.centerIn: parent

            radius: 20
            color: Color.menu.background
            border.color: Color.menu.border
            border.width: 1

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    // Eat clicks so clicking the launcher itself
                    // doesn't close the window.
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 14

                Text {
                    text: "Omarctalia Launcher" + (root.viModeEnabled ? "  ·  " + (root.insertMode ? "INSERT" : "NORMAL") : "")
                    color: root.secondaryText
                    font.pixelSize: 12
                    font.bold: true
                }

                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        id: backButton
                        visible: root.activeMenu !== "root"
                        text: "‹ Back"
                        focusPolicy: Qt.NoFocus
                        onClicked: root.goBack()
                        contentItem: Text {
                            text: backButton.text
                            color: backButton.down || backButton.hovered ? Color.menu.selectedText : Color.menu.text
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            implicitWidth: 70
                            implicitHeight: 32
                            radius: 8
                            color: backButton.down || backButton.hovered ? Color.menu.selectedBackground : root.inputBackground
                            border.color: Color.menu.border
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: root.activeMenu === "root" ? "Home" : "Home › " + catalog.pathFor(root.activeMenu)
                        color: Color.menu.text
                        font.pixelSize: 14
                        elide: Text.ElideMiddle
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: text.length > 0
                    text: [catalog.statusMessage, iconResolver.statusMessage].filter(function(v) { return v }).join(" · ")
                    color: Color.menu.text
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                TextField {
                    id: searchField

                    Layout.fillWidth: true
                    Layout.preferredHeight: 52

                    readOnly: !root.searchEditable
                    cursorVisible: root.searchEditable && activeFocus
                    selectByMouse: root.searchEditable
                    placeholderText: !root.searchEditable ? "Press i to search" : root.activeMenu === "root" ? "Search apps and actions..." : "Search " + catalog.pathFor(root.activeMenu) + "..."

                    font.pixelSize: 18
                    color: Color.menu.text
                    placeholderTextColor: root.secondaryText
                    selectionColor: Color.menu.selectedBackground
                    selectedTextColor: Color.menu.selectedText

                    background: Rectangle {
                        radius: 14
                        color: root.inputBackground
                        border.width: 1
                        border.color: root.searchEditable ? Color.menu.selectedText : "transparent"
                    }

                    onTextChanged: {
                        root.rebuild(true)
                        if (text.trim()) catalog.loadProvidersForSearch()
                    }
                    Keys.priority: Keys.BeforeItem
                    Keys.onPressed: function(event) { root.handleKey(event) }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    radius: 14
                    color: "transparent"

                    ListView {
                        id: appList
                        anchors.fill: parent
                        anchors.margins: 6
                        clip: true
                        model: root.results
                        currentIndex: -1
                        spacing: 4
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {
                            id: scrollBar
                            policy: ScrollBar.AsNeeded
                            contentItem: Rectangle {
                                implicitWidth: 6
                                implicitHeight: 40
                                radius: 3
                                color: Color.menu.selectedText
                                opacity: scrollBar.active || scrollBar.hovered ? 0.8 : 0.35
                            }
                            background: Rectangle { color: "transparent" }
                        }

                        delegate: Rectangle {
                            id: row
                            required property var modelData
                            required property int index
                            width: appList.width
                            height: 64
                            radius: 10
                            color: appList.currentIndex === index ? Color.menu.selectedBackground : (rowMouse.containsMouse ? root.hoverBackground : "transparent")
                            border.color: appList.currentIndex === index ? Color.menu.selectedBorder : "transparent"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 12
                                Item {
                                    Layout.preferredWidth: 36
                                    Layout.preferredHeight: 36
                                    Image {
                                        id: appIcon
                                        anchors.fill: parent
                                        property bool fileFallback: false
                                        source: root.iconSource(row.modelData, fileFallback)
                                        onStatusChanged: {
                                            if (status === Image.Error && !fileFallback) fileFallback = true
                                        }
                                        sourceSize.width: 36
                                        sourceSize.height: 36
                                        fillMode: Image.PreserveAspectFit
                                        asynchronous: true
                                    }
                                    Text {
                                        anchors.centerIn: parent
                                        visible: appIcon.status !== Image.Ready
                                        text: row.modelData.glyph || String(row.modelData.name || "?").charAt(0).toUpperCase()
                                        font.family: row.modelData.iconFont || "monospace"
                                        color: Color.menu.selectedText
                                        font.pixelSize: 24
                                    }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    Text {
                                        Layout.fillWidth: true
                                        text: row.modelData.name || row.modelData.id
                                        color: appList.currentIndex === row.index ? Color.menu.selectedText : Color.menu.text
                                        font.pixelSize: 16
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: row.modelData.comment || "Run " + row.modelData.name
                                        color: appList.currentIndex === row.index ? Util.alpha(Color.menu.selectedText, 0.75) : root.secondaryText
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }
                                Text {
                                    visible: row.modelData.kind === "menu" || row.modelData.kind === "link"
                                    text: "›"
                                    color: Color.menu.selectedText
                                    font.pixelSize: 26
                                }
                            }
                            MouseArea {
                                id: rowMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                onClicked: root.launch(row.index)
                            }
                        }
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: root.results.length === 0
                        text: searchField.text.trim() ? "No matching apps or actions" : "No items available"
                        color: root.secondaryText
                        font.pixelSize: 16
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: !root.viModeEnabled ? "Type to search  ·  ↑↓ Select  ·  Enter Open  ·  Alt+← Back  ·  Esc Close" :
                          root.insertMode ? "INSERT  ·  Type to search  ·  ↑↓ Select  ·  Enter Open  ·  Esc Normal" :
                          "NORMAL  ·  j/k Select  ·  h Back  ·  l Open  ·  i Search  ·  q Close"
                    color: root.secondaryText
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }
        }
    }
}
