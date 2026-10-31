#!/usr/bin/env python3
"""Inventory Rust archive inputs, not the objects retained by the final link."""
import argparse,collections,hashlib,json,re,subprocess,tomllib
from pathlib import Path
COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
ARCHIVE_SHA='78d6b99aae1276937b77756aede0a102a17357b3b7222509cc9efb9a1e8b5dcd'
MEMBER=re.compile(r'^([A-Za-z0-9_]+)-([0-9a-f]{16})\.')
FINGERPRINT=re.compile(r'^(.+)-([0-9a-f]{16})$')

def associate(members,fingerprints):
    groups=collections.Counter();other=[]
    for name in members:
        match=MEMBER.match(name)
        if match:groups[(match[1],match[2])]+=1
        else:other.append(name)
    byhash=collections.defaultdict(list)
    for name in fingerprints:
        match=FINGERPRINT.fullmatch(name)
        if match:byhash[match[2]].append(match[1])
    result=[]
    for (crate,build_hash),count in sorted(groups.items()):
        candidates=byhash[build_hash]
        if len(candidates)!=1:raise ValueError('Missing or ambiguous target fingerprint for '+crate+'-'+build_hash)
        result.append({'crate':crate,'buildHash':build_hash,'package':candidates[0],'members':count})
    return result,sorted(other)

def inventory(archive,ar,repo,fingerprints):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True)
    if git('rev-parse','HEAD').strip()!=COMMIT or git('status','--porcelain'):raise ValueError('Expected clean pinned Firefox checkout')
    h=hashlib.sha256()
    with archive.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=ARCHIVE_SHA:raise ValueError('Wrong Rust static archive')
    members=subprocess.check_output([str(ar),'t',str(archive)],text=True).splitlines()
    fps=[p.name for p in fingerprints.iterdir() if p.is_dir() and not p.is_symlink() and list(p.glob('lib-*.json'))]
    entries,other=associate(members,fps);names={e['package'] for e in entries};packages={}
    for name in git('ls-files','*Cargo.toml').splitlines():
        try:pkg=tomllib.loads((repo/name).read_text(encoding='utf-8')).get('package',{})
        except (ValueError,OSError,UnicodeError):continue
        package=pkg.get('name')
        if package in names:packages.setdefault(package,[]).append({'manifest':name,'version':pkg.get('version'),'license':pkg.get('license')})
    return {'version':'codi-gecko-rust-archive-inputs/1','firefoxCommit':COMMIT,'archiveSHA256':ARCHIVE_SHA,
            'scope':'archive members supplied to Gecko link, not proof of final retained objects',
            'memberCount':len(members),'crateBuilds':entries,'otherMembers':other,
            'packages':{name:packages[name] for name in sorted(packages)},'withoutTrackedManifest':sorted(names-packages.keys())}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('archive','ar','firefox','fingerprints','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    data=inventory(a.archive,a.ar,a.firefox,a.fingerprints);a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'members':data['memberCount'],'crateBuilds':len(data['crateBuilds']),'packages':len({e['package'] for e in data['crateBuilds']}),'matchedManifests':len(data['packages']),'unmatched':data['withoutTrackedManifest'],'otherMembers':data['otherMembers']}))
