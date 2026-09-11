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
            catalog.acceptSource('{"about":{"label":"About","action":"omarchy-launch-about"}}', false)

        }
        function test_partial_and_invalid() {
            verify(catalog.acceptSource('{"about":{"description":"New description"}}', true))
            compare(catalog.item('about').action, 'omarchy-launch-about')
            compare(catalog.item('about').label, 'About')
            verify(!catalog.acceptSource('{"about":', true))
            compare(catalog.item('about').description, 'New description')
            verify(catalog.statusMessage.length > 0)
            verify(catalog.acceptSource('{}', true))
            compare(catalog.item('about').description, '')
            verify(!catalog.issues['user-menu'])
            verify(!catalog.acceptSource('{"orphan.child":{}}', false))
            compare(catalog.item('about').action, 'omarchy-launch-about')
        }
        function test_reverse_startup() {
            verify(startup.acceptSource('{"about":{"description":"Override"}}', true))
            verify(startup.acceptSource('{"about":{"label":"About","action":"omarchy-launch-about"}}', false))
            compare(startup.item('about').action, 'omarchy-launch-about')
            compare(startup.item('about').description, 'Override')
        }
        function test_untrusted_executable_fields() {
            verify(catalog.isVisible(catalog.item('about')))
            for (var field of ['action', 'when', 'checked', 'provider']) {
                var patch = {about: {}}
                patch.about[field] = '/usr/bin/touch /tmp/omarctalia-injection'
                verify(catalog.acceptSource(JSON.stringify(patch), true))
                verify(catalog.item('about').policyBlocked)
                verify(!catalog.isVisible(catalog.item('about')))
                catalog.acceptSource('{}', true)
            }
            verify(catalog.acceptSource('{"custom":{"action":"echo injected"}}', true))
            verify(!catalog.isVisible(catalog.item('custom')))
        }
        function test_description_override_allowed() {
            catalog.acceptSource('{"about":{"description":"Personal description"}}', true)
            verify(catalog.isVisible(catalog.item('about')))
            compare(catalog.item('about').description, 'Personal description')
        }
        function cleanupTestCase() {
            console.log("OMARCTALIA_TEST_RESULT=" + JSON.stringify({failed: qtest_results.failCount, passed: qtest_results.passCount}))
            Qt.quit()
        }
    }
}
