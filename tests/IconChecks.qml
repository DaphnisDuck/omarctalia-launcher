import QtQuick
import QtTest
import Quickshell
import "../" as Plugin
Item {
    Plugin.IconResolver { id: resolver }
    Image { id: chromium; source: resolver.resolve('chromium', '', true); sourceSize.width: 36; sourceSize.height: 36 }
    Image { id: discord; source: resolver.resolve('omarchy-discord', '', true); sourceSize.width: 36; sourceSize.height: 36 }
    Component.onCompleted: resolver.refresh()
    TestCase {
        name: "IconCache"
        when: !resolver.scanning && resolver.lastRefresh > 0
        function test_decoding_and_cache() {
            tryCompare(chromium, 'status', Image.Ready)
            tryCompare(discord, 'status', Image.Ready)
            verify(String(chromium.source).indexOf('data:image/png;base64,') === 0)
            verify(String(discord.source).indexOf('data:image/png;base64,') === 0)
            compare(resolver.resolve('missing-omarctalia-test', '', true), '')
            compare(resolver.fileUrl('/tmp/a #b?.png'), 'file:///tmp/a%20%23b%3F.png')
            var count = resolver.scanCount
            resolver.refresh(); resolver.refresh()
            compare(resolver.scanCount, count)
            resolver.invalidate(); resolver.invalidate()
            tryCompare(resolver, 'scanCount', count + 1, 3000)
            tryCompare(resolver, 'scanning', false, 4000)
            compare(resolver.statusMessage, '')
        }
        function cleanupTestCase() {
            console.log("OMARCTALIA_TEST_RESULT=" + JSON.stringify({failed: qtest_results.failCount, passed: qtest_results.passCount}))
            Qt.quit()
        }
    }
}
