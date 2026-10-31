#!/usr/bin/env python3
"""Collect notices for libraries named in this pinned Gecko link list."""
import argparse
from pathlib import Path
import subprocess

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
PATHS=('third_party/abseil-cpp/LICENSE','third_party/dav1d/COPYING',
       'third_party/msgpack/LICENSE_1_0.txt','third_party/zstd/LICENSE',
       'media/libjpeg/LICENSE.md','media/libjpeg/README.ijg','media/libmkv/LICENSE',
       'media/libnestegg/LICENSE','media/libpng/LICENSE','media/libspeex_resampler/COPYING',
       'media/libwebp/COPYING','media/libyuv/LICENSE','media/libcubeb/LICENSE',
       'third_party/content_analysis_sdk/LICENSE')

def collect(repo):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    return b''.join(('\n===== Firefox source: '+path+' =====\n').encode()+git('show','HEAD:'+path)+b'\n' for path in PATHS)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--firefox',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink():parser.error('Output must not exist')
    args.output.write_bytes(collect(args.firefox))
