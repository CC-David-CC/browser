#!/usr/bin/env python3
"""Expand Gecko's generated unified sources named in the pinned link list.

This is build-input evidence, not proof that code survives the final link.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from collections import Counter

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
LINK_SHA='eccd9f7f14288290eec6b15d076a1306be323474bbeee5530b9f987478b199ad'
INCLUDE=re.compile(r'^#include "([^"\n]+)"',re.MULTILINE)

def inventory(firefox,objdir):
    firefox=Path(firefox).resolve();objdir=Path(objdir).resolve()
    if subprocess.check_output(['git','-C',str(firefox),'rev-parse','HEAD'],text=True).strip()!=COMMIT:
        raise ValueError('Unexpected Firefox revision')
    listing=objdir/'toolkit/library/build/libxul_so.list';raw=listing.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=LINK_SHA:raise ValueError('Unexpected Gecko link input list')
    generated=[];third_party=[];missing=[];total=0
    for line in raw.decode('utf-8').splitlines():
        obj=(listing.parent/line).resolve()
        if not obj.is_relative_to(objdir):raise ValueError('Object outside build directory')
        if not obj.name.startswith('Unified_'):continue
        matches=[obj.with_suffix(ext) for ext in ('.c','.cpp','.mm') if obj.with_suffix(ext).is_file()]
        if len(matches)!=1:raise ValueError('Missing or ambiguous unified source: '+line)
        source=matches[0];data=source.read_bytes();paths=INCLUDE.findall(data.decode('utf-8'))
        generated.append({'object':obj.relative_to(objdir).as_posix(),'source':source.relative_to(objdir).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'includes':len(paths)})
        for path in paths:
            total+=1;resolved=(source.parent/path).resolve()
            if not resolved.is_file():missing.append({'source':source.relative_to(objdir).as_posix(),'include':path})
            if resolved.is_relative_to(firefox):
                rel=resolved.relative_to(firefox).as_posix()
                if '/third_party/' in '/'+rel:
                    third_party.append({'object':obj.relative_to(objdir).as_posix(),'source':rel})
    counts=Counter(x['source'].split('third_party/',1)[1].split('/',1)[0] for x in third_party)
    return {'version':'codi-gecko-unified-link-inputs/1','firefoxCommit':COMMIT,'linkListSHA256':LINK_SHA,
            'scope':'generated unified sources in link inputs, not final linked code',
            'unifiedObjects':len(generated),'includes':total,'missingIncludes':missing,
            'thirdPartyGroups':dict(sorted(counts.items())),'thirdPartySources':third_party,'generated':generated}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firefox',type=Path,required=True);p.add_argument('--objdir',type=Path,required=True);a=p.parse_args()
    print(json.dumps(inventory(a.firefox,a.objdir),sort_keys=True,indent=2))
