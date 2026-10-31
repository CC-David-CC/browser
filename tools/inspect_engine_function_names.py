#!/usr/bin/env python3
"""Inspect named functions in the pinned shipped WebAssembly engine.

Names are evidence of retained functions or type references, not a complete
component inventory: optimization, inlining and stripped names affect results.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ENGINE='6736dce5b81479667da894deb15860999f43a4178b9e81eb68f1d10d3508db1b'
TERMS=('svg_fmt::','seahash::','content_analysis::sdk::','app_units::','debug_tree::','core_maths::','void::')
PATTERNS={term:re.compile(r'(?<![A-Za-z0-9_])'+re.escape(term)) for term in TERMS}

def leb(f):
    value=0
    for i in range(10):
        raw=f.read(1)
        if not raw:raise ValueError('Truncated LEB')
        value|=(raw[0]&127)<<(7*i)
        if raw[0]<128:return value
    raise ValueError('Oversized LEB')

def inspect(path):
    path=Path(path);size=path.stat().st_size;h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    if h.hexdigest()!=ENGINE:raise ValueError('Not the pinned shipped engine')
    counts={term:0 for term in TERMS};samples={term:[] for term in TERMS};total=None
    with path.open('rb') as f:
        if f.read(8)!=b'\x00asm\x01\x00\x00\x00':raise ValueError('Invalid WASM header')
        while f.tell()<size:
            kind=f.read(1)[0];length=leb(f);end=f.tell()+length
            if end>size:raise ValueError('Truncated section')
            if kind==0:
                n=leb(f)
                if n>1024 or f.tell()+n>end:raise ValueError('Invalid custom section name')
                name=f.read(n)
                if name==b'name':
                    while f.tell()<end:
                        subkind=f.read(1)[0];length=leb(f);subend=f.tell()+length
                        if subend>end:raise ValueError('Truncated name subsection')
                        if subkind==1:
                            if total is not None:raise ValueError('Duplicate function name subsection')
                            total=leb(f)
                            if total>1000000:raise ValueError('Too many function names')
                            for _ in range(total):
                                leb(f);n=leb(f)
                                if n>1000000 or f.tell()+n>subend:raise ValueError('Invalid function name')
                                name=f.read(n).decode('utf-8','strict')
                                for term in TERMS:
                                    if PATTERNS[term].search(name):
                                        counts[term]+=1
                                        if len(samples[term])<3:samples[term].append(name)
                            if f.tell()!=subend:raise ValueError('Invalid function name map')
                        f.seek(subend)
            f.seek(end)
    if total is None:raise ValueError('Function names unavailable')
    return {'engineSHA256':ENGINE,'namedFunctions':total,'matches':counts,'samples':samples,
            'scope':'retained names and type references, not a complete linked component inventory'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('engine',type=Path);a=p.parse_args()
    print(json.dumps(inspect(a.engine),sort_keys=True,indent=2))
