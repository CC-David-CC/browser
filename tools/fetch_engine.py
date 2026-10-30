#!/usr/bin/env python3
"""Explicit network action: fetch exactly the upstream source recorded in the lock."""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--into',type=Path,default=ROOT/'.work/firefox-wasm');a=p.parse_args()
lock=json.loads((ROOT/'upstream.lock.json').read_text());dest=a.into.resolve()
def git(*args):return subprocess.check_output(['git','-C',str(dest),*args],text=True).strip()
if dest.exists():
    if not (dest/'.git').exists():sys.exit('STOP: destination exists but is not the expected checkout.')
    if git('rev-parse','HEAD')!=lock['commit']:sys.exit('STOP: existing checkout has a different revision; will not reset it.')
    if git('remote','get-url','origin')!=lock['repository']:sys.exit('STOP: existing origin differs.')
    print(dest);sys.exit(0)
dest.mkdir(parents=True)
try:
    subprocess.run(['git','init',str(dest)],check=True)
    git('remote','add','origin',lock['repository']);git('fetch','--depth','1','origin',lock['commit'])
    git('checkout','--detach','FETCH_HEAD')
    if git('rev-parse','HEAD')!=lock['commit']:raise RuntimeError('Revision mismatch.')
except Exception:
    print('Fetch failed. The partial directory was retained for inspection; no unrelated files were removed.',file=sys.stderr)
    raise
print(dest)
