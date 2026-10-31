#!/usr/bin/env python3
"""Collect pinned upstream notices omitted from selected vendored Rust crates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request,urlopen

def collect(manifest):
    value=json.loads(Path(manifest).read_text())
    if value.get('version')!='codi-rust-upstream-notices/1':raise ValueError('Unexpected manifest')
    result=['Pinned upstream Rust license files. Cargo fingerprint inclusion is conservative, not proof of final linking.\n']
    for item in value['sources']:
        repo=item['repository'];rev=item['revision']
        if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo) or not re.fullmatch(r'[0-9a-f]{40}',rev):raise ValueError('Invalid repository or revision')
        for file in item['files']:
            path=file['path'];expected=file['sha256']
            if not re.fullmatch(r'[A-Za-z0-9_.\-/]+',path) or '..' in path.split('/') or not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('Invalid license path or digest')
            url=repo.replace('https://github.com/','https://raw.githubusercontent.com/',1)+'/'+rev+'/'+path
            with urlopen(Request(url,headers={'User-Agent':'CodiServer-license-review/1'}),timeout=30) as response:raw=response.read(524289)
            if len(raw)>524288 or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Upstream license changed: '+url)
            result.append('\n===== '+', '.join(item['packages'])+'; '+url+' =====\n'+raw.decode('utf-8').rstrip()+'\n')
    return ''.join(result).encode('utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    a.output.write_bytes(collect(a.manifest))
