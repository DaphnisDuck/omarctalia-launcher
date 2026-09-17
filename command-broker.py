#!/usr/bin/python3
"""Typed operations only. Shared menu text is never an executable program."""
import ctypes
import base64
import selectors
import signal
import stat
import struct
import time
import uuid
import json
import os
from pathlib import Path
import subprocess
import sys

POLICY = json.loads(Path(__file__).with_name('CommandPolicy.json').read_text())
# Child scripts also inherit only the system executable search path. Never read
# shell startup hooks supplied through the calling environment.
ENV = {k:v for k,v in os.environ.items() if k not in {'BASH_ENV','ENV','PYTHONPATH','PYTHONHOME','LD_PRELOAD','LD_LIBRARY_PATH','SHELLOPTS','BASHOPTS','CDPATH'} and not k.startswith('BASH_FUNC_')}
ENV['PATH'] = '/usr/bin'

# Adopt orphaned grandchildren so group cleanup can reap them as well.
if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
    raise OSError('Cannot establish child reaping boundary')

def terminate(signum, frame):
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, terminate)
MAX_OUTPUT = 65536

def run(argv, timeout=8, byte_limit=MAX_OUTPUT):
    """Bound stdout + stderr before decoding; kill the entire child group."""
    child = subprocess.Popen(argv, env=ENV, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    streams = selectors.DefaultSelector()
    streams.register(child.stdout, selectors.EVENT_READ)
    streams.register(child.stderr, selectors.EVENT_READ)
    output = {child.stdout: bytearray(), child.stderr: bytearray()}
    deadline = time.monotonic() + timeout
    total = 0
    try:
        while streams.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise subprocess.TimeoutExpired(argv, timeout)
            for key, _ in streams.select(min(remaining, 0.1)):
                chunk = os.read(key.fileobj.fileno(), min(4096, byte_limit - total + 1))
                if not chunk:
                    streams.unregister(key.fileobj)
                    continue
                total += len(chunk)
                if total > byte_limit: raise ValueError('Helper output limit exceeded')
                output[key.fileobj].extend(chunk)
        child.wait(timeout=max(0.001, deadline-time.monotonic()))
        return subprocess.CompletedProcess(argv, child.returncode,
            output[child.stdout].decode('utf-8', 'replace'), output[child.stderr].decode('utf-8', 'replace'))
    finally:
        # Also stop descendants left running after the parent exits.
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait()
        while True:
            try: os.waitpid(-child.pid, 0)
            except ChildProcessError: break
            except InterruptedError: continue
        streams.close()
        child.stdout.close()
        child.stderr.close()

# Icon bytes, not mutable filenames, cross into the QML image loader.
ICON_ENTRIES = 512
ICON_BYTES = 2 * 1024 * 1024
ICON_FILE_BYTES = 128 * 1024
ICON_VISITS = 65536

def icon_roots():
    home = str(Path.home())
    data = os.environ.get('XDG_DATA_HOME') or home + '/.local/share'
    roots = [home+'/.icons', data+'/icons', data+'/pixmaps']
    for folder in (os.environ.get('XDG_DATA_DIRS') or '/usr/local/share:/usr/share').split(':'):
        if folder.startswith('/'):
            roots.extend([folder+'/icons', folder+'/pixmaps'])
    return list(dict.fromkeys(roots))

def open_directory(path):
    # O_NOFOLLOW at every component prevents root and descendant symlink races.
    if not os.path.isabs(path) or '..' in Path(path).parts: raise ValueError('Invalid icon root')
    fd=os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in Path(path).parts[1:]:
            next_fd=os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd=next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise

def icon_data(fd, name):
    image_fd=os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        info=os.fstat(image_fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= ICON_FILE_BYTES: return None
        data=b''
        while len(data)<=ICON_FILE_BYTES:
            chunk=os.read(image_fd,min(8192,ICON_FILE_BYTES+1-len(data)))
            if not chunk: break
            data+=chunk
        if len(data)>ICON_FILE_BYTES: return None
        # PNG only: no SVG external references, XML entities or file URLs.
        if len(data)<24 or data[:8]!=b'\x89PNG\r\n\x1a\n' or data[12:16]!=b'IHDR': return None
        width,height=struct.unpack('>II',data[16:24])
        if not (0<width<=512 and 0<height<=512): return None
        return 'data:image/png;base64,'+base64.b64encode(data).decode('ascii')
    finally: os.close(image_fd)

def scan_icons(requested, roots=None, entry_limit=ICON_ENTRIES, byte_limit=ICON_BYTES, visit_limit=ICON_VISITS):
    if len(requested)>entry_limit: raise ValueError('Too many icon requests')
    wanted=set(requested)
    total=0; emitted=0; visits=0
    deadline=time.monotonic()+8
    def walk(fd, parent, depth=0):
        nonlocal total, emitted, visits
        if depth>16: return
        with os.scandir(fd) as entries:
            for entry in entries:
                visits+=1
                if visits>visit_limit or time.monotonic()>deadline: raise ValueError('Icon traversal budget exceeded')
                if entry.is_symlink(): continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in {"actions", "status", "places", "devices", "mimetypes", "emblems", "animations", "categories", "stock", "panel", "emotes", "cursors", "scalable", "symbolic"}: continue
                    try: child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                    except OSError: continue
                    try: yield from walk(child,parent+'/'+entry.name,depth+1)
                    finally: os.close(child)
                elif entry.name.lower().endswith('.png'):
                    path=parent+'/'+entry.name
                    name=entry.name[:-4]
                    matches=wanted.intersection((name,path))
                    if not matches: continue
                    try: data=icon_data(fd,entry.name)
                    except OSError: continue
                    if not data: continue
                    for key in sorted(matches):
                        record=json.dumps({'name':key,'source':data},ensure_ascii=True)
                        size=len(record.encode())+1
                        if emitted>=entry_limit or total+size>byte_limit: raise ValueError('Icon output budget exceeded')
                        total+=size; emitted+=1; wanted.remove(key)
                        yield record
                if not wanted: return
    for root in roots if roots is not None else icon_roots():
        if not wanted: break
        if not os.path.isabs(root) or os.path.realpath(root)!=os.path.normpath(root): continue
        try: fd=open_directory(root)
        except OSError: continue
        try: yield from walk(fd,os.path.normpath(root))
        finally: os.close(fd)


def expand(value):
    home = str(Path.home())
    if value.startswith('$HOME/'): return home + value[5:]
    if value.startswith('~/'): return home + value[1:]
    return value

def evaluate(spec):
    if spec is None: return True
    kind=spec['type']
    if kind=='unsupported': return False
    if kind=='not': return not evaluate(spec['child'])
    if kind=='pkg': return run(['/usr/bin/pacman','-Q',spec['value']]).returncode==0
    if kind=='cmd': return os.access('/usr/bin/'+spec['value'],os.X_OK)
    if kind=='path':
        p=Path(expand(spec['value']))
        result=p.is_dir() if spec['test']=='d' else p.is_file() if spec['test']=='f' else os.access(p,os.X_OK)
        return not result if spec.get('negate') else result
    result=run(spec['argv'])
    if kind=='equals': return result.returncode==0 and result.stdout.strip()==spec['value']
    return result.returncode==0

def provider(name):
    commands={'fonts':(['/usr/bin/omarchy-font-list'],['/usr/bin/omarchy-font-current']), 'power-profiles':(['/usr/bin/omarchy-powerprofiles-list'],['/usr/bin/powerprofilesctl','get'])}
    listing,current=commands[name]
    rows=run(listing); selected=run(current)
    if rows.returncode or selected.returncode: raise ValueError('Provider failed')
    return rows.stdout.splitlines(), selected.stdout.strip()

def action(mode, value):
    if mode=='action':
        argv=POLICY[value]['argv']
        if not argv: raise ValueError('Unsupported action')
        return [expand(a) for a in argv]
    if mode=='app':
        if not value or value.startswith('-') or '/' in value or any(ord(c)<32 for c in value): raise ValueError('Invalid desktop ID')
        return ['/usr/bin/uwsm-app','--','/usr/bin/gtk-launch',value+'.desktop']
    if mode in ('fonts','power-profiles'):
        rows,_=provider(mode)
        if value not in rows or value.startswith('-') or any(ord(c)<32 for c in value): raise ValueError('Invalid provider choice')
        return ['/usr/bin/omarchy-font-set',value] if mode=='fonts' else ['/usr/bin/omarchy-powerprofiles-set','autodetect',value]
    raise ValueError('Unknown operation')

MENU_BYTES = 128 * 1024

def read_menu(path, owner, limit=MENU_BYTES):
    path=Path(path)
    parent=open_directory(str(path.parent))
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=owner or info.st_mode & 0o022 or info.st_nlink!=1 or info.st_size>limit:
                raise ValueError('Unsafe or oversized menu')
            data=bytearray()
            while True:
                chunk=os.read(fd,min(8192,limit+1-len(data)))
                if not chunk: break
                data.extend(chunk)
                if len(data)>limit: raise ValueError('Menu grew beyond limit')
            return data.decode('utf-8')
        finally: os.close(fd)
    finally: os.close(parent)

def menu_deadline(signum, frame):
    raise TimeoutError('Menu read deadline exceeded')

def menu_sources(custom_path=None):
    if custom_path is not None and (not os.path.isabs(custom_path) or ".." in Path(custom_path).parts):
        raise ValueError("Custom menu path must be absolute without parent traversal")
    # A separate hard outer timeout also bounds blocked filesystem operations.
    signal.signal(signal.SIGALRM,menu_deadline)
    signal.setitimer(signal.ITIMER_REAL,1.5)
    try:
        sources=[(False,Path('/usr/share/omarchy/default/omarchy/omarchy-menu.jsonc'),os.stat('/usr/share/omarchy',follow_symlinks=False).st_uid),
                 (True,Path(custom_path) if custom_path is not None else Path.home()/'.config/omarchy/extensions/omarchy-menu.jsonc',os.getuid())]
        for user,path,owner in sources:
            try: result={'user':user,'status':'ok','text':read_menu(path,owner)}
            except FileNotFoundError: result={'user':user,'status':'missing'}
            except (OSError,ValueError): result={'user':user,'status':'error'}
            print(json.dumps(result,ensure_ascii=True),flush=True)
    finally: signal.setitimer(signal.ITIMER_REAL,0)

VM_URIS = ('qemu:///system', 'qemu:///session')

def vm_connection(uri, readonly):
    if uri not in VM_URIS: raise ValueError('Unsupported VM connection')
    import libvirt
    connection=libvirt.openReadOnly(uri) if readonly else libvirt.open(uri)
    if connection is None: raise ValueError('VM connection unavailable')
    return connection

def vm_rows(uri):
    if not os.access("/usr/bin/virt-manager",os.X_OK): return []
    connection=vm_connection(uri, True)
    try:
        rows=[]
        states={0:'Unknown',1:'Running',2:'Busy',3:'Paused',4:'Shutting down',5:'Stopped',6:'Crashed',7:'Suspended'}
        domains=connection.listAllDomains(0)
        if len(domains)>128: raise ValueError('Too many virtual machines')
        for domain in domains:
            name=domain.name()
            if not name or len(name)>256 or any(ord(c)<32 for c in name): continue
            identifier=str(uuid.UUID(domain.UUIDString()))
            state=domain.state()[0]
            rows.append({'id':'vm:'+uri+':'+identifier,'kind':'vm','name':name,
                         'uuid':identifier,'uri':uri,'state':states.get(state,'Unknown')})
        return sorted(rows,key=lambda row:row['name'].casefold())
    finally: connection.close()

def vm_open(uri, identifier):
    if not os.access("/usr/bin/virt-manager",os.X_OK): raise ValueError("virt-manager is not installed")
    # Only canonical UUIDs are passed to lookup and virt-manager, never names or commands.
    if str(uuid.UUID(identifier))!=identifier: raise ValueError('Invalid VM identifier')
    connection=vm_connection(uri,False)
    try:
        domain=connection.lookupByUUIDString(identifier)
        state=domain.state()[0]
        if state==5: domain.create()
        elif state==3: domain.resume()
        elif state not in (1,2): raise ValueError('VM is not ready to open')
    finally: connection.close()
    subprocess.Popen(['/usr/bin/virt-manager','--connect',uri,'--show-domain-console',identifier],
                     env=ENV,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)

def main():
    mode=sys.argv[1]
    if mode=='vm-list':
        rows=vm_rows(sys.argv[2])
        output=json.dumps(rows,ensure_ascii=True)
        if len(output)>65536: raise ValueError('VM catalog too large')
        print(output)
        return 0
    if mode=='vm-open':
        try: vm_open(sys.argv[2],sys.argv[3])
        except Exception:
            run(['/usr/bin/notify-send','-a','Omarctalia Launcher','--','Could not open virtual machine','Check its state and connection in virt-manager.'])
            raise
        return 0
    if mode=='menus':
        menu_sources(sys.argv[2] if len(sys.argv) == 3 else None)
        return 0
    if mode=='icons':
        for record in scan_icons(sys.argv[2:]): print(record,flush=True)
        return 0
    if mode=='guards':
        for key,spec in POLICY.items():
            for tag,field in [('w','when'),('c','checked')]:
                if spec[field] is not None:
                    try: answer = evaluate(spec[field])
                    except (OSError, ValueError, subprocess.TimeoutExpired): answer = False
                    print(f'{key}:{tag}:{int(answer)}')
        return 0
    if mode=='provider':
        rows,current=provider(sys.argv[2])
        for value in rows:
            if value and not any(ord(c)<32 for c in value): print(f'{value}\t{value}\t{current}')
        return 0
    argv=action(mode,sys.argv[2])
    result=subprocess.run(argv,env=ENV,check=False).returncode
    if result not in (0,130,143,-2,-15):
        run(['/usr/bin/notify-send','-a','Omarctalia Launcher','--','Action did not complete','See the application output for details.'])
    return result

if __name__=='__main__':
    try: sys.exit(main())
    except (KeyError,ValueError,OSError,subprocess.TimeoutExpired) as error:
        print('Omarctalia operation refused or failed: '+str(error),file=sys.stderr)
        sys.exit(1)
