#!/usr/bin/env python3
"""Stage the exact redistributable Noto fonts used by the Browser.

Uses matching installed Ubuntu fonts when available; otherwise downloads and
verifies the pinned Ubuntu packages before extracting them in a temporary dir.
The license notices are kept alongside this script's output in engine-fonts/.
"""
from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
FONTS = (
    ('usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf', 'arabic.ttf',
     '504d7407d86875acf7d04dfaa0fd7524d0b8797723bc4aa18022f29db25b0b6e',
     'pool/main/f/fonts-noto/fonts-noto-core_20201225-2_all.deb',
     '4fee136cb12fc197703a340e010478f780a41044339fcefbd78ed9aa96c8b617'),
    ('usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'cjk.data',
     'b76b0433203017ca80401b2ee0dd69350349871c4b19d504c34dbdd80541690a',
     'pool/main/f/fonts-noto-cjk/fonts-noto-cjk_20230817+repack1-3_all.deb',
     '7d64b985f6fe128c99eae5610d5c047338e572bdcfb2bb09736be01b824a7f6c'),
)

def digest(path):
    h = sha256()
    with path.open('rb') as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    dest = ROOT / 'engine-fonts'
    dest.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='codi-fonts-') as directory:
        tmp = Path(directory)
        for relative, name, expected, package, package_sha in FONTS:
            target = dest / name
            if target.is_file() and digest(target) == expected:
                continue
            source = Path('/') / relative
            if not source.is_file() or digest(source) != expected:
                archive = tmp / (name + '.deb')
                with urllib.request.urlopen('https://archive.ubuntu.com/ubuntu/' + package, timeout=120) as response, archive.open('wb') as out:
                    shutil.copyfileobj(response, out)
                if digest(archive) != package_sha:
                    raise ValueError('Font package checksum mismatch: ' + package)
                unpack = tmp / (name + '-unpacked')
                subprocess.run(['dpkg-deb', '-x', str(archive), str(unpack)], check=True)
                source = unpack / relative
            if digest(source) != expected:
                raise ValueError('Font checksum mismatch: ' + name)
            shutil.copyfile(source, target)
            print('Prepared', target.name)

if __name__ == '__main__':
    main()
