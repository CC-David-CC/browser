"""Request-scoped device reports; the caller supplies authenticated principals.

No listener or background collection. Operator authorization and transport
must be provided by the host. Reports are only accepted after an explicit
administrator request and remain private service state until removed.
"""
import json
import os
import secrets
import sqlite3
import stat
import time
from pathlib import Path
from .report import verify_report,aggregate_reports

class ReportRequests:
    def __init__(self,path,*,origin,admin_subjects,clock=time.time):
        self.path=Path(path);self.origin=origin;self.admins=frozenset(admin_subjects);self.clock=clock
        if not self.path.is_absolute() or not self.admins or any(not isinstance(x,str) or not x.startswith('user:') for x in self.admins):raise ValueError('Private database and explicit administrators required')
        parent=self.path.parent
        if not parent.is_dir() or parent.is_symlink() or parent.stat().st_uid!=os.geteuid() or stat.S_IMODE(parent.stat().st_mode)&0o077:raise ValueError('Private service-owned directory required')
        fd=os.open(self.path,os.O_RDWR|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_uid!=os.geteuid() or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('Private service-owned database required')
        finally:os.close(fd)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, created INTEGER NOT NULL, expires INTEGER NOT NULL, owner TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS reports (request_id TEXT NOT NULL, subject TEXT NOT NULL, device TEXT NOT NULL, report TEXT NOT NULL, PRIMARY KEY(request_id,subject,device))')
    def db(self):return sqlite3.connect(self.path,timeout=5)
    def principal(self,principal):
        if not principal or principal.kind!='registered' or not isinstance(principal.sub,str) or not principal.sub.startswith('user:') or principal.deadline<=self.clock():raise PermissionError('Live registered account required')
        return principal.sub
    def admin(self,principal):
        sub=self.principal(principal)
        if sub not in self.admins:raise PermissionError('Administrator required')
        return sub
    def role(self,principal):return {'admin':self.principal(principal) in self.admins}
    def list_admin(self,principal):
        self.admin(principal)
        with self.db() as db:
            return [{'id':row[0],'created':row[1],'expires':row[2]} for row in db.execute('SELECT id,created,expires FROM requests ORDER BY created DESC,id DESC LIMIT 100')]
    def create(self,principal,seconds=3600):
        owner=self.admin(principal)
        if type(seconds) is not int or not 60<=seconds<=86400:raise ValueError('Request duration must be 60–86400 seconds')
        now=int(self.clock());token=secrets.token_urlsafe(24)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT count(*) FROM requests WHERE expires>?',(now,)).fetchone()[0]>=16:raise ValueError('Too many active report requests')
            db.execute('INSERT INTO requests VALUES(?,?,?,?)',(token,now,now+seconds,owner));db.commit()
        return {'id':token,'created':now,'expires':now+seconds}
    def pending(self,principal):
        self.principal(principal)
        with self.db() as db:return [{'id':r[0],'created':r[1],'expires':r[2]} for r in db.execute('SELECT id,created,expires FROM requests WHERE expires>? ORDER BY created',(int(self.clock()),))]
    def submit(self,principal,request_id,report):
        subject=self.principal(principal)
        if not isinstance(request_id,str) or len(request_id)>64:raise ValueError('Invalid request ID')
        raw=json.dumps(report,separators=(',',':'),ensure_ascii=False)
        if len(raw.encode())>12*1024*1024:raise ValueError('Report exceeds current transfer limit')
        checked=verify_report(report,subject=subject,origin=self.origin)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');request=db.execute('SELECT expires FROM requests WHERE id=?',(request_id,)).fetchone()
            if not request or request[0]<=int(self.clock()):raise PermissionError('No active request')
            old=db.execute('SELECT report FROM reports WHERE request_id=? AND subject=? AND device=?',(request_id,subject,checked['deviceKey'])).fetchone()
            if old:
                previous=json.loads(old[0]);common=min(len(previous['events']),len(checked['events']))
                if any(previous['events'][i]['hash']!=checked['events'][i]['hash'] for i in range(common)) or len(checked['events'])<len(previous['events']):raise ValueError('Conflicting or truncated device history')
            db.execute('INSERT OR REPLACE INTO reports VALUES(?,?,?,?)',(request_id,subject,checked['deviceKey'],json.dumps(checked,separators=(',',':'))));db.commit()
        return {'device':checked['deviceKey'],'head':checked['head'],'events':len(checked['events'])}
    def summary(self,principal,request_id,subject=None):
        self.admin(principal)
        sql='SELECT report FROM reports WHERE request_id=?';args=[request_id]
        if subject is not None:sql+=' AND subject=?';args.append(subject)
        with self.db() as db:
            cursor=db.execute(sql,args);count=0
            def reports():
                nonlocal count
                for row in cursor:count+=1;yield json.loads(row[0])
            domains=aggregate_reports(reports())
        return {'devices':count,'domains':domains}
    def remove(self,principal,request_id):
        self.admin(principal)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE');db.execute('DELETE FROM reports WHERE request_id=?',(request_id,));db.execute('DELETE FROM requests WHERE id=?',(request_id,));db.commit()
