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
 result=subprocess.run(['/usr/bin/python3','-I',str(root/'command-broker.py'),'icons',str(icons)],env=env,capture_output=True,text=True)
 assert result.returncode==0 and 'sample.png' in result.stdout
 assert not marker.exists()
print('PASS: typed dispatch, rejected commands, literal arguments, and poisoned PATH/startup hooks')
