#!/usr/bin/python3
import importlib.util
from pathlib import Path
import json
import os
import subprocess
import tempfile
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('broker',root/'command-broker.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
assert b.action('action','about')==['/usr/bin/omarchy-launch-about']
for mode,value in [('action','echo hacked'),('app','--help'),('app','../evil'),('fonts','$(touch /tmp/evil)')]:
 try:
  with patch.object(b,'provider',return_value=(['Safe Font'],'Safe Font')): b.action(mode,value)
 except (ValueError,KeyError): pass
 else: raise AssertionError((mode,value))
with patch.object(b,'provider',return_value=(["Font $(literal); name"],'')):
 assert b.action('fonts','Font $(literal); name')==['/usr/bin/omarchy-font-set','Font $(literal); name']
assert b.action('app','org.example.App')==['/usr/bin/uwsm-app','--','/usr/bin/gtk-launch','org.example.App.desktop']
assert b.ENV['PATH']=='/usr/bin'
for value in b.POLICY.values():
 if value['argv']: assert value['argv'][0].startswith('/usr/bin/')
assert not b.evaluate({'type':'unsupported'})
# Poison PATH and shell startup hooks; icon enumeration must not execute either.
with tempfile.TemporaryDirectory() as d:
 p=Path(d); marker=p/'executed'; poison=p/'bin';poison.mkdir();icons=p/'icons';icons.mkdir();(icons/'sample.png').touch()
 for name in ['python3','bash','find','timeout']:
  f=poison/name;f.write_text('#!/bin/sh\ntouch '+str(marker)+'\n');f.chmod(0o755)
 startup=p/'startup';startup.write_text('touch '+str(marker)+'\n')
 env=dict(os.environ,PATH=str(poison),BASH_ENV=str(startup),ENV=str(startup))
 result=subprocess.run(['/usr/bin/python3','-I',str(root/'command-broker.py'),'icons','nonexistent-test-icon'],env=env,capture_output=True,text=True)
 assert result.returncode in (0,1) and (not result.stderr or "budget exceeded" in result.stderr)
 assert not marker.exists()
print('PASS: typed dispatch, rejected commands, literal arguments, and poisoned PATH/startup hooks')
# Traversal ignores links and special files; no unvalidated source path reaches QML.
import struct
with tempfile.TemporaryDirectory() as d:
 p=Path(d); icons=p/'icons';icons.mkdir();outside=p/'outside';outside.mkdir()
 png=b'\x89PNG\r\n\x1a\n'+b'\0\0\0\rIHDR'+struct.pack('>II',16,16)+b'fixture'
 (icons/'safe.png').write_bytes(png);(outside/'escape.png').write_bytes(png)
 (icons/'link.png').symlink_to(outside/'escape.png');(icons/'dir').symlink_to(outside,target_is_directory=True)
 os.mkfifo(icons/'pipe.png')
 assert len(list(b.scan_icons(['safe','link','escape','pipe'],[str(icons)])))==1
 assert not list(b.scan_icons([str(outside/'escape.png')],[str(icons)]))
 assert not list(b.scan_icons(['escape'],[str(icons/'dir')]))
 for kw in [{'byte_limit':10},{'visit_limit':0},{'entry_limit':0}]:
  try: list(b.scan_icons(['safe'],[str(icons)],**kw))
  except ValueError: pass
  else: raise AssertionError('Missing icon budget')
 # Snapshot is already bytes; swapping the original for a symlink cannot redirect Qt.
 record=json.loads(next(b.scan_icons(['safe'],[str(icons)])))
 (icons/'safe.png').unlink();(icons/'safe.png').symlink_to(outside/'escape.png')
 assert record['source'].startswith('data:image/png;base64,')
 assert not list(b.scan_icons(['safe'],[str(icons)]))
# A noisy parent with a sleeping descendant must be killed and reaped.
with tempfile.TemporaryDirectory() as d:
 pidfile=Path(d)/'pids'
 program="import os,time; p=os.fork(); open("+repr(str(pidfile))+",'a').write(str(os.getpid())+'\\n'); time.sleep(.1); "+"\nif p: \n while True: os.write(1,b'x'*4096)\nelse: time.sleep(60)"
 try: b.run(['/usr/bin/python3','-c',program],byte_limit=1024,timeout=2)
 except ValueError: pass
 else: raise AssertionError('No output bound')
 for pid in pidfile.read_text().splitlines(): assert not Path('/proc/'+pid).exists(),pid
 try: b.run(['/usr/bin/python3','-c','import time; time.sleep(60)'],timeout=.05)
 except subprocess.TimeoutExpired: pass
 else: raise AssertionError('No timeout')
print('PASS: no symlinks/special files, icon budgets, immutable image bytes, bounded output and group reaping')
