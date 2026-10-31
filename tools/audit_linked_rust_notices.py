#!/usr/bin/env python3
"""Inventory notice coverage for Rust packages associated with final symbols.

Heading and supplemental-source checks are evidence of included material, not
proof of exact linkage or a legal compliance determination.
"""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_INVENTORY='dc4b75f92974d6b68738c53e94b9c904031b65c4632877adc5ebfc95e7676f28'
EXPECTED_SUMMARY='8de3a1c7a0c07ed9d07c3032dde1275b71cc82a62aa57e2bc2a0a517ac4d8ac7'
EXPECTED_NOTICES='953caeb7f1f698f875d5ef4675d81b31e6cb4c26b3665cebf4a3419d497c1ba0'
# Search labels for packages without vendored top-level notices. A match is a
# lead for human review, not a guarantee that its license terms are satisfied.
SUPPLEMENT={
 'aa-stroke':'Firefox source notice: third_party/rust/aa-stroke/',
 'debug_tree':'Firefox source: third_party/rust/debug_tree/Cargo.toml.orig',
 'seahash':'Firefox source: third_party/rust/seahash/Cargo.toml.orig',
 'pulse':'cubeb-pulse-rs LICENSE', 'pulse-ffi':'cubeb-pulse-rs LICENSE',
 'neqo-common':'neqo crates 0.29.0;', 'neqo-http3':'neqo crates 0.29.0;',
 'neqo-qpack':'neqo crates 0.29.0;', 'neqo-transport':'neqo crates 0.29.0;',
 'neqo-udp':'neqo crates 0.29.0;',
}

def sha(raw):return hashlib.sha256(raw).hexdigest()
def audit(inv,summary,text):
    packages=inv['packages']; candidates=set(summary['uniquePackageSymbols'])|set(summary['ambiguousPackageSymbols'])
    rows=[]
    for name in sorted(candidates):
        for entry in packages.get(name,[]):
            if not entry['manifest'].startswith('third_party/rust/'):continue
            prefix='===== '+name+' '+str(entry['version'])+';'
            pos=text.find(prefix)
            end=text.find('\n===== ',pos+len(prefix)) if pos>=0 else -1
            section=text[pos:end if end>=0 else None] if pos>=0 else ''
            no_file='No separate license file in this vendored package' in section
            marker=SUPPLEMENT.get(name,name+' '+str(entry['version']))
            if no_file and name not in SUPPLEMENT:
                supplemental=any(line.startswith('===== ') and marker in line and 'https://raw.githubusercontent.com/' in line for line in text.splitlines())
            else:
                supplemental=marker in text if no_file else None
            rows.append({'name':name,'version':entry['version'],'license':entry['license'],
                         'manifest':entry['manifest'],'heading':pos>=0,'vendoredNotice':pos>=0 and not no_file,
                         'supplementMarker':marker if no_file else None,'supplementPresent':supplemental,
                         'metadataOnly':name in ('aa-stroke','debug_tree','seahash') and no_file,
                         'historicalSourceMatch':name=='svg_fmt' and no_file})
    return {'version':'codi-linked-rust-notice-coverage/1',
            'scope':'vendored package versions attributed uniquely or ambiguously by final symbol matching; presence checks only',
            'rows':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inventory','summary','notices','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    values=[a.inventory.read_bytes(),a.summary.read_bytes(),a.notices.read_bytes()]
    if [sha(v) for v in values]!=[EXPECTED_INVENTORY,EXPECTED_SUMMARY,EXPECTED_NOTICES]:raise ValueError('Inputs are not the pinned audit inputs')
    if a.output.exists() or a.output.is_symlink():raise ValueError('Output already exists')
    result=audit(json.loads(values[0]),json.loads(values[1]),values[2].decode('utf-8'))
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    rows=result['rows'];print(json.dumps({'versions':len(rows),'missingHeadings':[r['name'] for r in rows if not r['heading']],
      'withoutVendoredNotice':sum(not r['vendoredNotice'] for r in rows),
      'missingSupplement':[r['name'] for r in rows if r['supplementPresent'] is False],
      'metadataOnly':[r['name'] for r in rows if r['metadataOnly']]}))

if __name__=='__main__':main()
