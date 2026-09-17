#!/usr/bin/env python3
"""Run pure-model, real QML/key-event, and detached-action tests safely offscreen."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ['Launcher.qml','MenuCatalog.qml','IconResolver.qml','MenuModel.js','VirtualMachines.qml','MenuDescriptions.js','Calculator.js','command-broker.py','CommandPolicy.json','CommandPolicy.js','manifest.json']

def qml_result(output):
    found = re.findall(r'OMARCTALIA_TEST_RESULT=(\{[^\n]+\})', output)
    if not found:
        raise AssertionError('QML did not finish its assertions:\n' + output)
    result = json.loads(found[-1])
    if result['failed'] or result['passed'] < 1:
        raise AssertionError('QML assertion failure: ' + str(result) + '\n' + output)
    return result

def execute_qml(path, env, expected_failure=False):
    run = subprocess.run(['quickshell','-p',str(path),'--no-color'],env=env,capture_output=True,text=True,timeout=25)
    output = run.stdout + run.stderr
    if run.returncode: raise AssertionError(output)
    if expected_failure:
        found = re.findall(r'OMARCTALIA_TEST_RESULT=(\{[^\n]+\})', output)
        assert found and json.loads(found[-1])['failed'] > 0, 'Runner self-test did not report its intentional failure: ' + output
        print('PASS: deliberately failing QML is rejected')
        return
    result = qml_result(output)
    print(f'PASS: {path.name} ({result["passed"]} assertions/test phases)')


def main():
    subprocess.run(['/usr/bin/python3',str(ROOT/'tests/security_test.py')],check=True)
    subprocess.run(['node',str(ROOT/'tests/model.test.cjs')],check=True)
    subprocess.run(['node',str(ROOT/'tests/calculator.test.cjs')],check=True)
    subprocess.run(['/usr/bin/python3',str(ROOT/'tests/vm_test.py')],check=True)
    subprocess.run(['python3',str(ROOT/'tests/installer_test.py')],check=True)
    with tempfile.TemporaryDirectory(prefix='omarctalia-test-') as folder:
        temp=Path(folder)
        for name in RUNTIME: shutil.copy2(ROOT/name,temp/name)
        (temp/'Commons').symlink_to('/usr/share/omarchy/shell/Commons',target_is_directory=True)
        (temp/'tests').mkdir()
        (temp/'runtime').mkdir(mode=0o700)
        env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QPA_PLATFORMTHEME='basic',XDG_RUNTIME_DIR=str(temp/'runtime'))
        # Verify that a QtTest assertion cannot silently exit with apparent success.
        (temp/'Sentinel.qml').write_text('''import QtQuick
import QtTest
Item { TestCase { name: "RunnerSentinel"; when: true
function test_expected_failure() { verify(false, "Intentional runner self-test") }
function cleanupTestCase() { console.log("OMARCTALIA_TEST_RESULT=" + JSON.stringify({failed:qtest_results.failCount,passed:qtest_results.passCount})); Qt.quit() }
} }''')
        execute_qml(temp/'Sentinel.qml',env,True)
        for name in ['CatalogChecks.qml','IconChecks.qml']:
            (temp/name).write_text((ROOT/'tests'/name).read_text().replace('import "../" as Plugin', 'import "." as Plugin'))
            execute_qml(temp/name,env)
        # A filesystem cycle causes a real find failure; the previous cache must survive.
        bad=temp/'bad-data/icons'; bad.mkdir(parents=True)
        for index in range(65546): (bad/str(index)).touch()
        name='IconFailureChecks.qml'
        (temp/name).write_text((ROOT/'tests'/name).read_text().replace('import "../" as Plugin', 'import "." as Plugin'))
        execute_qml(temp/name,dict(env,XDG_DATA_HOME=str(temp/'bad-data')))
        # Keep the production controls and handlers; replace only its Wayland surface
        # and external side effects. Test the real MenuCatalog separately above.
        vm=(temp/'VirtualMachines.qml').read_text().replace('    function refresh() {','    function refresh() { return // Fixtures supply the VM catalog.')
        (temp/'VirtualMachines.qml').write_text(vm)
        source=(ROOT/'Launcher.qml').read_text()
        source=source.replace('import QtQuick\n','import QtQuick\nimport QtTest\n',1)
        assert source.count('    PanelWindow {') == 1
        source=source.replace('    PanelWindow {','    Item {\n        width: 1000\n        height: 800',1)
        start=source.index('        anchors {')
        end=source.index('        Rectangle {',start)
        source=source[:start]+source[end:]
        source=source.replace('Quickshell.execDetached(', 'root.recordDispatch(')
        source=source.rstrip()[:-1]+(ROOT/'tests/UiChecks.qmlpart').read_text()
        (temp/'UiChecks.qml').write_text(source)
        catalog=(temp/'MenuCatalog.qml').read_text().replace('  function evaluateGuards() {','  function evaluateGuards() {\n    return // No desktop probes during keyboard tests.')
        catalog=catalog.replace('    providerProc.running = true','    // Provider rows are supplied by tests.')
        (temp/'MenuCatalog.qml').write_text(catalog)
        execute_qml(temp/'UiChecks.qml',env)
    print('ALL TESTS PASSED')

if __name__=='__main__': main()
