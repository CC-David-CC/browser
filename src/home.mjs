// Guest page source. This string is never inserted into the host DOM.
export const HOME_HTML = `<!doctype html><meta charset="utf-8"><title>Independent browser</title>
<style>
body{font:18px system-ui;background:#f4f7fa;color:#172538;margin:0;padding:36px;line-height:1.5}
main{max-width:800px;margin:auto}h1{font-size:38px}code{background:#dce8ee;padding:2px 5px}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
section{background:white;padding:20px;border-radius:10px}button,input{font:inherit;padding:9px}
@media(max-width:600px){.cards{grid-template-columns:1fr}}
</style><main><h1>A browser inside your desktop.</h1>
<p>This document belongs to <b>Gecko</b>. Its HTML, CSS, DOM and JavaScript are not the outer page's.</p>
<div class="cards"><section><h2>JavaScript</h2><button id="count">Clicks: 0</button>
<p id="test">Script has not run.</p></section><section><h2>Ordinary web content</h2>
<input placeholder="Try typing here"><p>No mount(host) export is needed by this page.</p></section></div>
<p>Open an HTML file to test offline. Public websites require the integrator's Wisp relay.</p>
<p><strong>Research integration — not a security-reviewed browser.</strong></p></main>
<script>
let n=0;document.getElementById('count').onclick=()=>document.getElementById('count').textContent='Clicks: '+ ++n;
Promise.resolve([1,2,3].map(x=>x*x).join(', ')).then(x=>document.getElementById('test').textContent='Guest JS: '+x);
<\/script>`;
