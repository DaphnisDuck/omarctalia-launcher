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

import os
from unittest.mock import patch

def rejects(call):
    try: call()
    except (OSError, ValueError, RuntimeError): return
    raise AssertionError('Unsafe path was accepted')

with tempfile.TemporaryDirectory(prefix='omarctalia-installer-boundary-') as directory:
    root=Path(directory); outside=root/'outside'; outside.mkdir()
    (outside/'sentinel').write_text('untouched')
    target=root/'plugin'; target.symlink_to(outside,target_is_directory=True)
    rejects(lambda: installer.install(target,root/'backups'))
    target.unlink(); target.mkdir()
    backup_link=root/'backup-link'; backup_link.symlink_to(outside,target_is_directory=True)
    rejects(lambda: installer.install(target,backup_link))
    leaf=target/'Launcher.qml'; leaf.symlink_to(outside/'sentinel')
    rejects(lambda: installer.install(target,root/'backups'))
    leaf.unlink(); os.mkfifo(leaf)
    rejects(lambda: installer.install(target,root/'backups'))
    leaf.unlink()
    with leaf.open('wb') as file: file.truncate(installer.MAX_FILE+1)
    rejects(lambda: installer.install(target,root/'backups'))
    leaf.unlink()
    # Swap the pathname after the installer has retained its target descriptor.
    original_replace=installer.replace_file
    swapped=False
    def swap_then_write(fd,name,data):
        global swapped
        if not swapped and name=='MenuModel.js' and os.readlink('/proc/self/fd/'+str(fd))==str(target):
            swapped=True
            target.rename(root/'original-plugin')
            target.symlink_to(outside,target_is_directory=True)
        return original_replace(fd,name,data)
    with patch.object(installer,'replace_file',side_effect=swap_then_write):
        snapshot=installer.install(target,root/'backups')
    assert swapped and (root/'original-plugin/MenuModel.js').is_file()
    assert list(outside.iterdir())==[outside/'sentinel']
    rejects(lambda: installer.restore(snapshot,target,force=True))
    # Symlinked snapshot directories and backed-up files must be refused too.
    target.unlink(); (root/'original-plugin').rename(target)
    snapshot_link=root/'snapshot-link';snapshot_link.symlink_to(snapshot,target_is_directory=True)
    rejects(lambda: installer.restore(snapshot_link,target,force=True))
    snapshot2=installer.install(target,root/'backups')
    saved=snapshot2/'Launcher.qml';saved.unlink();saved.symlink_to(target/'Launcher.qml')
    rejects(lambda: installer.restore(snapshot2,target,force=True))
    assert (outside/'sentinel').read_text()=='untouched'
print('PASS: installer no-follow paths, bounded reads, target swaps, and hostile restore paths')
with tempfile.TemporaryDirectory(prefix='omarctalia-backup-swap-') as d:
    root=Path(d); target=root/'plugin'; target.mkdir(); (target/'Launcher.qml').write_text('old')
    outside=root/'outside';outside.mkdir(); base=root/'backups'
    original_replace=installer.replace_file
    swapped=False
    def swap_backup(fd,name,data):
        global swapped
        path=Path(os.readlink('/proc/self/fd/'+str(fd)))
        if not swapped and path.parent==base:
            swapped=True
            path.rename(root/'retained-backup')
            path.symlink_to(outside,target_is_directory=True)
        return original_replace(fd,name,data)
    with patch.object(installer,'replace_file',side_effect=swap_backup): installer.install(target,base)
    assert swapped and not list(outside.iterdir())
    assert (root/'retained-backup/Launcher.qml').read_text()=='old'
    assert (root/'retained-backup/snapshot.json').is_file()
print('PASS: backup path swaps cannot redirect descriptor-relative writes')
with tempfile.TemporaryDirectory(prefix='omarctalia-path-preference-') as d:
    root=Path(d); target=root/'plugin';target.mkdir()
    configured='/home/example/dotfiles/custom "menu".jsonc'
    import json
    (target/'MenuCatalog.qml').write_text('property string customMenuPath: '+json.dumps(configured)+'\n')
    installer.install(target,root/'backups')
    assert 'property string customMenuPath: '+json.dumps(configured) in (target/'MenuCatalog.qml').read_text()
print('PASS: explicit menu path preference survives upgrades')
