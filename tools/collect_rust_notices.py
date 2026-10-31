#!/usr/bin/env python3
"""Collect a conservative set of vendored Rust notices for a Gecko build.

Target fingerprints identify crates built for the target, not necessarily the
exact code retained by the final link. Multiple vendored versions are included
when their package names match; build-only proc macros can also be included.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'

def collect(repo,fingerprints):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    if git('status','--porcelain','--','third_party/rust'):raise ValueError('Vendored Rust source has uncommitted changes')
    names={re.sub(r'-[0-9a-f]{16}$','',p.name) for p in fingerprints.iterdir() if p.is_dir() and list(p.glob('lib-*.json'))}
    if not 100<=len(names)<=5000:raise ValueError('Expected target Cargo fingerprints')
    out=['Target-built vendored Rust crate notices from Firefox '+COMMIT+'\n',
         'This is a conservative set inferred from Cargo fingerprints; it is not an exact final-link inventory.\n']
    found=set()
    for manifest in sorted((repo/'third_party/rust').glob('*/Cargo.toml')):
        try:package=tomllib.loads(manifest.read_text(encoding='utf-8')).get('package',{})
        except (ValueError,UnicodeError):continue
        name=package.get('name')
        if name not in names:continue
        found.add(name);license_name=package.get('license','not declared')
        out.append('\n===== '+str(name)+' '+str(package.get('version','unknown'))+'; declared license: '+str(license_name)+' =====\n')
        paths=sorted(p for p in manifest.parent.iterdir() if p.is_file() and not p.is_symlink() and p.name.lower().startswith(('license','copying','notice','copyright')))
        for path in paths:
            if path.stat().st_size>512*1024:raise ValueError('Unexpectedly large notice')
            out.append('\n--- '+path.relative_to(repo).as_posix()+' ---\n'+path.read_text(encoding='utf-8')+'\n')
        if not paths:out.append('No separate license file in this vendored package; see declared license and source.\n')
    out.append('\nUnmatched target fingerprint names (workspace, toolchain, or otherwise not matched to vendored manifests):\n'+json.dumps(sorted(names-found))+'\n')
    return ''.join(out).encode(),len(names),len(found)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firefox',type=Path,required=True);p.add_argument('--fingerprints',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    data,names,found=collect(a.firefox,a.fingerprints);a.output.write_bytes(data)
    print(json.dumps({'fingerprintNames':names,'matchedVendoredNames':found,'bytes':len(data)}))
