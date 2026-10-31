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
 'codi-browser-source-485928f3f.tar.zst':'e3d823eeb3d042ca051f7b12c2c775a945660036c7ec3ca55bd07588e32bf968',
 'codi-browser-source-29a71d717.tar.zst':'f231dfee54279c20c6bca77988b556d6fcad7c8886792eb78c63e1f9c10b680b',
 'codi-browser-source-f4a43b30e.tar.zst':'3e090e5a9508f0ff53aae97791ff21c71dc38afb5d84bc9cc2cc54f304aeb42c',
 'codi-browser-source-ee1704dcd.tar.zst':'0ef62be5518d9cbd01543efd9bacafc22238ac6b4ca7a00719898753cfbab60a',
 'codi-browser-source-f70a64aa3.tar.zst':'1772fa4cc0e5ec205a163b9e6467ba18ffabf782e6c3a38f62316e9ad84f520d',
 'codi-browser-source-808fac040.tar.zst':'8a5d4ee98efd14272379a54665dce2c3a21fd92aff4871281ab2ff674b4a4249',
 'codi-browser-source-1573b1ffc.tar.zst':'4f376d5619d916adf902c7818bc2f8a577c2849a830db27790aa045d00f3f4a5',
 'codi-browser-source-b6b5d43e2.tar.zst':'574d6652461794e99cb746e90da5c50b168283e5e12b6cf2ab27f5851a9cb999',
 'codi-browser-source-1f6f3c159.tar.zst':'e9dd5610d383abc8619c989b69dd3e0b470c1f403bbc5f3455fd97b4608c8fb9',
 'codi-relay-source-05e70e3b0.tar.zst':'6031d72c1c102de2260a634e9e1b8b559f8cccf292b6512e9270e348f2df5ef9',
}
FIREFOX_LICENSE_SHA='e84624c9655b7d4d28a35e1539fdba8420b141ed4d12c791ab7a53e996a84701'
LIBERATION_LICENSE_SHA='93fed46019c38bbe566b479d22148e2e8a1e85ada614accb0211c37b2c61c19b'
COMPILED_NOTICES_SHA='85201fadf7d77201dc1d8c026f0340ecd6b258f6d63fe339486a200d3e377dde'
RUST_NOTICES_SHA='8c083caaa5a59ab1a01c0239ca82e378f4e9868b91f6c746a4f711ccea9444eb'
RUST_STDLIB_SHA='90567e2718bf7fd65a71a3a43c5596488e80e5f51ed02bfea6fec54458b5f3d1'
PULSE_LICENSE_SHA='44c6b5ae5ec3fe2fbc608b00e6f4896f4d2d5c7e525fcbaa3eaa3cf2f3d5a983'
RLBOX_LICENSE_SHA='891d419ba95ab39090775820f4178421dbdcd241c080003aa44f62445a48615a'
GRAPHICS_NOTICES_SHA='a447f4de3c0b4b60c6bf707811d89a9f8a5ec0e7297eb0e82573ea196b06196e'
FREETYPE_LICENSE_SHA='5a5ee54c5001bbad1cdc1a57cc3dd4c42199b2da09d39c7ee41fab002d02967f'
RUST_UPSTREAM_NOTICES_SHA='9cd8a4dddcf8e6617435d59de8051734425dc8af5cea1fde6be914404b73db92'
ENUM_MAP_NOTICES_SHA='e3caa11d93d7b92ea4bb5f5f5d2006f50304446abe1229516df5b4f8b7cb56a3'
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
def prepare(firefox_license,emscripten,wisp,adapter_license,liberation_license,compiled_notices,rust_notices,rust_stdlib,pulse_license,rlbox_license,graphics_notices,freetype_license,rust_upstream_notices,enum_map_notices,out):
    out=Path(out).absolute()
    if out.exists() or out.is_symlink() or not out.parent.is_dir():raise ValueError('New output directory required')
    if sha(firefox_license)!=FIREFOX_LICENSE_SHA:raise ValueError('Firefox notice is not from the pinned build')
    if sha(emscripten)!=SOURCES['emscripten-6.0.1-patched-source.tar.zst']:raise ValueError('Wrong Emscripten source archive')
    if sha(wisp)!=SOURCES['wisp-js-0.4.1-source.tar.zst']:raise ValueError('Wrong Wisp source archive')
    if sha(liberation_license)!=LIBERATION_LICENSE_SHA:raise ValueError('Wrong Liberation Sans font license')
    if sha(compiled_notices)!=COMPILED_NOTICES_SHA:raise ValueError('Wrong compiled component notices')
    if sha(rust_notices)!=RUST_NOTICES_SHA:raise ValueError('Wrong Rust component notices')
    if sha(rust_stdlib)!=RUST_STDLIB_SHA:raise ValueError('Wrong Rust standard library notices')
    if sha(pulse_license)!=PULSE_LICENSE_SHA:raise ValueError('Wrong Pulse Rust license')
    if sha(rlbox_license)!=RLBOX_LICENSE_SHA:raise ValueError('Wrong RLBox license')
    if sha(graphics_notices)!=GRAPHICS_NOTICES_SHA:raise ValueError('Wrong graphics component notices')
    if sha(freetype_license)!=FREETYPE_LICENSE_SHA:raise ValueError('Wrong FreeType license')
    if sha(rust_upstream_notices)!=RUST_UPSTREAM_NOTICES_SHA:raise ValueError('Wrong upstream Rust notices')
    if sha(enum_map_notices)!=ENUM_MAP_NOTICES_SHA:raise ValueError('Wrong enum-map notices')
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
    ems.append('===== Rust 1.95.0 standard library copyright notices (original HTML) =====\n'+Path(rust_stdlib).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append('===== cubeb-pulse-rs LICENSE, revision 3cf4a1af09a1748d0e184297a17132bdcc608874 =====\n'+Path(pulse_license).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append('===== Firefox third_party/rlbox/LICENSE, revision 2e1e835a5da5907e5ceef19aade58a7493f1e34d =====\n'+Path(rlbox_license).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append(Path(graphics_notices).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append('===== FreeType 2.14.2 docs/FTL.TXT =====\n'+Path(freetype_license).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append(Path(rust_upstream_notices).read_text(encoding='utf-8').rstrip()+'\n')
    ems.append(Path(enum_map_notices).read_text(encoding='utf-8').rstrip()+'\n')
    license_wisp=member(wisp,'LICENSE');adapter=Path(adapter_license).read_bytes()
    links='\n'.join('<li><a href="'+html.escape(name,quote=True)+'">'+html.escape(name)+'</a><br><code>SHA-256 '+value+'</code></li>' for name,value in SOURCES.items())
    index='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Browser licenses and source</title></head><body><main><h1>Browser licenses and source</h1>
<p>The Browser uses a locally built Firefox/Gecko WebAssembly port and the Wisp client. These notices and source snapshots correspond to the build offered by this site. Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org). All rights reserved.</p>
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
    for name in ('firefox-license','emscripten','wisp','adapter-license','liberation-license','compiled-notices','rust-notices','rust-stdlib','pulse-license','rlbox-license','graphics-notices','freetype-license','rust-upstream-notices','enum-map-notices','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(prepare(a.firefox_license,a.emscripten,a.wisp,a.adapter_license,a.liberation_license,a.compiled_notices,a.rust_notices,a.rust_stdlib,a.pulse_license,a.rlbox_license,a.graphics_notices,a.freetype_license,a.rust_upstream_notices,a.enum_map_notices,a.out),indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as error:p.error(str(error))
