#!/usr/bin/env python3
"""Inventory Rust object members observed in the reproduced libxul link map.

The map describes the intermediate relocatable Gecko link, not the final
Browser WASM. Inlining and the later link prevent treating absence as proof
that a dependency contributed no code.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
MAP_SHA='2683bbc21bc944cd4df6bd158dd0469be4be8a01c479dfe2f4b209e1362fa6b0'
INVENTORY_SHA='dc4b75f92974d6b68738c53e94b9c904031b65c4632877adc5ebfc95e7676f28'
MEMBER=re.compile(rb'libgkrust\.a\(([^)]+)\):\(')
CRATE=re.compile(r'^([A-Za-z0-9_]+)-([0-9a-f]{16})\.')
def analyze(linkmap,inventory):
 raw=inventory.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INVENTORY_SHA:raise ValueError('Unexpected Rust archive inventory')
 data=json.loads(raw)
 if data.get('version')!='codi-gecko-rust-archive-inputs/1':raise ValueError('Unexpected inventory version')
 allowed={(e['crate'],e['buildHash']):e for e in data['crateBuilds']};members=set();lines=0;digest=hashlib.sha256()
 with linkmap.open('rb') as f:
  for line in f:
   digest.update(line)
   if len(line)>1024*1024:raise ValueError('Unexpected map line size')
   m=MEMBER.search(line)
   if m:members.add(m.group(1).decode('ascii'));lines+=1
 if digest.hexdigest()!=MAP_SHA:raise ValueError('Unexpected link map hash')
 groups=collections.Counter();other=[]
 for member in members:
  m=CRATE.match(member)
  if m:groups[(m[1],m[2])]+=1
  else:other.append(member)
 if any(k not in allowed or n>allowed[k]['members'] for k,n in groups.items()):raise ValueError('Map member does not match archive inventory')
 if any(name not in data['otherMembers'] for name in other):raise ValueError('Unexpected non-crate archive member')
 entries=[{'crate':crate,'buildHash':h,'package':allowed[(crate,h)]['package'],'members':count} for (crate,h),count in sorted(groups.items())]
 return {'version':'codi-gecko-rust-linkmap/1','mapSHA256':MAP_SHA,'archiveInventorySHA256':INVENTORY_SHA,
         'scope':'reproduced intermediate relocatable link; not final WASM or proof of absence after inlining',
         'mapEntries':lines,'distinctArchiveMembers':len(members),'crateBuilds':entries,'otherMembers':sorted(other)}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--map',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
 d=analyze(a.map,a.inventory);a.output.write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'mapEntries':d['mapEntries'],'distinctArchiveMembers':d['distinctArchiveMembers'],'crateBuilds':len(d['crateBuilds']),'packages':len({x['package'] for x in d['crateBuilds']}),'otherMembers':d['otherMembers']}))
