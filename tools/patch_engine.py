#!/usr/bin/env python3
"""Apply a narrow, reviewable native-embedding patch to an EXACT checkout.
No sudo, no dependency installation, no engine build, no unrelated repo writes.
"""
from pathlib import Path
import argparse, hashlib, json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]

def replace_once(text,old,new,label):
    if text.count(old)!=1:
        raise RuntimeError(f'{label}: expected one upstream anchor, found {text.count(old)}. Stop and review source drift.')
    return text.replace(old,new,1)

def transformed(files,source):
    result=dict(files)
    result['gecko.js/src/embed-xul.h'] += '\n// browser.zip native navigation extension\nchar* browser_host_control(int action);\nuint32_t browser_progress_mark();\nbool browser_progress_failed_since(uint32_t mark);\n'
    path='gecko.js/src/embed-xul.cpp';s=result[path]
    s=replace_once(s,'        case 9:  // set clipboard text',
        '        case 10:  // browser.zip: native navigation/status, not page eval\n'
        '          g_evalResult = browser_host_control(g_cmd->evType);\n'
        '          ok = (g_evalResult != nullptr);\n'
        '          break;\n'
        '        case 9:  // set clipboard text','native opcode')
    s=replace_once(s,'if (g_cmd->op >= 5 && g_cmd->op <= 8) {',
        'if ((g_cmd->op >= 5 && g_cmd->op <= 8) || g_cmd->op == 10) {','native string-result route')
    result[path]=s
    path='gecko.js/src/embed-browser.cpp';s=result[path]
    s=replace_once(s,'  if (g_isChrome) {\n    // browser.xhtml is already loading',
        '  const uint32_t progressMark = browser_progress_mark();\n  if (g_isChrome) {\n    // browser.xhtml is already loading','navigation progress mark')
    s=replace_once(s,
        '  uint32_t spins = 0;\n  SpinEventLoopUntil("xul_load"_ns, [&]() -> bool {\n    PresShell* p = ds->GetPresShell();',
        '  uint32_t spins = 0;\n  bool canceled = false;\n  SpinEventLoopUntil("xul_load"_ns, [&]() -> bool {\n'
        '    constexpr int32_t kCancelNavigation = 0x43414e43;\n'
        '    if (g_cmd && __atomic_exchange_n(&g_cmd->evType, 0, __ATOMIC_SEQ_CST) == kCancelNavigation) {\n'
        '      nsCOMPtr<nsIWebNavigation> nav = do_QueryInterface(ds);\n'
        '      if (nav) nav->Stop(nsIWebNavigation::STOP_ALL);\n'
        '      canceled = true;\n      return true;\n    }\n'
        '    if (browser_progress_failed_since(progressMark)) { canceled = true; return true; }\n'
        '    PresShell* p = ds->GetPresShell();',
        'navigation cancellation check')
    s=replace_once(s,
        '  printf("xul_load: spun %u, ready\\n", spins);\n  fflush(stdout);\n\n  // Make our content window',
        '  printf("xul_load: spun %u, ready\\n", spins);\n  fflush(stdout);\n  if (canceled) return true;\n\n  // Make our content window',
        'navigation cancellation exit')
    result[path]=s
    path='gecko.js/src/embed-input.cpp';s=result[path]
    s=replace_once(s,
        'CSSPoint::FromAppUnits(before) + CSSPoint((float)dx, (float)dy),\n        ScrollMode::Smooth);',
        'CSSPoint::FromAppUnits(before) + CSSPoint((float)dx, (float)dy),\n        ScrollMode::Instant);',
        'software wheel scroll mode')
    result[path]=s
    path='gecko.js/build-lib.sh';s=result[path]
    s=replace_once(s,'for src in embed-xul embed-init embed-browser embed-paint embed-input embed-mirror; do',
        'for src in embed-xul embed-init embed-browser embed-paint embed-input embed-mirror embed-host; do','embed object list')
    s=replace_once(s,'-sEXPORTED_FUNCTIONS=_main,','-sEXPORTED_FUNCTIONS=_browser_embed_abi,_main,','ABI export')
    s=replace_once(s,'-sEXPORTED_RUNTIME_METHODS=ccall,','-sEXPORTED_RUNTIME_METHODS=PThread,ccall,','lifetime export')
    s=replace_once(s,'-sOFFSCREENCANVASES_TO_PTHREAD=#gldummy',
        "'-sOFFSCREENCANVASES_TO_PTHREAD=\"\"'",'remove page-global canvas selector')
    result[path]=s
    result['gecko.js/src/embed-host.cpp']=source
    return result

def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('checkout',type=Path);a=parser.parse_args()
    repo=a.checkout.resolve();lock=json.loads((ROOT/'upstream.lock.json').read_text())
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if head!=lock['commit']:raise RuntimeError(f'Wrong source commit: {head}; need {lock["commit"]}.')
    marker=repo/'.browser-patch.json'
    if marker.exists():
        record=json.loads(marker.read_text())
        for name,digest in record['files'].items():
            if not (repo/name).is_file() or sha((repo/name).read_text())!=digest:raise RuntimeError('Patched source changed: '+name)
        if record['localNativeSHA256']!=sha((ROOT/'native/embed-host.cpp').read_text()):raise RuntimeError('Handoff native code changed; review and repatch a clean checkout.')
        print('Exact patch already present.');return
    names=['gecko.js/src/embed-xul.h','gecko.js/src/embed-xul.cpp','gecko.js/src/embed-browser.cpp','gecko.js/src/embed-input.cpp','gecko.js/build-lib.sh']
    # Never overwrite an integrator's modifications to these files.
    for name in names:
        original=subprocess.check_output(['git','-C',str(repo),'show',f'HEAD:{name}']).decode()
        if (repo/name).read_text()!=original:raise RuntimeError('Refusing modified source: '+name)
    if (repo/'gecko.js/src/embed-host.cpp').exists():raise RuntimeError('Native extension path already exists without patch marker.')
    native=(ROOT/'native/embed-host.cpp').read_text()
    result=transformed({n:(repo/n).read_text() for n in names},native)
    # All anchors checked before any file is written.
    for name,s in result.items():(repo/name).write_text(s)
    marker.write_text(json.dumps({'upstreamCommit':head,'localNativeSHA256':sha(native),'files':{n:sha(s)for n,s in result.items()}},indent=2)+'\n')
    print('Patch written. Inspect git diff before compiling. This patch has not been compiled here.')
if __name__=='__main__':
    try:main()
    except (RuntimeError,subprocess.CalledProcessError) as e:print(f'STOP: {e}',file=sys.stderr);sys.exit(1)
