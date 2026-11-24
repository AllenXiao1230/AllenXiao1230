"""Refresh the exact Chinese font subset from Google Fonts, only when copy changes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]


def main():
    copy=(ROOT/'locales.json').read_text('utf-8')+(ROOT/'scripts/render_cards.py').read_text('utf-8')+(ROOT/'profile.json').read_text('utf-8')
    chars=''.join(sorted(set(c for c in copy if ord(c)>127)))
    digest=hashlib.sha256(chars.encode('utf-8')).hexdigest()
    font=ROOT/'fonts/han.woff2'
    stamp=ROOT/'fonts/han.sha256'
    if font.exists() and stamp.exists() and stamp.read_text().strip()==digest:
        print('Chinese glyph set unchanged; using bundled font.')
        return
    query=urlencode({'family':'Noto Sans TC:wght@400','text':chars})
    ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    request=Request('https://fonts.googleapis.com/css2?'+query,headers={'User-Agent':ua})
    with urlopen(request,timeout=40) as response:css=response.read().decode('utf-8')
    match=re.search(r'url\((https://fonts\.gstatic\.com/[^)]+)\)\s+format\([\'"]woff2[\'"]\)',css)
    if not match:raise ValueError('Google Fonts did not return a WOFF2 subset; keeping existing font.')
    with urlopen(match.group(1),timeout=40) as response:content=response.read()
    if content[:4]!=b'wOF2':raise ValueError('Unexpected font format; keeping existing font.')
    temp=font.with_suffix('.tmp');temp.write_bytes(content);temp.replace(font)
    stamp.write_text(digest+'\n','utf-8')
    print(f'Updated Chinese font subset: {len(chars)} characters, {len(content)} bytes.')


if __name__=='__main__':main()
