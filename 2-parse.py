#!/usr/bin/env python3
"""Stage 2: mbox tree (from 1-convert.sh) -> one JSONL, one record per email.
Stdlib only. Usage: ./2-parse.py workdata/<name>  -> workdata/<name>.jsonl
Fields: message_id, in_reply_to, references[], date (ISO), from_name, from_email,
to[], cc[], subject, subject_norm, folder, body, attachments[{filename,size,type}], is_read (readpst 'Status: RO').
"""
import email, email.policy, hashlib, json, mailbox, re, sys
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

RE_SUBJ = re.compile(r'^\s*((re|fwd?|fw|r|i|tr|aw|sv)\s*:\s*)+', re.I)
# Conservative quoted-tail stripper: cut only at unambiguous reply markers.
RE_TAIL = re.compile(
    r'(?m)^(?:-----\s*(?:Original Message|Messaggio originale)\s*-----|'
    r'Da:\s.+\nInviato:\s|From:\s.+\nSent:\s|On .+ wrote:\s*$|Il .+ ha scritto:\s*$)')

class _Text(HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.skip=0
    def handle_starttag(s,t,a):
        if t in ('style','script'): s.skip+=1
        if t in ('p','br','div','tr','li'): s.out.append('\n')
    def handle_endtag(s,t):
        if t in ('style','script'): s.skip-=1
    def handle_data(s,d):
        if not s.skip: s.out.append(d)
def html2text(h):
    p=_Text(); p.feed(h); return re.sub(r'\n{3,}','\n\n',''.join(p.out))

def body_of(msg):
    plain=html=None; atts=[]
    for part in msg.walk():
        if part.is_multipart(): continue
        fn=part.get_filename(); disp=(part.get('Content-Disposition') or '')
        if fn or 'attachment' in disp:
            pay=part.get_payload(decode=True) or b''
            atts.append({'filename':fn or '', 'size':len(pay), 'type':part.get_content_type()})
            continue
        ct=part.get_content_type()
        try: txt=part.get_content()
        except Exception:
            pay=part.get_payload(decode=True) or b''
            txt=pay.decode(part.get_content_charset() or 'utf-8','replace')
        if ct=='text/plain' and plain is None: plain=txt
        elif ct=='text/html' and html is None: html=txt
    body=plain if plain and plain.strip() else (html2text(html) if html else '')
    body=body.replace('\r\n','\n')
    m=RE_TAIL.search(body)
    if m and m.start()>0: body=body[:m.start()]
    return body.strip(), atts

IT_DAYS={'lun':'Mon','mar':'Tue','mer':'Wed','gio':'Thu','ven':'Fri','sab':'Sat','dom':'Sun'}
IT_MONTHS={'gen':'Jan','feb':'Feb','mar':'Mar','apr':'Apr','mag':'May','giu':'Jun','lug':'Jul',
           'ago':'Aug','set':'Sep','ott':'Oct','nov':'Nov','dic':'Dec'}
def norm_date(v):
    """RFC-2822 date -> ISO. Fallback: Italian-localized day/month names (some IT servers emit 'Sab, 22 Ago 2026')."""
    v=(v or '').strip()
    try: return parsedate_to_datetime(v).isoformat()
    except Exception: pass
    try:
        t=re.sub(r'\s*\([A-Z]+\)\s*$','',v).split()
        if t and t[0].rstrip(',').lower() in IT_DAYS: t[0]=IT_DAYS[t[0].rstrip(',').lower()]+','
        if len(t)>2 and t[2].lower() in IT_MONTHS: t[2]=IT_MONTHS[t[2].lower()]
        return parsedate_to_datetime(' '.join(t)).isoformat()
    except Exception: return ''

def addrs(msg,h):
    return [a.lower() for n,a in getaddresses(msg.get_all(h,[])) if a]

def main(root):
    root=Path(root); out=root.with_suffix('.jsonl'); n=0; seen=set()
    with out.open('w',encoding='utf-8') as fo:
        for f in sorted(p for p in root.rglob('*') if p.is_file()):
            folder=str(f.relative_to(root))
            for msg in mailbox.mbox(str(f),factory=lambda fp: email.message_from_binary_file(fp,policy=email.policy.default)):
                try:
                    body,atts=body_of(msg)
                    mid=(msg.get('Message-ID') or '').strip()
                    if not mid:  # synthesize a stable id
                        mid='<synth-'+hashlib.sha1((msg.get('Date','')+msg.get('From','')+msg.get('Subject','')).encode()).hexdigest()[:16]+'>'
                    if mid in seen: continue
                    seen.add(mid)
                    fn,fe=parseaddr(msg.get('From',''))
                    subj=str(msg.get('Subject','') or '')
                    rec={'message_id':mid,'in_reply_to':(msg.get('In-Reply-To') or '').strip(),
                         'references':(msg.get('References') or '').split(),
                         'date':norm_date(msg.get('Date','')),'from_name':fn,'from_email':fe.lower(),
                         'to':addrs(msg,'To'),'cc':addrs(msg,'Cc'),'subject':subj,
                         'subject_norm':RE_SUBJ.sub('',subj).strip().lower(),'folder':folder,
                         'body':body,'attachments':atts,
                         'is_read':'R' in (msg.get('Status') or '')}
                    fo.write(json.dumps(rec,ensure_ascii=False)+'\n'); n+=1
                except Exception as e:
                    print(f'!! {f}: {e}',file=sys.stderr)
    print(f'{n} emails -> {out}')

if __name__=='__main__': main(sys.argv[1])
