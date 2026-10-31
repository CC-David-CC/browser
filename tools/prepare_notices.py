#!/usr/bin/env python3
"""Prepare browsable license notices for the pinned Browser engine build.

Inputs are produced by the actual engine build and locked dependency install.
The output is static text only; it is not automatically published.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import subprocess

SOURCES={
 'firefox-2e1e835a.tar.zst':'85618173c479db5432a046b86e94bec24f5edba14013390fbf50ad86c7e688cb',
 'firefox-wasm-bc69aaa5.tar.zst':'1c2cea6cd55f317fb196b389d5580f2d783296ecd13af4765c2b1e491d2bc57c',
 'firefox-wasm-local.patch':'63effdb856f86dad6995efe99a4d520694e4c9234a279e6ff3c0f6cf3131df8c',
 'embed-host.cpp':'13080154869cf68b07186c19dfc9891f3c85246ad7a6e721fd8fce549dde5e03',
 'emscripten-6.0.1-patched-source.tar.zst':'0ef04153b359fc83a6222c44aebeb32b9ad96e36362720c958f0d2e97b7ad818',
 'wisp-js-0.4.1-source.tar.zst':'3f5ed9fd60dfab9fecef30ce6877f436eb4895a096873e551c2fb4cb13f08557',
 'codi-browser-source-59dfaf024.tar.zst':'00e499a9c5e8c812666616023f4d02e98f49696b7fc7d85040123a93ebe0ea34',
 'codi-browser-source-0fc6bf9a7.tar.zst':'47ac4d287646b42b808680e2be422e4a7a7bf62dcd928b6ae911bf4a2c91bbe4',
 'codi-browser-source-adece7482.tar.zst':'2e64c1c3856f622af986157059eca6f8f14a8c73e275829d397372b70701c127',
 'codi-browser-source-2ed6d0259.tar.zst':'49f1c63f6160a58d9d6624d5baa35589fae1a74580f32cbb8883f71f9a203b0b',
 'codi-browser-source-0488c275e.tar.zst':'841993d069a9d824942224b2e34012a1dc56ce6c24f3407b920adaa4f2d7e0cd',
 'codi-browser-source-802621ec2.tar.zst':'128c33ee16a6dde95f5c594b19ef6c8a05cb9b251024e95ac859f888b3a26c90',
 'codi-relay-source-05e70e3b0.tar.zst':'6031d72c1c102de2260a634e9e1b8b559f8cccf292b6512e9270e348f2df5ef9',
}
FIREFOX_LICENSE_SHA='e84624c9655b7d4d28a35e1539fdba8420b141ed4d12c791ab7a53e996a84701'
LIBERATION_LICENSE_SHA='93fed46019c38bbe566b479d22148e2e8a1e85ada614accb0211c37b2c61c19b'
COMPILED_NOTICES_SHA='85201fadf7d77201dc1d8c026f0340ecd6b258f6d63fe339486a200d3e377dde'
RUST_NOTICES_SHA='8e8bafa0d9f2f3243d1e02910c9b9fd270c24f9c357aa3fcafcb3be8a4a60712'
EMS_LICENSES=('LICENSE','system/lib/libunwind/LICENSE.TXT','system/lib/mimalloc/LICENSE',
              'system/lib/libc/musl/COPYRIGHT','system/lib/libcxx/LICENSE.TXT',
              'system/lib/compiler-rt/LICENSE.TXT','system/lib/llvm-libc/LICENSE.TXT',
              'system/lib/libcxxabi/LICENSE.TXT')


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def member(archive,name):
    return subprocess.run(['tar','--zstd','-xOf',str(archive),name],check=True,capture_output=True).stdout
def prepare(firefox_license,emscripten,wisp,adapter_license,liberation_license,compiled_notices,rust_notices,out):
    out=Path(out).absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():raise ValueError('New output directory required')
    if sha(firefox_license)!=FIREFOX_LICENSE_SHA:raise ValueError('Firefox notice is not from the pinned build')
    if sha(emscripten)!=SOURCES['emscripten-6.0.1-patched-source.tar.zst']:raise ValueError('Wrong Emscripten source archive')
    if sha(wisp)!=SOURCES['wisp-js-0.4.1-source.tar.zst']:raise ValueError('Wrong Wisp source archive')
    if sha(liberation_license)!=LIBERATION_LICENSE_SHA:raise ValueError('Wrong Liberation Sans font license')
    if sha(compiled_notices)!=COMPILED_NOTICES_SHA:raise ValueError('Wrong compiled component notices')
    if sha(rust_notices)!=RUST_NOTICES_SHA:raise ValueError('Wrong Rust component notices')
    raw=Path(firefox_license).read_text(encoding='utf-8')
    # Retain the license text; make Firefox-internal links usable as a normal
    # same-origin webpage and remove Firefox-only stylesheet references.
    page=raw.replace('href="about:license#','href="#').replace('href="about:buildconfig"','href="/browser-sources/"')
    page='\n'.join(line for line in page.split('\n') if 'href="chrome://global/skin/' not in line)
    ems=[]
    for name in EMS_LICENSES:
        data=member(emscripten,'emscripten/'+name).decode('utf-8')
        ems.append('===== emscripten/'+name+' =====\n'+data.rstrip()+'\n')
    ems.append('===== Liberation Sans fonts: SIL Open Font License 1.1 =====\n'+Path(liberation_license).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append(Path(compiled_notices).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append(Path(rust_notices).read_text(encoding='utf-8').rstrip()+'\n')
    license_wisp=member(wisp,'LICENSE');adapter=Path(adapter_license).read_bytes()
    links='\n'.join('<li><a href="'+html.escape(name,quote=True)+'">'+html.escape(name)+'</a><br><code>SHA-256 '+value+'</code></li>' for name,value in SOURCES.items())
    index='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Browser licenses and source</title></head><body><main><h1>Browser licenses and source</h1>
<p>The Browser uses a locally built Firefox/Gecko WebAssembly port and the Wisp client. These notices and source snapshots correspond to the build offered by this site.</p>
<h2>License notices</h2><ul><li><a href="firefox-licenses.html">Firefox and bundled component notices</a></li><li><a href="emscripten-licenses.txt">Emscripten, compiled components and Liberation Sans font notices</a></li><li><a href="wisp-license.txt">Wisp client: GNU AGPL 3.0</a></li><li><a href="adapter-license.txt">Browser adapter: MIT license</a></li></ul>
<h2>Source code</h2><p>The Firefox-WASM base, local patch and added native file together represent the modified wrapper. The Emscripten snapshot includes the build's patched sources. Large archives download only when selected.</p><ul>'''+links+'''</ul>
<p>IP geolocation data: <a href="https://db-ip.com">IP Geolocation by DB-IP</a>.</p></main></body></html>\n'''
    out.mkdir(mode=0o755)
    for name,data in [('index.html',index.encode()),('firefox-licenses.html',page.encode()),
                      ('emscripten-licenses.txt','\n'.join(ems).encode()),('wisp-license.txt',license_wisp),
                      ('adapter-license.txt',adapter)]:
        (out/name).write_bytes(data)
    records={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir())}
    (out/'notice-manifest.json').write_text(json.dumps({'version':'codi-browser-notices/1','sourceArchives':SOURCES,'files':records},sort_keys=True,indent=2)+'\n')
    return records


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('firefox-license','emscripten','wisp','adapter-license','liberation-license','compiled-notices','rust-notices','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(prepare(a.firefox_license,a.emscripten,a.wisp,a.adapter_license,a.liberation_license,a.compiled_notices,a.rust_notices,a.out),indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as error:p.error(str(error))
