export const styles = `
:host{display:flex;flex-direction:column;height:100%;min-height:0;font:14px system-ui;color:#dce6f3;background:#111827}
*{box-sizing:border-box}button,input{font:inherit}button{border:1px solid #53627a;background:#243246;color:inherit;border-radius:5px;padding:6px 10px;cursor:pointer}
button:disabled{opacity:.45;cursor:default}button:focus-visible,input:focus-visible,canvas:focus-visible{outline:2px solid #7dd3fc;outline-offset:1px}
.toolbar{display:flex;gap:6px;padding:8px;align-items:center;flex-wrap:wrap;border-bottom:1px solid #374151}
form{display:flex;gap:6px;flex:1;min-width:200px}input[aria-label="Website address"]{width:100%;min-width:100px;background:#0b1322;border:1px solid #53627a;color:inherit;border-radius:5px;padding:7px}
.stage{flex:1;min-height:160px;position:relative;overflow:hidden;background:white;display:flex;align-items:flex-start;justify-content:flex-start}
canvas{display:block;width:100%;height:100%;object-fit:fill;touch-action:none}
.info{position:absolute;inset:0;background:#111827;padding:24px;overflow:auto;white-space:pre-wrap;line-height:1.6}
.info[hidden]{display:none}.status{padding:6px 10px;background:#172033;white-space:pre-wrap;overflow-wrap:anywhere}
.details{max-height:160px;overflow:auto;background:#0b1322;margin:0;padding:8px;white-space:pre-wrap;font:11px ui-monospace,monospace}
.warn{display:block;padding:5px 10px;font-size:12px;color:#fbbf24;background:#1f2937}
`;
