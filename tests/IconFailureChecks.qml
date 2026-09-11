import QtQuick
import QtTest
import Quickshell
import "../" as Plugin
Item {
    Plugin.IconResolver { id: resolver; files: ({kept: '/tmp/previous.png'}) }
    Component.onCompleted: resolver.refresh()
    TestCase {
        name: "IconFailureRecovery"
        when: resolver.statusMessage.length > 0
        function test_keeps_cache_and_backs_off() {
            compare(resolver.files.kept, '/tmp/previous.png')
            compare(resolver.lastRefresh, 0)
            var count=resolver.scanCount
            resolver.refresh()
            compare(resolver.scanCount, count)
            verify(resolver.dirty)
        }
        function cleanupTestCase() {
            console.log("OMARCTALIA_TEST_RESULT=" + JSON.stringify({failed:qtest_results.failCount,passed:qtest_results.passCount}))
            Qt.quit()
        }
    }
}
