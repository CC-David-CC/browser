#!/usr/bin/env python3
"""Collect source comment notices from Rust packages seen in the final-link map.

This is a conservative candidate set: package attribution does not prove that a
particular source file survived linking. Tests, examples and comments beginning
past the first 100 lines are outside this scan; this is not a legal conclusion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
INVENTORY_SHA='dc4b75f92974d6b68738c53e94b9c904031b65c4632877adc5ebfc95e7676f28'
SUMMARY_SHA='8de3a1c7a0c07ed9d07c3032dde1275b71cc82a62aa57e2bc2a0a517ac4d8ac7'

def pinned(path,expected):
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Unexpected input: '+str(path))
    return json.loads(data)

def collect(repo,inventory,summary):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    if git('status','--porcelain','--','third_party/rust'):raise ValueError('Vendored Rust source has uncommitted changes')
    inv=pinned(inventory,INVENTORY_SHA)['packages']
    linked=pinned(summary,SUMMARY_SHA)['uniquePackageSymbols']
    paths=sorted({str(Path(e['manifest']).parent) for n in linked for e in inv.get(n,[]) if e['manifest'].startswith('third_party/rust/')})
    if len(paths)!=195:raise ValueError('Unexpected package set')
    tracked=git('ls-files','-z','--',*paths).decode().split('\0')
    blocks={}
    for file in tracked:
        if not file.endswith(('.rs','.c','.cpp','.h','.S')) or any(p in Path(file).parts for p in ('tests','test','examples','benches','bench')):continue
        try:data=(repo/file).read_text(encoding='utf-8')
        except (OSError,UnicodeError):continue
        prefix='\n'.join(data.splitlines()[:100])
        for match in re.finditer(r'/\*.*?\*/|(?m:(?:^[ \t]*//[^\n]*(?:\n|$))+)',prefix,re.S):
            comment=match.group().strip()
            if re.search(r'copyright\s*(?:\(c\)|©|[0-9])',comment,re.I):blocks.setdefault(comment,[]).append(file)
    out=['Source copyright comment blocks in selected linked Rust package candidates\n',
         'Firefox '+COMMIT+'; inferred from direct final-link symbol matches. This conservative scan does not prove that any particular file was linked.\n']
    for comment,files in sorted(blocks.items()):
        out.append('\n===== Source files: '+', '.join(sorted(files))+' =====\n'+comment+'\n')
    return ''.join(out).encode(),len(blocks),sum(map(len,blocks.values()))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('firefox','inventory','summary','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    data,blocks,files=collect(a.firefox,a.inventory,a.summary);a.output.write_bytes(data)
    print(json.dumps({'blocks':blocks,'fileReferences':files,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}))
