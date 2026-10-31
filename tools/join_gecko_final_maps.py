#!/usr/bin/env python3
"""Match final libxul symbols to the reproduced intermediate link map.

This is evidence of direct symbol matches, not a complete component or license
inventory. Inlining, local symbols and identical names can hide provenance.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
WASM_SHA='4da6079da4a9bf6d1d48701895935bb97f3cfc197db38a771f693705c6d64ba3'
FINAL_SHA='5697e6e675004edb8cb32f5ec964d63b7596881353d291e1b46c711cf9d9f699'
INTERMEDIATE_SHA='2683bbc21bc944cd4df6bd158dd0469be4be8a01c479dfe2f4b209e1362fa6b0'
INVENTORY_SHA='dc4b75f92974d6b68738c53e94b9c904031b65c4632877adc5ebfc95e7676f28'
ENTRY=re.compile(rb'\s+(\S+):\((.*)\)\s*$')
ARCHIVE=re.compile(rb'libgkrust\.a\(([^)]+)\)$')
CRATE=re.compile(rb'^([A-Za-z0-9_]+)-([0-9a-f]{16})\.')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def lines(path,expected):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for line in f:
   if len(line)>1024*1024:raise ValueError('Unexpected map line length')
   h.update(line);yield line
 if h.hexdigest()!=expected:raise ValueError('Unexpected link map hash')
def join(wasm,final_map,intermediate_map,inventory):
 if sha(wasm)!=WASM_SHA:raise ValueError('Unexpected final WASM')
 raw=inventory.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INVENTORY_SHA:raise ValueError('Unexpected Rust archive inventory')
 inv=json.loads(raw)
 if inv.get('version')!='codi-gecko-rust-archive-inputs/1':raise ValueError('Unexpected inventory version')
 allowed={(e['crate'],e['buildHash']):e['package'] for e in inv['crateBuilds']}
 final=set()
 for line in lines(final_map,FINAL_SHA):
  m=ENTRY.search(line)
  if m and m.group(1).endswith(b'/libxul.o'):final.add(m.group(2))
 origins={};entries=0
 for line in lines(intermediate_map,INTERMEDIATE_SHA):
  m=ENTRY.search(line)
  if not m or m.group(2) not in final:continue
  origin,symbol=m.groups();a=ARCHIVE.search(origin)
  if a:
   c=CRATE.match(a.group(1))
   if c:
    key=(c.group(1).decode('ascii'),c.group(2).decode('ascii'))
    if key not in allowed:raise ValueError('Map crate absent from archive inventory')
    tag=allowed[key]
   else:
    tag='[native archive member]'
    if a.group(1).decode('ascii') not in inv['otherMembers']:raise ValueError('Unexpected native archive member')
  else:tag='[non-rust input]'
  origins.setdefault(symbol,set()).add(tag);entries+=1
 unique=collections.Counter();ambiguous=collections.Counter()
 for tags in origins.values():
  for tag in tags:
   if not tag.startswith('['):(unique if len(tags)==1 else ambiguous)[tag]+=1
 return {'version':'codi-gecko-final-symbol-join/1','wasmSHA256':WASM_SHA,'finalMapSHA256':FINAL_SHA,
         'intermediateMapSHA256':INTERMEDIATE_SHA,'archiveInventorySHA256':INVENTORY_SHA,
         'scope':'direct symbol-name matches; not proof of exclusive origin, absence, or complete license obligations',
         'finalLibxulSymbols':len(final),'intermediateEntries':entries,'matchedSymbols':len(origins),
         'unmatchedFinalSymbols':len(final-origins.keys()),'ambiguousSymbols':sum(len(x)>1 for x in origins.values()),
         'uniquePackageSymbols':dict(sorted(unique.items())),'ambiguousPackageSymbols':dict(sorted(ambiguous.items()))}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('wasm','final-map','intermediate-map','inventory','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
 d=join(a.wasm,a.final_map,a.intermediate_map,a.inventory);a.output.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
 print(json.dumps({k:d[k] for k in ('finalLibxulSymbols','matchedSymbols','unmatchedFinalSymbols','ambiguousSymbols')}))
 print('Packages with unambiguous direct matches:',len(d['uniquePackageSymbols']))
