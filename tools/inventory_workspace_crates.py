#!/usr/bin/env python3
"""Map Gecko target Cargo fingerprints to tracked workspace manifests.

The result is a target-build superset, not a final-link inventory. A package
without a declared license requires review of its source and notices.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'

def inventory(repo,fingerprints):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True)
    if git('rev-parse','HEAD').strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    if git('status','--porcelain'):raise ValueError('Firefox checkout has uncommitted changes')
    names={re.sub(r'-[0-9a-f]{16}$','',p.name) for p in fingerprints.iterdir() if p.is_dir() and list(p.glob('lib-*.json'))}
    if not 100<=len(names)<=5000:raise ValueError('Expected target Cargo fingerprints')
    packages={}
    for path in git('ls-files','*Cargo.toml').splitlines():
        try:pkg=tomllib.loads((repo/path).read_text(encoding='utf-8')).get('package',{})
        except (ValueError,OSError,UnicodeError):continue
        name=pkg.get('name')
        if not isinstance(name,str) or name not in names:continue
        packages.setdefault(name,[]).append({'manifest':path,'version':pkg.get('version'),'license':pkg.get('license')})
    unmatched=sorted(names-packages.keys())
    return {'version':'codi-gecko-workspace-crates/1','firefoxCommit':COMMIT,
            'scope':'target build fingerprints; not final linked crates',
            'fingerprintNames':len(names),'matchedNames':len(packages),'unmatched':unmatched,
            'packages':{name:packages[name] for name in sorted(packages)}}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firefox',type=Path,required=True);p.add_argument('--fingerprints',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    result=inventory(a.firefox,a.fingerprints);a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print('Matched',result['matchedNames'],'of',result['fingerprintNames'],'target names')
