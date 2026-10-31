#!/usr/bin/env python3
"""Collect notices for libraries named in this pinned Gecko link list."""
import argparse
import hashlib
from pathlib import Path
import subprocess

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
PATHS=('third_party/abseil-cpp/LICENSE','third_party/dav1d/COPYING',
       'third_party/msgpack/LICENSE_1_0.txt','third_party/zstd/LICENSE',
       'media/libjpeg/LICENSE.md','media/libjpeg/README.ijg','media/libmkv/LICENSE',
       'media/libnestegg/LICENSE','media/libpng/LICENSE','media/libspeex_resampler/COPYING',
       'media/libwebp/COPYING','media/libyuv/LICENSE','media/libcubeb/LICENSE',
       'third_party/content_analysis_sdk/LICENSE',
       'third_party/rust/seahash/Cargo.toml.orig',
       'third_party/rust/app_units/Cargo.toml.orig',
       'third_party/rust/core_maths/Cargo.toml.orig',
       'third_party/rust/debug_tree/Cargo.toml.orig',
       'third_party/rust/void/Cargo.toml')

# These notices occur inside source files rather than standalone license files.
# Pin both complete inputs before extracting their original comment headers.
AA_STROKE_HEADERS=(
    ('third_party/rust/aa-stroke/src/bezierflattener.rs',
     '6afe01b228b5e05878550af16beee71f0ef7f881203e5fa24d1b628c360908e6', 'lines'),
    ('third_party/rust/aa-stroke/src/tri_rasterize.rs',
     'a01a730551b4b6be78cbc10fe404c9c7f0c2fc46884accfb212f3232d3dc47b7', 'block'),
)

def collect(repo,wpf_license,linked_headers):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    output=b''.join(('\n===== Firefox source: '+path+' =====\n').encode()+git('show','HEAD:'+path)+b'\n' for path in PATHS)
    for path,expected,kind in AA_STROKE_HEADERS:
        source=git('show','HEAD:'+path)
        if hashlib.sha256(source).hexdigest()!=expected:raise ValueError('Unexpected source: '+path)
        if kind=='lines':
            header=b'\n'.join(source.split(b'\n',3)[:3])+b'\n'
            if not header.startswith(b'// Licensed to the .NET Foundation') or b'MIT license' not in header:raise ValueError('Unexpected .NET notice')
        else:
            header,separator,_=source.partition(b'\n*/\n')
            if not separator or b'Copyright 2012 VMware, Inc.' not in header:raise ValueError('Unexpected VMware notice')
            header+=separator
        output+=('\n===== Firefox source notice: '+path+' =====\n').encode()+header+b'\n'
    license_text=wpf_license.read_bytes()
    if hashlib.sha256(license_text).hexdigest()!='ae48df11a335dc1a615f4f938b69cba73bcf4485c4f97af49b38efb0f216353b':raise ValueError('Unexpected WPF license')
    output+=b'\n===== .NET WPF LICENSE.TXT, revision 3993645a2957293053ec8090eff1fd472a07cd65 =====\n'+license_text+b'\n'
    header_text=linked_headers.read_bytes()
    if hashlib.sha256(header_text).hexdigest()!='2f7b3f7d5e6892292b83d2b8808f67661cdb66ea6d3b618c59a17d6e3cab59a7':raise ValueError('Unexpected Rust source headers')
    output+=b'\n'+header_text
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--firefox',type=Path,required=True);parser.add_argument('--wpf-license',type=Path,required=True);parser.add_argument('--linked-headers',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('Output must not exist')
    args.output.write_bytes(collect(args.firefox,args.wpf_license,args.linked_headers))
