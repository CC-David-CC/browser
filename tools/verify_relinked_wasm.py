#!/usr/bin/env python3
"""Compare the pinned retained Gecko library and its isolated mapped relink."""
import argparse,hashlib,json
from pathlib import Path
ORIGINAL='e600c6226797fb32a7ec1501de5e541a78aed7540bb3fa2a04ea9ebb854e185b'
RELINK='48fdea509ed523c5296d3a677f9c73eec4798b27d64ac02545b02717246b5975'
def leb(f):
 value=0
 for i in range(10):
  b=f.read(1)
  if not b:raise ValueError('Truncated LEB')
  value|=(b[0]&127)<<(7*i)
  if b[0]<128:return value
 raise ValueError('Oversized LEB')
def digest_range(f,size):
 h=hashlib.sha256()
 while size:
  chunk=f.read(min(size,4*1024*1024))
  if not chunk:raise ValueError('Truncated section')
  h.update(chunk);size-=len(chunk)
 return h.hexdigest()
def sections(path):
 result=[];size=path.stat().st_size
 with path.open('rb') as f:
  if f.read(8)!=b'\0asm\x01\0\0\0':raise ValueError('Invalid WASM')
  while f.tell()<size:
   k=f.read(1)[0];n=leb(f);start=f.tell();end=start+n
   if end>size:raise ValueError('Truncated section')
   name='';subsections=None
   if k==0:
    length=leb(f)
    if length>1024 or f.tell()+length>end:raise ValueError('Invalid custom section')
    name=f.read(length).decode('utf-8','strict')
    if name=='name':
     subsections=[]
     while f.tell()<end:
      kind=f.read(1)[0];length=leb(f)
      if f.tell()+length>end:raise ValueError('Truncated name subsection')
      subsections.append((kind,length,digest_range(f,length)))
   f.seek(start);result.append((k,name,n,digest_range(f,n),subsections))
 return result
def sha(path):
 with path.open('rb') as f:return digest_range(f,path.stat().st_size)
def verify(original,relink):
 if sha(original)!=ORIGINAL or sha(relink)!=RELINK:raise ValueError('Unexpected library hash')
 a,b=sections(original),sections(relink)
 if len(a)!=len(b):raise ValueError('Section count differs')
 differences=[]
 for i,(x,y) in enumerate(zip(a,b)):
  if x==y:continue
  if x[:2]!=(0,'name') or y[:2]!=(0,'name'):
   if x[:2]!=(0,'build_id') or y[:2]!=(0,'build_id'):raise ValueError('Non-metadata section differs')
   differences.append('build_id');continue
  xs,ys=x[4],y[4]
  if len(xs)!=len(ys) or any(u!=v and not (u[0]==v[0]==0) for u,v in zip(xs,ys)):raise ValueError('Name content beyond module name differs')
  differences.append('module_name')
 if sorted(differences)!=['build_id','module_name']:raise ValueError('Unexpected metadata differences')
 return {'originalSHA256':ORIGINAL,'relinkSHA256':RELINK,'sections':len(a),'differences':differences,'scope':'intermediate relocatable library, not final Browser WASM'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original',type=Path,required=True);p.add_argument('--relink',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.original,a.relink),sort_keys=True))
