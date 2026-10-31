#!/usr/bin/env python3
"""Compare the Firefox-vendored void crate with its upstream release tag.

This establishes a source match, not that the package was linked or that a
later relicensing applies to the version used by Firefox.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tomllib

COMMIT = 'ab2f4dbb7c95c144ccba2fa8afd11e155aa91133'
LOCK = '1617a3c654395fa24543a12b4eb95c62700f1b75f5d439b8cd1b93ffc7404b03'
CRATE = '6a02e4885ed3bc0f2de90ea6dd45ebcbb66dacffe03547fadbb0eeae2770887d'

def audit(firefox, upstream):
    firefox, upstream = Path(firefox), Path(upstream)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(upstream), *args])
    if hashlib.sha256((firefox/'Cargo.lock').read_bytes()).hexdigest() != LOCK:
        raise ValueError('Unexpected Firefox Cargo.lock')
    lock = tomllib.loads((firefox/'Cargo.lock').read_text())
    packages = [p for p in lock['package'] if p['name'] == 'void' and p['version'] == '1.0.2']
    if len(packages) != 1 or packages[0].get('checksum') != CRATE:
        raise ValueError('Unexpected void package checksum')
    if git('rev-parse', '1.0.2^{commit}').decode().strip() != COMMIT:
        raise ValueError('Upstream release tag changed')
    crate = firefox/'third_party/rust/void'
    package = tomllib.loads((crate/'Cargo.toml').read_text())['package']
    original = tomllib.loads(git('show', COMMIT+':Cargo.toml').decode())['package']
    for key in ('name', 'version', 'authors', 'license', 'repository'):
        if package.get(key) != original.get(key):
            raise ValueError('Package metadata differs: '+key)
    for name in ('README.md', 'src/lib.rs'):
        if (crate/name).read_bytes() != git('show', COMMIT+':'+name):
            raise ValueError('Release file differs: '+name)
    names = git('ls-tree', '-r', '--name-only', COMMIT).decode().splitlines()
    if any(Path(name).name.lower().startswith(('license', 'licence', 'copying')) for name in names):
        raise ValueError('Release contains a license file; review it')
    return {'releaseCommit': COMMIT, 'package': 'void 1.0.2',
            'declaredLicense': package['license'], 'authors': package['authors'],
            'matchingFiles': ['README.md', 'src/lib.rs'],
            'separateLicenseFileAtRelease': False,
            'linkedInFinalBinary': 'not established'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--firefox', required=True, type=Path)
    p.add_argument('--upstream', required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(audit(a.firefox, a.upstream), indent=2))
