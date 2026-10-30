#!/usr/bin/env python3
"""Loopback-only static development server. NO proxy, no auth, no remote browser.
Does not modify the real desktop server or install security-header middleware there.
"""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote,urlsplit
import argparse
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**k):super().__init__(*a,directory=str(ROOT),**k)
    def translate_path(self,path):
        raw=unquote(urlsplit(path).path)
        if any(p.startswith('.') for p in raw.split('/') if p):return str(ROOT/'__not_found__')
        target=Path(super().translate_path(path)).resolve()
        if ROOT not in target.parents and target!=ROOT:return str(ROOT/'__not_found__')
        return str(target)
    def end_headers(self):
        self.send_header('Cross-Origin-Opener-Policy','same-origin')
        self.send_header('Cross-Origin-Embedder-Policy','require-corp')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=(), usb=(), serial=(), hid=()')
        # No public relay by default. An integrator must add an exact approved WSS
        # origin if they enable networking. 'self' permits same-origin WSS in modern browsers.
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' blob: 'wasm-unsafe-eval'; worker-src 'self' blob:; connect-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'")
        super().end_headers()
    def guess_type(self,path):
        if path.endswith(('.mjs','.js')):return 'text/javascript'
        if path.endswith('.wasm'):return 'application/wasm'
        return super().guess_type(path)
def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8087);a=p.parse_args()
    print(f'Development only: http://127.0.0.1:{a.port}/demo/ (no Wisp server)',flush=True)
    with ThreadingHTTPServer(('127.0.0.1',a.port),Handler)as server:
        try:server.serve_forever()
        except KeyboardInterrupt:pass
if __name__=='__main__':main()
