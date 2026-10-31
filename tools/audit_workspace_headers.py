#!/usr/bin/env python3
"""Audit Rust source headers for target workspace manifests lacking a license."""
import argparse
import json
from pathlib import Path
import re
import subprocess

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'

def audit(repo,inventory):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True)
    if git('rev-parse','HEAD').strip()!=COMMIT or git('status','--porcelain'):raise ValueError('Expected clean pinned Firefox checkout')
    data=json.loads(inventory.read_text())
    if data.get('firefoxCommit')!=COMMIT or data.get('version')!='codi-gecko-workspace-crates/1':raise ValueError('Wrong workspace inventory')
    results=[]
    for name,entries in sorted(data['packages'].items()):
        for entry in entries:
            manifest=entry['manifest']
            if entry['license'] is not None or manifest.startswith('third_party/rust/'):continue
            parent=Path(manifest).parent.as_posix()
            if '..' in Path(parent).parts:raise ValueError('Invalid manifest path')
            paths=git('ls-files',parent+'/*.rs').splitlines()
            missing=[]
            for path in paths:
                header=(repo/path).read_text(encoding='utf-8',errors='replace')[:3000]
                if not re.search(r'Mozilla Public\s*\*?\s*License',header):missing.append(path)
            results.append({'name':name,'manifest':manifest,'rustFiles':len(paths),'withoutMozillaHeader':missing})
    return {'version':'codi-gecko-workspace-header-audit/1','firefoxCommit':COMMIT,
            'scope':'tracked Rust files under target workspace manifests with no declared license; metadata and non-Rust files excluded',
            'manifests':results}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firefox',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    result=audit(a.firefox,a.inventory);a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print('Audited',len(result['manifests']),'manifests;',sum(len(x['withoutMozillaHeader']) for x in result['manifests']),'files without Mozilla header')
