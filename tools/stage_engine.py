#!/usr/bin/env python3
"""Stage a locally built engine. Hashes identify this build; they are not a signature."""
from pathlib import Path
import argparse,json,hashlib,subprocess,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
def hash_file(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('checkout',type=Path);a=p.parse_args();repo=a.checkout.resolve()
    lock=json.loads((ROOT/'upstream.lock.json').read_text());out=ROOT/'engine'
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if head!=lock['commit']:raise RuntimeError('Wrong engine source revision.')
    inner=subprocess.check_output(['git','-C',str(repo/'firefox'),'rev-parse','HEAD'],text=True).strip()
    if inner!=lock['gecko_commit']:raise RuntimeError('Wrong inner Gecko revision.')
    record=json.loads((repo/'.browser-patch.json').read_text())
    if record['localNativeSHA256']!=hash_file(ROOT/'native/embed-host.cpp'):raise RuntimeError('Local native source changed after patching.')
    for n,digest in record['files'].items():
        if hash_file(repo/n)!=digest:raise RuntimeError('Native patch changed: '+n)
    paths={'runtime':repo/'gecko.js/wasm/gecko.js','wasm':repo/'gecko.js/wasm/gecko.wasm','data':repo/'gecko.js/wasm/gecko.data'}
    for name,p in paths.items():
        if not p.is_file()or p.stat().st_size==0:raise RuntimeError('Missing build output: '+str(p))
    with paths['wasm'].open('rb')as f:
        if f.read(8)!=b'\0asm\x01\0\0\0':raise RuntimeError('Invalid wasm header.')
    runtime=paths['runtime'].read_text()
    for token in ['createGecko','browser_embed_abi','terminateAllThreads']:
        if token not in runtime:raise RuntimeError('Raw runtime missing '+token)
    # Require separately built client; do not download public endpoints or CDN JS.
    if not (out/'wisp-client.mjs').is_file():raise RuntimeError('Run bundle_wisp.cjs first.')
    for p in paths.values():shutil.copy2(p,out/p.name)
    names={'runtime':'gecko.js','wasm':'gecko.wasm','data':'gecko.data','wisp':'wisp-client.mjs'}
    manifest={'schema':1,'abi':lock['engine_abi'],'upstreamCommit':head,
              'geckoCommit':inner,'nativeSourceSHA256':hash_file(ROOT/'native/embed-host.cpp'),
              'runtimeTested':False,'assets':{}}
    for k,n in names.items():
        p=out/n;manifest['assets'][k]={'file':n,'bytes':p.stat().st_size,'sha256':hash_file(p)}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Staged and hashed. This is NOT a browser compatibility or security certification.')
if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,subprocess.CalledProcessError)as e:print('STOP: '+str(e),file=sys.stderr);sys.exit(1)
