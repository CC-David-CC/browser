"""Optional signed relay metadata ledger. Never constructed when disabled.

Key custody, access control, retention and exporting checkpoints are operator
responsibilities; signatures do not independently certify wall-clock time or
who operated a device. No content, page path or request body is recorded.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from .policy import hostname, PolicyDenied

class AuditLedger:
    def __init__(self,path,signing_key):
        if not isinstance(signing_key,Ed25519PrivateKey):raise ValueError('Protected Ed25519 key required')
        self.key=signing_key;self.path=Path(path)
        if not self.path.is_absolute():raise ValueError('Absolute private ledger path required')
        parent=self.path.parent
        if not parent.is_dir() or parent.is_symlink() or parent.stat().st_uid!=os.geteuid() or stat.S_IMODE(parent.stat().st_mode)&0o077:raise ValueError('Ledger parent must be private and service-owned')
        fd=os.open(self.path,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('Private service-owned ledger required')
        finally:os.close(fd)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, record TEXT NOT NULL, prev TEXT NOT NULL, digest TEXT NOT NULL, signature BLOB NOT NULL)')

    def db(self):return sqlite3.connect(self.path,timeout=5)

    def append(self,value):
        allowed={'subject','source','destination','port','event','sentBytes','receivedBytes'}
        if not isinstance(value,dict) or not {'subject','source','destination','port','event'}<=value.keys() or not value.keys()<=allowed:raise ValueError('Destination metadata only')
        subject=value['subject'];kind=value['event'];port=value['port'];sent=value.get('sentBytes',0);received=value.get('receivedBytes',0)
        if not isinstance(subject,str) or not subject.startswith('user:') or len(subject)>100 or kind not in ('opened','denied','closed'):raise ValueError('Invalid subject or event')
        try:source=str(ipaddress.ip_address(value['source']))
        except ValueError as error:raise ValueError('Trusted source address required') from error
        try:domain=hostname(value['destination'])
        except PolicyDenied:domain='(invalid)'
        if type(port) is not int or not 0<=port<=65535 or any(type(n) is not int or not 0<=n<2**63 for n in (sent,received)):raise ValueError('Invalid traffic metadata')
        record=json.dumps({'at':int(time.time()),'subject':subject,'source':source,'domain':domain,'port':port,'event':kind,'sentBytes':sent,'receivedBytes':received},sort_keys=True,separators=(',',':'))
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');prior=db.execute('SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1').fetchone();seq=(prior[0]+1 if prior else 1);prev=prior[1] if prior else '0'*64
            digest=hashlib.sha256((str(seq)+'\n'+prev+'\n'+record).encode()).hexdigest();signature=self.key.sign(bytes.fromhex(digest))
            db.execute('INSERT INTO events(seq,record,prev,digest,signature) VALUES(?,?,?,?,?)',(seq,record,prev,digest,signature));db.commit()
        return {'seq':seq,'digest':digest,'signature':signature.hex()}

    def verify(self,expected_head=None):
        prev='0'*64;expected=1;public=self.key.public_key()
        with self.db() as db:
            for seq,record,prior,digest,signature in db.execute('SELECT seq,record,prev,digest,signature FROM events ORDER BY seq'):
                if seq!=expected or prior!=prev or hashlib.sha256((str(seq)+'\n'+prior+'\n'+record).encode()).hexdigest()!=digest:raise ValueError('Ledger chain changed')
                public.verify(signature,bytes.fromhex(digest));prev=digest;expected+=1
        if expected_head is not None and prev!=expected_head:raise ValueError('Ledger differs from the saved checkpoint')
        return {'records':expected-1,'head':prev}

    def domains(self,subject=None):
        if subject is not None and (not isinstance(subject,str) or not subject.startswith('user:')):raise ValueError('Invalid subject')
        sql="""SELECT json_extract(record,'$.domain'),
                 SUM(json_extract(record,'$.event')='opened'),
                 SUM(json_extract(record,'$.event')='denied'),
                 SUM(json_extract(record,'$.sentBytes')),
                 SUM(json_extract(record,'$.receivedBytes')),
                 MAX(json_extract(record,'$.at')) FROM events"""
        params=()
        if subject is not None:sql+=" WHERE json_extract(record,'$.subject')=?";params=(subject,)
        sql+=" GROUP BY json_extract(record,'$.domain') ORDER BY 2 DESC, 1"
        with self.db() as db:
            return [{'domain':row[0],'connections':row[1],'denied':row[2],
                     'sentBytes':row[3],'receivedBytes':row[4],'lastSeen':row[5]} for row in db.execute(sql,params)]
