#!/usr/bin/env python3
"""Stages 1+2 on native Windows: PST -> one JSONL, one record per email, read straight from the
PST with libpff (no readpst, no mbox tree). Replaces 1-convert.sh + 2-parse.py on Windows.
Needs: pip install libpff-python (win_amd64 wheels exist). The PST is opened read-only; it may
sit inside Dropbox as long as Outlook does not have it open.

Usage: python 2-parse-pst.py maildata/<name>.pst [out.jsonl] [--limit N]
       (default out = <name>.jsonl next to the PST; written as .part then renamed)

Schema = 2-parse.py's, so q.py / 4-triage.py / 6-merge.py run unchanged:
  message_id, in_reply_to, references[], date (ISO), from_name, from_email, to[], cc[], subject,
  subject_norm, folder, body, attachments[{filename,size,type}], is_read
  + one extra field: message_class (MAPI PR_MESSAGE_CLASS, e.g. IPM.Note, IPM.Schedule.Meeting.Request).
`folder` keeps readpst's layout ("Outlook Data File/Inbox/mbox") because 4-triage.py --folder
matches on it. Calendar/Contacts/Tasks folders and non-mail item classes are skipped.
Sources: Message-ID / In-Reply-To / References from the MAPI properties (present on Sent Items
too, which carry no transport headers), falling back to the transport headers; date from the
Date: header when present (same normalisation as 2-parse.py), else the delivery / submit time
(UTC); is_read from PR_MESSAGE_FLAGS & MSGFLAG_READ; addresses from the recipient table
(PR_SMTP_ADDRESS first, so Exchange DNs resolve to real addresses).
"""
import codecs, email, email.policy, hashlib, json, mimetypes, os, re, sys, time
from datetime import timezone
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

try:
    import pypff
except ImportError:
    sys.exit('pypff missing: pip install libpff-python')

# ---- identical text handling to 2-parse.py --------------------------------------------------
RE_SUBJ = re.compile(r'^\s*((re|fwd?|fw|r|i|tr|aw|sv)\s*:\s*)+', re.I)
RE_TAIL = re.compile(
    r'(?m)^(?:-----\s*(?:Original Message|Messaggio originale)\s*-----|'
    r'Da:\s.+\nInviato:\s|From:\s.+\nSent:\s|On .+ wrote:\s*$|Il .+ ha scritto:\s*$)')

class _Text(HTMLParser):
    def __init__(s): super().__init__(); s.out = []; s.skip = 0
    def handle_starttag(s, t, a):
        if t in ('style', 'script'): s.skip += 1
        if t in ('p', 'br', 'div', 'tr', 'li'): s.out.append('\n')
    def handle_endtag(s, t):
        if t in ('style', 'script'): s.skip -= 1
    def handle_data(s, d):
        if not s.skip: s.out.append(d)
def html2text(h):
    p = _Text(); p.feed(h); return re.sub(r'\n{3,}', '\n\n', ''.join(p.out))

IT_DAYS = {'lun': 'Mon', 'mar': 'Tue', 'mer': 'Wed', 'gio': 'Thu', 'ven': 'Fri', 'sab': 'Sat', 'dom': 'Sun'}
IT_MONTHS = {'gen': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'mag': 'May', 'giu': 'Jun', 'lug': 'Jul',
             'ago': 'Aug', 'set': 'Sep', 'ott': 'Oct', 'nov': 'Nov', 'dic': 'Dec'}
def norm_date(v):
    v = (v or '').strip()
    try: return parsedate_to_datetime(v).isoformat()
    except Exception: pass
    try:
        t = re.sub(r'\s*\([A-Z]+\)\s*$', '', v).split()
        if t and t[0].rstrip(',').lower() in IT_DAYS: t[0] = IT_DAYS[t[0].rstrip(',').lower()] + ','
        if len(t) > 2 and t[2].lower() in IT_MONTHS: t[2] = IT_MONTHS[t[2].lower()]
        return parsedate_to_datetime(' '.join(t)).isoformat()
    except Exception: return ''

# ---- MAPI property access --------------------------------------------------------------------
PT_STRING8, PT_UNICODE, PT_BINARY = 0x001E, 0x001F, 0x0102
SKIP_FOLDERS = {'Calendar', 'Contacts', 'Tasks', 'PersonMetadata', 'Journal', 'Notes',
                'Search Root', 'SPAM Search Folder 2', 'Recipient Cache', 'Suggested Contacts'}
SKIP_CLASSES = ('IPM.Contact', 'IPM.Appointment', 'IPM.Task', 'IPM.StickyNote', 'IPM.Activity',
                'IPM.DistList', 'IPM.Configuration')

def props_rs(rs):
    """one record set -> {entry_type: (value_type, raw bytes)}"""
    d = {}
    for j in range(rs.number_of_entries):
        e = rs.get_entry(j)
        d[e.entry_type] = (e.value_type, e.data)
    return d

def props(item):
    """an item's record set 0 (message, attachment) -> property dict"""
    return props_rs(item.get_record_set(0)) if item.number_of_record_sets else {}

def codec_of(cpid):
    if not cpid: return 'cp1252'
    if cpid == 65001: return 'utf-8'
    if cpid == 20127: return 'ascii'
    if cpid == 1200: return 'utf-16-le'
    if 28591 <= cpid <= 28605: return f'iso-8859-{cpid - 28590}'
    try: codecs.lookup(f'cp{cpid}'); return f'cp{cpid}'
    except LookupError: return 'cp1252'

def decode(b, cpid):
    """strict with the declared codepage, then utf-8, then cp1252 lossy — ascii-declared bodies often carry utf-8."""
    for c in (codec_of(cpid), 'utf-8'):
        try: return b.decode(c)
        except (UnicodeDecodeError, LookupError): pass
    return b.decode('cp1252', 'replace')

def S(d, t, cp='cp1252'):
    v = d.get(t)
    if not v or v[1] is None: return ''
    vt, b = v
    if vt == PT_UNICODE: return b.decode('utf-16-le', 'replace').rstrip('\x00')
    if vt == PT_STRING8: return b.decode(cp, 'replace').rstrip('\x00')
    if vt == PT_BINARY: return b.decode('utf-8', 'replace').rstrip('\x00')
    return ''

def I(d, t):
    v = d.get(t)
    if not v or not v[1]: return None
    return int.from_bytes(v[1], 'little')

def mapi_dt(dt):
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else ''

# ---- one message -> record --------------------------------------------------------------------
def record(m, folder, stats):
    d = props(m)
    cls = S(d, 0x001A)
    if cls.startswith(SKIP_CLASSES):
        stats['skipped_class'] += 1; return None
    cp = codec_of(I(d, 0x3FFD))            # PR_MESSAGE_CODEPAGE for PT_STRING8 properties
    inet_cp = I(d, 0x3FDE)                 # PR_INTERNET_CPID for the HTML body

    th = None
    try: th = m.transport_headers
    except Exception: pass
    hdr = email.message_from_string(th, policy=email.policy.default) if th else None

    mid = S(d, 0x1035).strip() or (hdr.get('Message-ID', '') if hdr else '').strip()
    irt = S(d, 0x1042).strip() or (hdr.get('In-Reply-To', '') if hdr else '').strip()
    refs = (S(d, 0x1039) or (hdr.get('References', '') if hdr else '')).split()

    date = norm_date(hdr.get('Date', '')) if hdr else ''
    if not date:
        try: date = mapi_dt(m.delivery_time or m.client_submit_time or m.creation_time)
        except Exception: date = ''

    from_name = S(d, 0x0C1A, cp) or S(d, 0x0042, cp) or (m.sender_name or '')
    from_email = S(d, 0x5D01, cp) or S(d, 0x0C1F, cp)
    if '@' not in from_email: from_email = S(d, 0x5D02, cp) or from_email
    from_email = from_email.strip().lower()

    to, cc = [], []
    rec = m.recipients
    if rec is not None and rec.number_of_record_sets:
        for i in range(rec.number_of_record_sets):
            r = props_rs(rec.get_record_set(i))
            addr = (S(r, 0x39FE, cp) or S(r, 0x3003, cp)).strip().lower()
            if not addr: continue
            typ = I(r, 0x0C15)
            if typ == 2: cc.append(addr)
            elif typ in (1, None): to.append(addr)   # 3 = bcc: dropped, as readpst did
    elif hdr:
        to = [a.lower() for n, a in getaddresses(hdr.get_all('To', [])) if a]
        cc = [a.lower() for n, a in getaddresses(hdr.get_all('Cc', [])) if a]

    subj = m.subject or S(d, 0x0037, cp).lstrip('\x00\x01\x02\x03\x04\x05\x06\x07\x08')
    subj = str(subj or '')

    plain = S(d, 0x1000, cp) if 0x1000 in d else ''
    html = ''
    if not plain.strip() and 0x1013 in d and d[0x1013][1]:
        vt, b = d[0x1013]
        html = decode(b, inet_cp) if vt == PT_BINARY else S(d, 0x1013, cp)
    body = plain if plain.strip() else (html2text(html) if html else '')
    if not body: stats['no_body'] += 1
    body = body.replace('\r\n', '\n')
    t = RE_TAIL.search(body)
    if t and t.start() > 0: body = body[:t.start()]
    body = body.strip()

    atts = []
    for k in range(m.number_of_attachments):
        try:
            a = m.get_attachment(k); ad = props(a)
            fn = a.long_filename or S(ad, 0x3707, cp) or S(ad, 0x3704, cp) or ''
            method = I(ad, 0x3705)
            typ = S(ad, 0x370E, cp) or mimetypes.guess_type(fn)[0] or \
                  ('message/rfc822' if method == 5 else 'application/octet-stream')
            try: size = a.size
            except Exception: size = 0
            atts.append({'filename': fn, 'size': size, 'type': typ})
        except Exception as e:
            stats['att_errors'] += 1

    if not mid:
        mid = '<synth-' + hashlib.sha1((date + from_email + subj).encode()).hexdigest()[:16] + '>'
    flags = I(d, 0x0E07) or 0
    return {'message_id': mid, 'in_reply_to': irt, 'references': refs, 'date': date,
            'from_name': from_name, 'from_email': from_email, 'to': to, 'cc': cc,
            'subject': subj, 'subject_norm': RE_SUBJ.sub('', subj).strip().lower(),
            'folder': folder, 'body': body, 'attachments': atts,
            'is_read': bool(flags & 1), 'message_class': cls}

# ---- walk ---------------------------------------------------------------------------------------
def walk(fo, path):
    name = fo.name or ''
    if name in SKIP_FOLDERS: return
    if name == 'Top of Outlook data file': name = 'Outlook Data File'   # readpst's name for the root
    p = f'{path}/{name}' if path and name else (name or path)
    if fo.number_of_sub_messages: yield fo, p
    for i in range(fo.number_of_sub_folders):
        yield from walk(fo.get_sub_folder(i), p)

def main(pst, out, limit):
    t0 = time.time(); stats = {'written': 0, 'dup': 0, 'errors': 0, 'skipped_class': 0, 'no_body': 0, 'att_errors': 0}
    per_folder = {}; per_class = {}; seen = set()
    f = pypff.file(); f.open(str(pst))
    print(f'opened {pst} ({os.path.getsize(pst) / 2**30:.1f} GB) in {time.time() - t0:.0f} s', file=sys.stderr)
    part = Path(str(out) + '.part'); n_seen = 0
    with part.open('w', encoding='utf-8') as fo:
        for folder, fpath in walk(f.get_root_folder(), ''):
            fname = f'{fpath}/mbox'; nf = 0
            for i in range(folder.number_of_sub_messages):
                n_seen += 1
                try:
                    m = folder.get_sub_message(i)
                    r = record(m, fname, stats)
                    if r is None: continue
                    if r['message_id'] in seen: stats['dup'] += 1; continue
                    seen.add(r['message_id'])
                    fo.write(json.dumps(r, ensure_ascii=False) + '\n')
                    stats['written'] += 1; nf += 1
                    per_class[r['message_class']] = per_class.get(r['message_class'], 0) + 1
                except Exception as e:
                    stats['errors'] += 1
                    if stats['errors'] <= 30: print(f'!! {fname} #{i}: {type(e).__name__}: {e}', file=sys.stderr)
                if n_seen % 2000 == 0:
                    el = time.time() - t0
                    print(f'  {n_seen} items, {stats["written"]} written, {el:.0f} s ({n_seen / el:.0f}/s)', file=sys.stderr)
                if limit and n_seen >= limit: break
            per_folder[fname] = nf
            if limit and n_seen >= limit: break
    f.close()
    os.replace(part, out)
    el = time.time() - t0
    print(f'{stats["written"]} emails -> {out}   ({el / 60:.1f} min, {os.path.getsize(out) / 2**20:.0f} MB)')
    print('stats:', stats)
    print('classes:', dict(sorted(per_class.items(), key=lambda kv: -kv[1])))
    for k, v in per_folder.items(): print(f'{v:7d}  {k}')

if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    limit = int(a[a.index('--limit') + 1]) if '--limit' in a else 0
    a = [x for x in a if x != '--limit' and not x.isdigit()]
    pst = Path(a[0]); out = Path(a[1]) if len(a) > 1 else pst.with_suffix('.jsonl')
    main(pst, out, limit)
