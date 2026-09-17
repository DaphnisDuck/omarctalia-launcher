import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
spec=importlib.util.spec_from_file_location('broker',Path(__file__).resolve().parents[1]/'command-broker.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
id='12345678-1234-1234-1234-123456789abc'
for state,started,resumed in [(5,True,False),(1,False,False),(2,False,False),(3,False,True)]:
 domain=Mock();domain.state.return_value=(state,0)
 connection=Mock();connection.lookupByUUIDString.return_value=domain
 with patch.object(b,'vm_connection',return_value=connection) as connect,patch.object(b.subprocess,'Popen') as launch:
  b.vm_open('qemu:///system',id)
  connect.assert_called_once_with('qemu:///system',False)
  assert domain.create.called==started and domain.resume.called==resumed
  assert launch.call_args.args[0]==['/usr/bin/virt-manager','--connect','qemu:///system','--show-domain-console',id]
  connection.close.assert_called_once()
for state in [0,4,6,7]:
 domain=Mock();domain.state.return_value=(state,0)
 connection=Mock();connection.lookupByUUIDString.return_value=domain
 with patch.object(b,'vm_connection',return_value=connection),patch.object(b.subprocess,'Popen') as launch:
  try:b.vm_open('qemu:///system',id)
  except ValueError:pass
  else:raise AssertionError('Unsafe state accepted')
  launch.assert_not_called();domain.create.assert_not_called();connection.close.assert_called_once()
for bad in ['--help','$(touch /tmp/evil)','guest-name',id.upper()]:
 with patch.object(b,'vm_connection') as connect:
  try:b.vm_open('qemu:///system',bad)
  except ValueError:pass
  else:raise AssertionError('Bad VM identifier accepted')
  connect.assert_not_called()
try:b.vm_connection('qemu+ssh://untrusted/system',True)
except ValueError:pass
else:raise AssertionError('Remote URI accepted')
domain=Mock();domain.name.return_value='Guest with spaces';domain.UUIDString.return_value=id;domain.state.return_value=(5,0)
connection=Mock();connection.listAllDomains.return_value=[domain]
with patch.object(b,'vm_connection',return_value=connection) as connect:
 rows=b.vm_rows('qemu:///system');assert rows[0]['name']=='Guest with spaces' and rows[0]['state']=='Stopped'
 connect.assert_called_once_with('qemu:///system',True)
 domain.create.assert_not_called();connection.close.assert_called_once()
connection.listAllDomains.return_value=[domain]*129
with patch.object(b,'vm_connection',return_value=connection):
 try:b.vm_rows('qemu:///system')
 except ValueError:pass
 else:raise AssertionError('VM limit not enforced')
print('PASS: read-only VM discovery, UUID/URI validation, start/resume/running behavior, and console argv (mocked)')
