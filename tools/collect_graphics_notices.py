#!/usr/bin/env python3
"""Collect exact source notices for additional linked Firefox object groups."""
import argparse
from pathlib import Path
import subprocess

COMMIT='2e1e835a5da5907e5ceef19aade58a7493f1e34d'
PATHS=(
    'gfx/angle/checkout/LICENSE', 'gfx/skia/LICENSE',
    'gfx/cairo/cairo/COPYING', 'gfx/cairo/cairo/COPYING-LGPL-2.1',
    'gfx/cairo/cairo/COPYING-MPL-1.1', 'gfx/cairo/libpixman/COPYING',
    'modules/freetype2/LICENSE.TXT', 'modules/freetype2/src/bdf/README',
    'modules/freetype2/src/pcf/README', 'modules/brotli/LICENSE',
    'toolkit/components/protobuf/LICENSE', 'toolkit/components/protobuf/third_party/utf8_range/LICENSE',
    'toolkit/components/jsoncpp/LICENSE', 'parser/expat/COPYING',
    'gfx/graphite2/LICENSE', 'gfx/graphite2/COPYING', 'gfx/harfbuzz/COPYING',
    'gfx/harfbuzz/src/ms-use/COPYING', 'modules/woff2/LICENSE',
    'other-licenses/snappy/src/COPYING', 'ipc/chromium/src/LICENSE',
)

def collect(repo):
    def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
    if git('rev-parse','HEAD').decode().strip()!=COMMIT:raise ValueError('Unexpected Firefox revision')
    return b''.join(('\n===== Firefox source: '+p+' =====\n').encode()+git('show','HEAD:'+p)+b'\n' for p in PATHS)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firefox',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists() or a.output.is_symlink():p.error('Output must not exist')
    a.output.write_bytes(collect(a.firefox))
