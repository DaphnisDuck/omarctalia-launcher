#!/usr/bin/python3
"""Install only runtime files, preserving vi settings and a restorable snapshot."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
FILES = ['MenuModel.js','MenuDescriptions.js','IconResolver.qml','command-broker.py','CommandPolicy.json','CommandPolicy.js',
         'MenuCatalog.qml','Launcher.qml','manifest.json','LICENSE','LICENSE-OMARCHY','UPSTREAM.md']

def digest(data): return hashlib.sha256(data).hexdigest()

def check():
    missing=[name for name in ['quickshell','python3','timeout','uwsm-app','gtk-launch','notify-send'] if not os.access('/usr/bin/'+name, os.X_OK)]
    if missing: raise RuntimeError('Missing commands: '+', '.join(missing))
    commons=Path('/usr/share/omarchy/shell/Commons')
    for name in ['qmldir','Color.qml','Util.qml']:
        if not (commons/name).is_file(): raise RuntimeError('Missing Omarchy theme interface: '+name)
    color=(commons/'Color.qml').read_text()
    for name in ['selectedBackground','selectedText','selectedBorder','scrim']:
        if name not in color: raise RuntimeError('Unsupported Omarchy menu color interface: '+name)
    for name in FILES:
        if not (ROOT/name).is_file(): raise RuntimeError('Incomplete release: '+name)
    manifest=json.loads((ROOT/'manifest.json').read_text())
    if manifest.get('id') != 'omarctalia.launcher': raise RuntimeError('Incorrect plugin ID')
    return manifest['version']

def replace_file(target, data):
    # A complete file is published by one rename; no truncated QML can be loaded.
    fd, temporary=tempfile.mkstemp(prefix='.omarctalia-',suffix='.pending',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.chmod(temporary,0o644)
        os.replace(temporary,target)
    finally:
        Path(temporary).unlink(missing_ok=True)

def install(target, backups):
    version=check()
    payload={name:(ROOT/name).read_bytes() for name in FILES}
    current=target/'Launcher.qml'
    if current.is_file():
        match=re.search(rb'property bool viModeEnabled:\s*(true|false)',current.read_bytes())
        if match:
            payload['Launcher.qml']=re.sub(rb'(property bool viModeEnabled:\s*)(true|false)',lambda m:m[1]+match[1],payload['Launcher.qml'],count=1)
    target.mkdir(parents=True,exist_ok=True)
    backup=backups/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup.mkdir(parents=True)
    before={}
    for name in FILES:
        old=target/name
        if old.is_file():
            data=old.read_bytes(); (backup/name).write_bytes(data); before[name]=digest(data)
        else: before[name]=None
    record={'target':str(target),'before':before,'after':{name:digest(data) for name,data in payload.items()},'version':version}
    (backup/'snapshot.json').write_text(json.dumps(record,indent=2)+'\n')
    try:
        for name,data in payload.items():
            if not (target/name).is_file() or (target/name).read_bytes()!=data:
                replace_file(target/name,data)
        for name,data in payload.items():
            if (target/name).read_bytes()!=data: raise RuntimeError('Verification failed: '+name)
    except Exception:
        restore(backup,target,force=True)
        raise
    print(f'Installed Omarctalia Launcher {version}.')
    print(f'Backup: {backup}')
    return backup

def restore(backup,target,force=False):
    record=json.loads((backup/'snapshot.json').read_text())
    if Path(record['target']).resolve()!=target: raise RuntimeError('Backup belongs to another installation')
    if set(record['before'])!=set(FILES) or set(record['after'])!=set(FILES): raise RuntimeError('Invalid backup file list')
    # Validate all contents and conflicts before touching the installation.
    for name,checksum in record['before'].items():
        if checksum and digest((backup/name).read_bytes())!=checksum: raise RuntimeError('Damaged backup: '+name)
        current=target/name
        if not force and (not current.is_file() or digest(current.read_bytes())!=record['after'][name]):
            raise RuntimeError('Installed file changed since this backup: '+name+'; save your edits before using --force')
    for name,checksum in record['before'].items():
        if checksum: replace_file(target/name,(backup/name).read_bytes())
        else: (target/name).unlink(missing_ok=True)
    print('Restored the previous installation.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'.config/omarchy/plugins/omarctalia.launcher')
    parser.add_argument('--backup-root',type=Path,default=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'omarctalia-launcher/backups')
    parser.add_argument('--check',action='store_true',help='Check dependencies without writing files')
    parser.add_argument('--restore',type=Path,help='Restore a snapshot created by this installer')
    parser.add_argument('--force',action='store_true',help='Allow restore to replace edited files')
    args=parser.parse_args(); target=args.target.expanduser().resolve()
    if target==ROOT or target.is_relative_to('/usr') or target.is_relative_to('/etc'):
        parser.error('Choose a user plugin installation directory')
    if args.restore: restore(args.restore.expanduser().resolve(),target,args.force)
    elif args.check: print('Dependencies ready for Omarctalia Launcher '+check())
    else: install(target,args.backup_root.expanduser().resolve())

if __name__=='__main__': main()
