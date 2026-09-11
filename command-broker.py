#!/usr/bin/python3
"""Typed operations only. Shared menu text is never an executable program."""
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

def run(argv, timeout=8):
    return subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=timeout, check=False)

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

def main():
    mode=sys.argv[1]
    if mode=='icons':
        for directory in sys.argv[2:]:
            if not os.path.isabs(directory) or not os.path.isdir(directory): continue
            seen=set()
            for parent,dirs,files in os.walk(directory,followlinks=True):
                real=os.path.realpath(parent)
                if real in seen:
                    dirs[:]=[]
                    ancestor=os.path.dirname(parent)
                    while ancestor.startswith(directory):
                        if os.path.realpath(ancestor)==real: raise ValueError('Icon directory cycle')
                        next_parent=os.path.dirname(ancestor)
                        if next_parent==ancestor: break
                        ancestor=next_parent
                    continue
                seen.add(real)
                for name in files:
                    if name.lower().endswith(('.png','.svg','.xpm')): print(os.path.join(parent,name))
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
