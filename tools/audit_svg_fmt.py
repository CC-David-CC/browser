#!/usr/bin/env python3
"""Compare Firefox's svg_fmt crate with a source-matched upstream tree.

The crate's recorded 0.4.1 VCS revision is unavailable; this audit does not
claim that the older reachable commit is that missing revision.
"""
import argparse, hashlib, json, tomllib
from pathlib import Path
from urllib.request import Request, urlopen

REV='492600cac47f64bcadaf9ad037ed64c5fecc8e63'
MISSING_REV='95612bf320385cb460571939d46594e5651e88fb'
FILES={
 'src/layout.rs':'dc1378e2911912b59e826b31e30306ecc47cf2f12bada184c7c73a21c3a15acf',
 'src/lib.rs':'983b5686a05b093bf405418fe42eb662f72deb9f05c30c6ea122c477683ad405',
 'src/svg.rs':'345e6aac8c483b2c68b3b62caf3418c9078992c26c943a9dbffbd3600dd8f2d8',
 'README.md':'efffe3ac4d3b72a3786c842724f78721f65047c2420a51362355b73e6c5f879d',
 'Cargo.toml.orig':'d49c3b21ad717cf0819c6ac7931a3f93a5acbe9a17224e69e7d660453f078995',
}
LICENSE='7e98bed7f100747aaae7d82ab94fbe6b76fd6b84b09a3aaa413bff8196d0fbb1'
def digest(data):return hashlib.sha256(data).hexdigest()
def fetch(path):
 url=f'https://raw.githubusercontent.com/nical/rust_debug/{REV}/{path}'
 with urlopen(Request(url,headers={'User-Agent':'CodiServer-license-review/1'}),timeout=30) as response:return response.read(524289)
def run(firefox):
 crate=Path(firefox)/'third_party/rust/svg_fmt'
 vcs=json.loads((crate/'.cargo_vcs_info.json').read_text());assert vcs['git']['sha1']==MISSING_REV
 package=tomllib.loads((crate/'Cargo.toml.orig').read_text())['package']
 assert (package['name'],package['version'],package['license'],package['repository'])==('svg_fmt','0.4.1','MIT/Apache-2.0','https://github.com/nical/rust_debug')
 lock=tomllib.loads((Path(firefox)/'Cargo.lock').read_text());entry=next(x for x in lock['package'] if x['name']=='svg_fmt' and x['version']=='0.4.1');assert entry['checksum']=='8fb1df15f412ee2e9dfc1c504260fa695c1c3f10fe9f4a6ee2d2184d7d6450e2'
 for name,expected in FILES.items():
  local=(crate/name).read_bytes();assert digest(local)==expected
  upstream=fetch('svg_fmt/'+('Cargo.toml' if name=='Cargo.toml.orig' else name))
  if name=='Cargo.toml.orig':
   assert upstream.count(b'version = "0.4.0"')==1
   upstream=upstream.replace(b'version = "0.4.0"',b'version = "0.4.1"')
  assert local==upstream, name
 assert digest(fetch('LICENSE'))==LICENSE
 print('PASS svg_fmt 0.4.1 source and README match the reachable upstream tree; only the Cargo version differs. Package VCS revision remains unavailable.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('firefox',type=Path);run(p.parse_args().firefox)
