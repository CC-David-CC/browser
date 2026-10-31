#!/usr/bin/env python3
"""Check that vendored manifests in the pinned archive have notice headings.

Heading coverage does not prove complete license compliance or that the final
link retained a crate. Workspace/toolchain sources need their separate review.
"""
import argparse,hashlib,json,re
from pathlib import Path
INVENTORY_SHA='dc4b75f92974d6b68738c53e94b9c904031b65c4632877adc5ebfc95e7676f28'
RUST_SHA='8c083caaa5a59ab1a01c0239ca82e378f4e9868b91f6c746a4f711ccea9444eb'
COMBINED_SHA='04dd62fdc18dc6b94bfa439f55b4103de6bb34394b53e8e6167264dd8d2b8ada'
def verify(inventory,rust,combined):
    raw=inventory.read_bytes();notices=rust.read_bytes();all_notices=combined.read_bytes()
    for value,expected,label in ((raw,INVENTORY_SHA,'inventory'),(notices,RUST_SHA,'Rust notices'),(all_notices,COMBINED_SHA,'combined notices')):
        if hashlib.sha256(value).hexdigest()!=expected:raise ValueError('Unexpected '+label+' hash')
    data=json.loads(raw)
    if data.get('version')!='codi-gecko-rust-archive-inputs/1':raise ValueError('Unexpected inventory version')
    if notices not in all_notices:raise ValueError('Rust notice input absent from combined notice')
    headings=set(re.findall(r'^===== ([^\n]+?) ([^\s;]+); declared license:',notices.decode('utf-8'),re.M))
    missing=[];covered=0
    for name,entries in sorted(data['packages'].items()):
        for entry in entries:
            if entry['manifest'].startswith('third_party/rust/'):
                covered+=1
                if (name,entry['version']) not in headings:missing.append(name+' '+str(entry['version']))
    if missing:raise ValueError('Vendored package headings missing: '+', '.join(missing))
    return {'vendoredManifestsCovered':covered,'missing':missing,'scope':'heading coverage only; not complete license compliance'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inventory','rust','combined'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(verify(a.inventory,a.rust,a.combined),sort_keys=True))
