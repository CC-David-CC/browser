#!/usr/bin/env python3
"""Audit published registry packages against Firefox's locked checksums."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tomllib
from urllib.request import Request,urlopen

MAX_ARCHIVE=20*1024*1024
def audit(lock_path,manifest_path):
    raw=Path(lock_path).read_bytes();manifest=json.loads(Path(manifest_path).read_text())
    if manifest.get('version')!='codi-rust-missing-registry/1' or hashlib.sha256(raw).hexdigest()!=manifest['cargoLockSHA256']:raise ValueError('Unexpected Cargo lockfile or audit manifest')
    lock=tomllib.loads(raw.decode());packages={(p['name'],p['version']):p for p in lock['package'] if p.get('source','').startswith('registry+')}
    results=[]
    for item in manifest['packages']:
        name,version,checksum=item['name'],item['version'],item['checksum']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name) or not re.fullmatch(r'[0-9A-Za-z.+_-]+',version) or not re.fullmatch(r'[0-9a-f]{64}',checksum):raise ValueError('Invalid package identity')
        p=packages.get((name,version))
        if not p or p.get('checksum')!=checksum:raise ValueError('Package differs from Cargo.lock')
        url=f'https://static.crates.io/crates/{name}/{name}-{version}.crate'
        with urlopen(Request(url,headers={'User-Agent':'CodiServer-license-review/1'}),timeout=30) as response:data=response.read(MAX_ARCHIVE+1)
        if len(data)>MAX_ARCHIVE or hashlib.sha256(data).hexdigest()!=checksum:raise ValueError('Published crate checksum differs: '+name)
        prefix=f'{name}-{version}/';root=[];nested=[]
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            for member in archive:
                if not member.isfile() or not member.name.startswith(prefix):continue
                relative=member.name[len(prefix):];parts=relative.split('/')
                if parts[-1].lower().startswith(('license','licence','copying','notice','copyright')):
                    (root if len(parts)==1 else nested).append(relative)
        results.append({'name':name,'version':version,'rootLicenseFiles':sorted(root),'nestedLicenseFiles':sorted(nested)})
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cargo-lock',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args()
    print(json.dumps(audit(a.cargo_lock,a.manifest),indent=2))
