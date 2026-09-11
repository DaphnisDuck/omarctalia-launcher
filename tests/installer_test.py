import importlib.util
from pathlib import Path
import tempfile
spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'install.py')
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
with tempfile.TemporaryDirectory(prefix='omarctalia-install-') as directory:
    root=Path(directory); target=root/'plugin'; target.mkdir()
    original=b'// local\nproperty bool viModeEnabled: false\n'
    (target/'Launcher.qml').write_bytes(original)
    (target/'personal-notes.txt').write_text('Preserve this')
    backup=installer.install(target,root/'backups')
    assert b'property bool viModeEnabled: false' in (target/'Launcher.qml').read_bytes()
    assert (target/'personal-notes.txt').read_text()=='Preserve this'
    installer.restore(backup,target)
    assert (target/'Launcher.qml').read_bytes()==original
    assert not (target/'MenuModel.js').exists()
    assert (target/'personal-notes.txt').read_text()=='Preserve this'
    backup=installer.install(target,root/'backups')
    (target/'Launcher.qml').write_text('New edits')
    try: installer.restore(backup,target)
    except RuntimeError: pass
    else: raise AssertionError('Restore overwrote new edits')
print('PASS: install, vi setting preservation, rollback, and edit-conflict protection')
