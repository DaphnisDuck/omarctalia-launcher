import QtQuick
import QtTest
import Quickshell
import "../" as Plugin
Item {
    Plugin.MenuCatalog { id: catalog; autoLoad: false; lookupTimeoutSeconds: 1 }
    Plugin.MenuCatalog { id: startup; autoLoad: false }
    TestCase {
        name: "CatalogRecovery"
        when: true
        function init() {
            catalog.acceptSource('{}', true)
            catalog.acceptSource('{"tools":{"provider":"fixture"},"about":{"label":"About","action":"true"}}', false)
            catalog.providers.fixture = {script: "printf 'First\\tfirst\\tfirst\\n'", actionFor: function(v) { return 'true' }}
        }
        function test_partial_and_invalid() {
            verify(catalog.acceptSource('{"about":{"description":"New description"}}', true))
            compare(catalog.item('about').action, 'true')
            compare(catalog.item('about').label, 'About')
            verify(!catalog.acceptSource('{"about":', true))
            compare(catalog.item('about').description, 'New description')
            verify(catalog.statusMessage.length > 0)
            verify(catalog.acceptSource('{}', true))
            compare(catalog.item('about').description, '')
            verify(!catalog.issues['user-menu'])
            verify(!catalog.acceptSource('{"orphan.child":{}}', false))
            compare(catalog.item('about').action, 'true')
        }
        function test_reverse_startup() {
            verify(startup.acceptSource('{"about":{"description":"Override"}}', true))
            verify(startup.acceptSource('{"about":{"label":"About","action":"true"}}', false))
            compare(startup.item('about').action, 'true')
            compare(startup.item('about').description, 'Override')
        }
        function test_provider_failure_retry_timeout() {
            catalog.loadProviderForMenu('tools')
            tryVerify(function() { return catalog.item('tools.first') !== null }, 4000)
            catalog.providers.fixture.script = "printf 'Partial\\tpartial\\tfirst\\n'; exit 7"
            catalog.providersLoaded = ({})
            catalog.loadProviderForMenu('tools')
            tryVerify(function() { return !!catalog.issues['provider:tools'] }, 4000)
            verify(catalog.item('tools.first') !== null)
            compare(catalog.item('tools.partial'), null)
            catalog.providers.fixture.script = "sleep 3; printf 'Late\\tlate\\tlate\\n'"
            catalog.loadProviderForMenu('tools')
            tryVerify(function() { return catalog.providersLoaded.tools === false }, 4000)
            verify(catalog.item('tools.first') !== null)
            compare(catalog.item('tools.late'), null)
            catalog.providers.fixture.script = "printf 'Second\\tsecond\\tsecond\\n'"
            catalog.loadProviderForMenu('tools')
            tryVerify(function() { return catalog.item('tools.second') !== null }, 4000)
            compare(catalog.item('tools.first'), null)
            verify(!catalog.issues['provider:tools'])
        }
        function test_guard_timeout_and_recovery() {
            catalog.acceptSource('{"about":{"action":"true","when":"true"}}', false)
            tryVerify(function() { return catalog.whenResults.about === true }, 4000)
            catalog.items.about.when = 'sleep 3; true'
            catalog.evaluateGuards()
            tryVerify(function() { return !!catalog.issues.guards }, 4000)
            compare(catalog.whenResults.about, true)
            catalog.items.about.when = 'false'
            catalog.evaluateGuards()
            tryVerify(function() { return catalog.whenResults.about === false }, 4000)
            verify(!catalog.issues.guards)
        }
        function cleanupTestCase() {
            console.log("OMARCTALIA_TEST_RESULT=" + JSON.stringify({failed: qtest_results.failCount, passed: qtest_results.passCount}))
            Qt.quit()
        }
    }
}
