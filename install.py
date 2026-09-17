#!/usr/bin/python3
"""Install runtime files using retained, no-follow directory descriptors."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

ROOT = Path(os.path.abspath(__file__)).parent
MAX_FILE = 2 * 1024 * 1024
FILES = ['MenuModel.js','MenuDescriptions.js','Calculator.js','IconResolver.qml','command-broker.py','CommandPolicy.json','CommandPolicy.js',
         'MenuCatalog.qml','Launcher.qml','manifest.json','LICENSE','LICENSE-OMARCHY','UPSTREAM.md']

def digest(data): return hashlib.sha256(data).hexdigest()

def lexical(path):
    path=os.fspath(path)
    if '..' in Path(path).parts: raise ValueError('Parent traversal is not allowed')
    return Path(os.path.abspath(os.path.expanduser(path)))

@contextmanager
def directory(path, create=False, owned=True):
    path=lexical(path)
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            if create:
                try: os.mkdir(part,0o700,dir_fd=fd); os.fsync(fd)
                except FileExistsError: pass
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd); fd=child
        info=os.fstat(fd)
        if owned and (info.st_uid!=os.getuid() or info.st_mode & 0o022):
            raise ValueError('Directory must be owned by you and not group/world writable')
        yield fd
    finally: os.close(fd)

def read_file(fd,name,missing=False):
    if '/' in name or name in ('.','..'): raise ValueError('Invalid filename')
    try: file=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    except FileNotFoundError:
        if missing: return None
        raise
    try:
        info=os.fstat(file)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_nlink!=1 or info.st_mode & 0o022 or info.st_size>MAX_FILE:
            raise ValueError('Unsafe or oversized file: '+name)
        data=bytearray()
        while True:
            chunk=os.read(file,min(65536,MAX_FILE+1-len(data)))
            if not chunk: break
            data.extend(chunk)
            if len(data)>MAX_FILE: raise ValueError('File grew beyond limit: '+name)
        return bytes(data)
    finally: os.close(file)

def replace_file(fd,name,data):
    if name not in FILES and name!='snapshot.json': raise ValueError('Invalid output name')
    if len(data)>MAX_FILE: raise ValueError('Output too large')
    temporary='.omarctalia-'+secrets.token_hex(16)+'.pending'
    file=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    try:
        view=memoryview(data)
        while view:
            written=os.write(file,view)
            if not written: raise OSError('Short write')
            view=view[written:]
        os.fchmod(file,0o644); os.fsync(file)
        os.replace(temporary,name,src_dir_fd=fd,dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(file)
        try: os.unlink(temporary,dir_fd=fd)
        except FileNotFoundError: pass

def source():
    with directory(ROOT) as fd:
        return {name:read_file(fd,name) for name in FILES}

def check():
    for name in ['quickshell','python3','timeout','uwsm-app','gtk-launch','notify-send']:
        if not os.access('/usr/bin/'+name,os.X_OK): raise RuntimeError('Missing command: '+name)
    payload=source()
    manifest=json.loads(payload['manifest.json'])
    if manifest.get('id')!='omarctalia.launcher': raise RuntimeError('Incorrect plugin ID')
    return manifest['version']

def safe_target(target):
    target=lexical(target)
    if target==ROOT or target==Path('/') or target.is_relative_to('/usr') or target.is_relative_to('/etc'):
        raise ValueError('Choose a user plugin installation directory')
    return target

def write_previous(fd, previous):
    for name,data in previous.items():
        if data is None:
            try: os.unlink(name,dir_fd=fd)
            except FileNotFoundError: pass
            os.fsync(fd)
        else: replace_file(fd,name,data)

def install(target,backups):
    target=safe_target(target); backups=lexical(backups)
    version=check(); payload=source()
    with directory(target,create=True) as dest, directory(backups,create=True) as base:
        previous={name:read_file(dest,name,True) for name in FILES}
        current=previous['Launcher.qml']
        if current:
            match=re.search(rb'property bool viModeEnabled:\s*(true|false)',current)
            if match: payload['Launcher.qml']=re.sub(rb'(property bool viModeEnabled:\s*)(true|false)',lambda m:m[1]+match[1],payload['Launcher.qml'],count=1)
        catalog=previous['MenuCatalog.qml']
        if catalog:
            pattern=rb'(property string customMenuPath:\s*)("(?:[^"\\]|\\.)*")'
            setting=re.search(pattern,catalog)
            if setting:
                value=json.loads(setting[2])
                if not isinstance(value,str): raise ValueError('Invalid custom menu setting')
                payload['MenuCatalog.qml']=re.sub(pattern,lambda m:m[1]+json.dumps(value).encode(),payload['MenuCatalog.qml'],count=1)
        snapshot=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+secrets.token_hex(8)
        os.mkdir(snapshot,0o700,dir_fd=base); os.fsync(base)
        saved=os.open(snapshot,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=base)
        try:
            for name,data in previous.items():
                if data is not None: replace_file(saved,name,data)
            info=os.fstat(dest)
            record={'target':str(target),'targetIdentity':[info.st_dev,info.st_ino],
                'before':{name:digest(data) if data is not None else None for name,data in previous.items()},
                'after':{name:digest(data) for name,data in payload.items()},'version':version}
            replace_file(saved,'snapshot.json',json.dumps(record,indent=2).encode())
            try:
                for name,data in payload.items():
                    if previous[name]!=data: replace_file(dest,name,data)
                for name,data in payload.items():
                    if read_file(dest,name)!=data: raise RuntimeError('Verification failed: '+name)
            except Exception:
                write_previous(dest,previous)
                raise
        finally: os.close(saved)
    backup=backups/snapshot
    print(f'Installed Omarctalia Launcher {version}.')
    print(f'Backup: {backup}')
    return backup

def restore(backup,target,force=False):
    target=safe_target(target)
    with directory(target) as dest, directory(backup) as saved:
        record=json.loads(read_file(saved,'snapshot.json'))
        if record['target']!=str(target): raise RuntimeError('Backup belongs to another installation')
        info=os.fstat(dest)
        if 'targetIdentity' in record and record['targetIdentity']!=[info.st_dev,info.st_ino]: raise RuntimeError('Installation directory was replaced')
        if set(record['before'])!=set(FILES) or set(record['after'])!=set(FILES): raise RuntimeError('Invalid backup file list')
        previous={}
        for name,checksum in record['before'].items():
            data=read_file(saved,name) if checksum is not None else None
            if data is not None and digest(data)!=checksum: raise RuntimeError('Damaged backup: '+name)
            previous[name]=data
            current=read_file(dest,name,True)
            if not force and (current is None or digest(current)!=record['after'][name]): raise RuntimeError('Installed file changed since this backup: '+name)
        write_previous(dest,previous)
    print('Restored the previous installation.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=Path,default=Path.home()/'.config/omarchy/plugins/omarctalia.launcher')
    parser.add_argument('--backup-root',type=Path,default=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'omarctalia-launcher/backups')
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--restore',type=Path)
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    if args.restore: restore(args.restore,args.target,args.force)
    elif args.check: print('Dependencies ready for Omarctalia Launcher '+check())
    else: install(args.target,args.backup_root)

if __name__=='__main__': main()
