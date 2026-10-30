// Build the separately importable Wisp client using upstream's locked dependencies.
// Run only after the reviewed upstream `pnpm install --frozen-lockfile`.
const fs=require('node:fs');const path=require('node:path');const {createRequire}=require('node:module');
const [repo,out]=process.argv.slice(2);
if(!repo||!out)throw new Error('Usage: node tools/bundle_wisp.cjs CHECKOUT OUTPUT_DIRECTORY');
const pkg=path.join(path.resolve(repo),'gecko.js');
const req=createRequire(path.join(pkg,'package.json'));const rspack=req('@rspack/core');
const entry=path.join(pkg,'build','browser-wisp-entry.mjs');
fs.mkdirSync(path.dirname(entry),{recursive:true});
fs.writeFileSync(entry,"export { client } from '@mercuryworkshop/wisp-js/client';\n");
rspack({mode:'production',target:'webworker',context:pkg,entry,
  experiments:{outputModule:true},
  output:{path:path.resolve(out),filename:'wisp-client.mjs',module:true,library:{type:'module'}},
  resolve:{modules:[path.join(pkg,'node_modules'),'node_modules']},
},(error,stats)=>{
  if(error||stats.hasErrors()){console.error(error||stats.toString({all:false,errors:true}));process.exitCode=1;}
  else console.log('Wisp client bundled.');
});
