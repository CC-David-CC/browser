#!/usr/bin/env python3
"""Collect exact-revision enum-map licenses and vendored SPDX attribution."""
import argparse,hashlib,json,tomllib
from pathlib import Path
from urllib.request import Request,urlopen
REV='c788a9c4bd0431308d889942719f7a38761d9884'
BASE='https://codeberg.org/sugar700/enum-map/raw/commit/'+REV+'/'
LICENSES={'LICENSES/MIT.txt':'b85dcd3e453d05982552c52b5fc9e0bdd6d23c6f8e844b984a88af32570b0cc0','LICENSES/Apache-2.0.txt':'074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff'}
def digest(b):return hashlib.sha256(b).hexdigest()
def run(firefox):
 p=Path(firefox)/'third_party/rust/enum-map';v=json.loads((p/'.cargo_vcs_info.json').read_text());assert v['git']['sha1']==REV
 package=tomllib.loads((p/'Cargo.toml').read_text())['package'];assert (package['name'],package['version'],package['license'])==('enum-map','2.7.3','MIT OR Apache-2.0')
 lock=tomllib.loads((Path(firefox)/'Cargo.lock').read_text());entry=next(x for x in lock['package'] if x['name']=='enum-map' and x['version']=='2.7.3');assert entry['checksum']=='6866f3bfdf8207509a033af1a75a7b08abda06bbaaeae6669323fd5a097df2e9'
 copyrights=set()
 for f in p.rglob('*'):
  if not f.is_file() or f.is_symlink():continue
  try:lines=f.read_text().splitlines()
  except UnicodeDecodeError:continue
  for line in lines:
   if 'SPDX-FileCopyrightText:' in line:copyrights.add(line[line.index('SPDX-FileCopyrightText:'):].strip())
 if not copyrights:raise ValueError('No vendored attribution found')
 result=['===== enum-map 2.7.3 vendored SPDX copyright lines =====\n'+'\n'.join(sorted(copyrights))+'\n']
 for path,expected in LICENSES.items():
  url=BASE+path
  with urlopen(Request(url,headers={'User-Agent':'CodiServer-license-review/1'}),timeout=30) as response:raw=response.read(524289)
  if len(raw)>524288 or digest(raw)!=expected:raise ValueError('Upstream license changed: '+url)
  result.append('\n===== enum-map 2.7.3 '+url+' =====\n'+raw.decode().rstrip()+'\n')
 return ''.join(result).encode()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('firefox',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
 a.output.write_bytes(run(a.firefox))
