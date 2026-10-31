"""Patch-transform tests on synthetic anchors. NOT an upstream build test."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('patch_engine',ROOT/'tools/patch_engine.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

def files():
    return {'gecko.js/src/embed-xul.h':'// header\n',
            'gecko.js/src/embed-xul.cpp':'        case 9:  // set clipboard text\nif (g_cmd->op >= 5 && g_cmd->op <= 8) {\n',
            'gecko.js/src/embed-browser.cpp':'  if (g_isChrome) {\n    // browser.xhtml is already loading\n  uint32_t spins = 0;\n  SpinEventLoopUntil("xul_load"_ns, [&]() -> bool {\n    PresShell* p = ds->GetPresShell();\n  printf("xul_load: spun %u, ready\\n", spins);\n  fflush(stdout);\n\n  // Make our content window',
            'gecko.js/build-lib.sh':'for src in embed-xul embed-init embed-browser embed-paint embed-input embed-mirror; do\n-sEXPORTED_FUNCTIONS=_main,\n-sEXPORTED_RUNTIME_METHODS=ccall,\n-sOFFSCREENCANVASES_TO_PTHREAD=#gldummy\n'}
class PatchTests(unittest.TestCase):
    def test_navigation_patch(self):
        out=patch.transformed(files(),'native');self.assertIn('case 10:',out['gecko.js/src/embed-xul.cpp']);self.assertIn('|| g_cmd->op == 10',out['gecko.js/src/embed-xul.cpp'])
    def test_lifetime_and_abi_exports(self):
        out=patch.transformed(files(),'native')['gecko.js/build-lib.sh'];self.assertIn('=PThread,ccall',out);self.assertIn('=_browser_embed_abi,_main',out)
    def test_no_page_global_canvas_transfer(self):
        out=patch.transformed(files(),'native')['gecko.js/build-lib.sh'];self.assertNotIn('#gldummy',out);self.assertIn('OFFSCREENCANVASES_TO_PTHREAD=""',out)
    def test_native_object_added(self):
        out=patch.transformed(files(),'native');self.assertIn('embed-mirror embed-host;',out['gecko.js/build-lib.sh']);self.assertEqual(out['gecko.js/src/embed-host.cpp'],'native')
    def test_navigation_cancellation_is_checked_and_exits_load(self):
        out=patch.transformed(files(),'native')['gecko.js/src/embed-browser.cpp'];self.assertIn('__atomic_exchange_n(&g_cmd->evType',out);self.assertIn('nav->Stop(nsIWebNavigation::STOP_ALL)',out);self.assertIn('if (canceled) return true;',out)
    def test_failed_load_ends_native_wait(self):
        out=patch.transformed(files(),'native')['gecko.js/src/embed-browser.cpp'];self.assertIn('browser_progress_mark()',out);self.assertIn('browser_progress_failed_since(progressMark)',out)
    def test_missing_cancel_anchor_rejected(self):
        f=files();f['gecko.js/src/embed-browser.cpp']='changed';self.assertRaises(RuntimeError,patch.transformed,f,'native')
    def test_missing_anchor_rejected(self):
        f=files();f['gecko.js/src/embed-xul.cpp']='changed';self.assertRaises(RuntimeError,patch.transformed,f,'native')
    def test_duplicate_anchor_rejected(self):
        f=files();f['gecko.js/build-lib.sh']*=2;self.assertRaises(RuntimeError,patch.transformed,f,'native')
    def test_transform_does_not_mutate_input(self):
        f=files();before=f.copy();patch.transformed(f,'native');self.assertEqual(f,before)
if __name__=='__main__':unittest.main()
