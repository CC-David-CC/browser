"""Journaled primitives for switching the optional Browser metadata audit.

The privileged caller must hold both the hosting and destination-policy locks,
verify file ownership and expected unit contents, and validate the policy and
systemd unit. These primitives never generate or delete keys or ledgers.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

def digest(value):return hashlib.sha256(value).hexdigest()
def encode(value):return base64.b64encode(value).decode('ascii')
def decode(value):return base64.b64decode(value,validate=True)
def remove_journal(path):
    path.unlink();fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def atomic(path,data,mode):
    path=Path(path)
    if path.is_symlink():raise ValueError('Refusing linked transition file')
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path);fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(name):os.unlink(name)

def recover(policy,unit,journal,*,restart,check):
    policy,unit,journal=map(Path,(policy,unit,journal))
    if journal.is_symlink() or not journal.is_file():raise ValueError('No valid transition journal')
    value=json.loads(journal.read_bytes())
    if set(value)!={'version','oldPolicy','newPolicy','oldUnit','newUnit','policyMode','unitMode'} or value['version']!='codi-browser-audit-switch/1':raise ValueError('Invalid transition journal')
    old_policy,new_policy,old_unit,new_unit=(decode(value[k]) for k in ('oldPolicy','newPolicy','oldUnit','newUnit'))
    for path,old,new in ((policy,old_policy,new_policy),(unit,old_unit,new_unit)):
        if path.is_symlink() or path.read_bytes() not in (old,new):raise ValueError('Transition input changed outside the operator')
    for mode in (value['policyMode'],value['unitMode']):
        if type(mode) is not int or mode&~0o777 or mode&0o022:raise ValueError('Unsafe saved mode')
    atomic(policy,old_policy,value['policyMode']);atomic(unit,old_unit,value['unitMode'])
    restart();check();remove_journal(journal)
    return {'status':'rolled-back'}

def switch(policy,unit,journal,*,expected_unit,candidate_unit,enabled,validate,restart,check):
    policy,unit,journal=map(Path,(policy,unit,journal))
    if type(enabled) is not bool or journal.exists() or journal.is_symlink():raise ValueError('Unexpected mode or pending transition')
    if policy.is_symlink() or unit.is_symlink():raise ValueError('Linked policy or unit refused')
    old_policy=policy.read_bytes();old_unit=unit.read_bytes()
    if old_unit!=expected_unit:raise ValueError('Service unit changed')
    value=json.loads(old_policy)
    if type(value.get('serverAuditEnabled')) is not bool or value['serverAuditEnabled']==enabled:raise ValueError('Policy already in requested mode or invalid')
    value['serverAuditEnabled']=enabled;new_policy=(json.dumps(value,indent=2)+'\n').encode()
    validate(new_policy,candidate_unit)
    policy_mode=stat.S_IMODE(policy.stat().st_mode);unit_mode=stat.S_IMODE(unit.stat().st_mode)
    if policy_mode&0o022 or unit_mode&0o022:raise ValueError('Unprotected transition inputs')
    record={'version':'codi-browser-audit-switch/1','oldPolicy':encode(old_policy),'newPolicy':encode(new_policy),'oldUnit':encode(old_unit),'newUnit':encode(candidate_unit),'policyMode':policy_mode,'unitMode':unit_mode}
    atomic(journal,(json.dumps(record,sort_keys=True)+'\n').encode(),0o600)
    try:
        atomic(policy,new_policy,policy_mode);atomic(unit,candidate_unit,unit_mode)
        restart();check();remove_journal(journal)
        return {'status':'enabled' if enabled else 'disabled','policySHA256':digest(new_policy),'unitSHA256':digest(candidate_unit)}
    except Exception:
        recover(policy,unit,journal,restart=restart,check=check)
        raise
