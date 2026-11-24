"""Render self-contained animated SVGs and a local preview using only stdlib."""
from __future__ import annotations

import argparse
import base64
import calendar
import html
import json
import os
import re
import textwrap
import unicodedata
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C = {"paper": "#F5F2EB", "white": "#FFFEFA", "ink": "#252721", "muted": "#64665D", "line": "#DDDCD3", "blue": "#254BDD", "red": "#BD3C2D", "yellow": "#F0C84B"}
HEAT = ["#E4E7EC", "#C1CEF9", "#89A3F3", "#4D74E7", C["blue"]]
LANG = "en"
TRANSLATIONS = json.loads((ROOT / "locales.json").read_text("utf-8"))


def t(value):
    value = str(value)
    if LANG == "en": return value
    translated = TRANSLATIONS[LANG].get(value)
    if translated is not None: return translated
    match = re.fullmatch(r"([\d,]+) contributions", value)
    if match: return match.group(1) + " 次貢獻"
    return value


def wrap_copy(value, width):
    if not re.search(r"[\u3000-\u9fff]", value):return textwrap.wrap(value,width=width)
    lines=[]; line=""; units=0
    for ch in value:
        step=2 if unicodedata.east_asian_width(ch) in ("W","F") else 1
        if units+step>width:lines.append(line.rstrip());line="";units=0
        line+=ch;units+=step
    if line:lines.append(line.rstrip())
    return lines


def esc(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, size=16, fill=None, family="sans", weight=400, **attrs):
    value=t(value)
    family = "ProfileSerif" if family == "serif" and not re.search(r"[\u3000-\u9fff]",value) else "ProfileSans, ProfileHan"
    extra = " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items())
    return f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill or C["ink"]}" {extra}>{esc(value)}</text>'


def rect(x, y, w, h, fill, rx=0, **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{esc(v)}"' for k, v in attrs.items())
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {extra}/>'


def rule(x1, y, x2):
    return f'<path d="M{x1} {y}H{x2}" stroke="{C["line"]}"/>'


def arrow(x, y, color, scale=1):
    return f'<g transform="translate({x} {y}) scale({scale})" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M0 13 13 0M0 0h13v13"/></g>'


def icon(kind, x, y, color, scale=1):
    paths = {
        "camera": '<path d="M3 11h8l4-6h15l4 6h8v29H3Z"/><circle cx="22.5" cy="25" r="9"/><path d="M35 17h2"/>',
        "frame": '<rect x="3" y="3" width="37" height="37" rx="1"/><path d="M10 16h23v12H10Z"/><path d="M15 3v5m12-5v5M15 35v5m12-5v5"/>',
        "browser": '<rect x="3" y="5" width="38" height="33" rx="2"/><path d="M3 14h38M9 10h1m5 0h1m5 0h1M14 22l-5 5 5 5m15-10 5 5-5 5m-5-12-5 14"/>',
        "motion": '<path d="M4 4v10m0-10h10M40 4H30m10 0v10M4 40V30m0 10h10m26 0H30m10 0V30"/><circle cx="22" cy="22" r="9"/><path d="M17 22h10M22 17v10"/>'
    }
    return f'<g transform="translate({x} {y}) scale({scale})" fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>'


def font_css(include_han=False):
    css = []
    for file, family, weight in [("serif", "ProfileSerif", 400), ("sans", "ProfileSans", 400), ("sans-medium", "ProfileSans", 600)]:
        content = base64.b64encode((ROOT / "fonts" / f"{file}.woff2").read_bytes()).decode()
        css.append(f"@font-face{{font-family:{family};font-weight:{weight};src:url(data:font/woff2;base64,{content}) format('woff2')}}")
    if include_han:
        content=base64.b64encode((ROOT/'fonts/han.woff2').read_bytes()).decode()
        css.append(f"@font-face{{font-family:ProfileHan;font-weight:400;src:url(data:font/woff2;base64,{content}) format('woff2')}}")
    mono=ROOT/'fonts/mono.woff2'
    if mono.exists():
        content=base64.b64encode(mono.read_bytes()).decode()
        css.append(f"@font-face{{font-family:ProfileMono;font-weight:600;src:url(data:font/woff2;base64,{content}) format('woff2')}}")
    return "".join(css)


def svg(w, h, body, title, static=False, bg="paper"):
    motion = "" if static else """
      @keyframes printin{from{opacity:.4;transform:translateY(9px)}to{opacity:1;transform:translateY(0)}}
      @keyframes grow{from{transform:scaleY(.02)}to{transform:scaleY(1)}}
      @keyframes press{from{opacity:.45;transform:scale(.7)}to{opacity:1;transform:scale(1)}}
      @keyframes turn{from{transform:rotate(-22deg)}to{transform:rotate(0deg)}}
      @keyframes asciiPrint{from{opacity:0}to{opacity:1}}
      .print{animation:printin .85s cubic-bezier(.16,1,.3,1) both;animation-delay:var(--delay,0s)}
      .cell{transform-box:fill-box;transform-origin:center;animation:press .6s cubic-bezier(.16,1,.3,1) both;animation-delay:var(--delay,.25s)}
      .bar{transform-box:fill-box;transform-origin:center bottom;animation:grow .85s cubic-bezier(.16,1,.3,1) both;animation-delay:var(--delay,.6s)}
      .turn{transform-box:fill-box;transform-origin:center;animation:turn 1.5s cubic-bezier(.16,1,.3,1) both}
      .ascii-row{animation:asciiPrint .22s steps(2,end) both;animation-delay:calc(.15s + var(--row,0)*.014s)}
      @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
    """
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title"><title id="title">{esc(title)}</title><style>{FONT_CSS}{motion}</style>{rect(0,0,w,h,C[bg],14)}{body}</svg>'''


def hero(config, mobile, static):
    w, h = (420, 460) if mobile else (880, 412)
    x = 28 if mobile else 42
    s = 82 if mobile else 116
    a, b = (104, 218) if mobile else (126, 238)
    body = '<g class="print">' + text(x,a,config["name"],s,family="serif") + '</g>'
    body += '<g class="print" style="--delay:.12s">' + text(x,b,config["headline"],74 if mobile else s,C["blue"],family="serif") + '</g>'
    if config.get('portrait_ascii'):
        source=(ROOT/config['portrait_ascii']).resolve()
        if not source.is_relative_to(ROOT):raise ValueError('ASCII data must be inside the profile folder.')
        portrait=json.loads(source.read_text('utf-8'))['mobile' if mobile else 'desktop']
        px,py,pw,ph=(252,18,140,140) if mobile else (555,16,294,340)
        line_height=ph/len(portrait['rows'])
        body+='<g class="ascii-portrait" aria-label="ASCII portrait of Allen" fill="#161812">'
        for index,line in enumerate(portrait['rows']):
            if not line.strip():continue
            body+=f'<text class="ascii-row" style="--row:{index}" x="{px}" y="{py+(index+.82)*line_height:.3f}" font-family="ProfileMono,monospace" font-weight="600" font-size="{line_height:.3f}" textLength="{pw}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{esc(line)}</text>'
        body+='</g>'
    elif config.get('portrait'):
        portrait=(ROOT/config['portrait']).resolve()
        if not portrait.is_relative_to(ROOT):raise ValueError('Portrait must be inside the profile folder.')
        encoded=base64.b64encode(portrait.read_bytes()).decode()
        px,py,pw,ph=(282,22,110,110) if mobile else (614,30,226,286)
        crop='270 330 430 430' if mobile else '200 270 730 924'
        body+=f'<defs><clipPath id="portrait-clip"><rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="14"/></clipPath></defs>'
        body+=f'<g class="print" style="--delay:.2s" clip-path="url(#portrait-clip)"><svg x="{px}" y="{py}" width="{pw}" height="{ph}" viewBox="{crop}" preserveAspectRatio="xMidYMid slice"><image width="1045" height="1567" href="data:image/jpeg;base64,{encoded}"/></svg></g>'
    elif not mobile:
        spokes = ''.join(f'<rect x="-11" y="-83" width="22" height="166" rx="2" transform="rotate({angle})"/>' for angle in (0,45,90,135))
        body += f'<g transform="translate(740 154)"><g class="turn" fill="{C["blue"]}">{spokes}</g><circle cx="0" cy="0" r="16" fill="{C["paper"]}"/></g>'
        body += rect(793,258,18,18,C["yellow"],2) + f'<circle cx="828" cy="267" r="7" fill="{C["red"]}"/>'
    else:
        body += f'<circle cx="350" cy="68" r="9" fill="{C["red"]}"/>' + rect(367,87,17,17,C["yellow"],1)
    ty = 278 if mobile else 285
    for i,line in enumerate(config["tagline"]):
        body += text(x,ty+i*26,line,18 if mobile else 20)
    body += text(x,344 if mobile else 382,config["skills"],11 if mobile else 13,C["muted"])
    if mobile:
        body += rule(x,391,w-x)
        body += text(x,427,"@"+config["username"],13)
        body += text(w-x,427,config["location"],13,C["muted"],text_anchor="end")
    else:
        body += text(w-42,382,t(config["location"])+" / @"+config["username"],12,C["muted"],text_anchor="end")
    return svg(w,h,body,"Allen is coding. " + " ".join(config["tagline"]) + " " + config["skills"] + ". " + config["location"],static)


def stats(data):
    days = data["days"]
    monthly = defaultdict(int)
    run = longest = 0
    for d in days:
        monthly[d["date"][:7]] += d["count"]
        run = run + 1 if d["count"] else 0
        longest = max(longest,run)
    tail = days[:-1] if days and not days[-1]["count"] else days
    current = 0
    for d in reversed(tail):
        if not d["count"]: break
        current += 1
    return {"total": sum(d["count"] for d in days), "active": sum(d["count"]>0 for d in days), "longest": longest, "current": current, "monthly": dict(sorted(monthly.items()))}


def calendar_card(data, st, mobile, static):
    w,h = (420,244) if mobile else (880,224)
    x = 28
    body = text(x,43,"Code, day by day.",25 if mobile else 27,family="serif")
    start,end = date.fromisoformat(data["from"]),date.fromisoformat(data["to"])
    period = f'{start:%b %d, %Y} - {end:%b %d, %Y}'
    body += text(x if mobile else w-x,70 if mobile else 42,period,11 if mobile else 12,C["muted"],text_anchor="start" if mobile else "end")
    origin = start - timedelta(days=(start.weekday()+1)%7)
    columns = ((end-origin).days//7)+1
    pitch = (w-2*x)/columns
    cell = pitch-2.5 if mobile else 10
    yp = 9.5 if mobile else 12.5
    gy = 104 if mobile else 84
    for month in st["monthly"]:
        d = date.fromisoformat(month+"-01")
        if d < start: continue
        col = (d-origin).days//7
        body += text(round(x+col*pitch,2),gy-10,calendar.month_abbr[d.month][0] if mobile else calendar.month_abbr[d.month],9 if mobile else 10,C["muted"])
    for item in data["days"]:
        d = date.fromisoformat(item["date"])
        col,row = (d-origin).days//7,(d.weekday()+1)%7
        px,py = round(x+col*pitch,2),round(gy+row*yp,2)
        title = f'{d}: {item["count"]} contributions'
        body += '<g>' + rect(px,py,round(cell,2),round(yp-2.5,2),HEAT[min(4,max(0,item["level"]))],1.7 if not mobile else .7,**{"class":"cell","style":f"--delay:{.18+col*.013:.3f}s"}) + f'<title>{esc(title)}</title></g>'
    body += text(x,200 if mobile else 204,f'{st["total"]:,} contributions',14,weight=600)
    lx = w-123
    body += text(lx-8,225 if mobile else 204,"Less",10,C["muted"],text_anchor="end")
    for i,color in enumerate(HEAT):body += rect(lx+i*13,217 if mobile else 196,9,9,color,1.5)
    body += text(w-x,225 if mobile else 204,"More",10,C["muted"],text_anchor="end")
    if mobile:body += text(x,225,"Public GitHub calendar",10,C["muted"])
    return svg(w,h,body,f'{st["total"]:,} GitHub contributions, {period}. Exact public contribution calendar.',static)


def activity(data,st,mobile,static):
    w,h = (420,356) if mobile else (880,294)
    body = text(28,43,"A year in perspective.",26 if mobile else 30,family="serif")
    metrics = [(st["active"],"Active days"),(st["longest"],"Longest streak"),(st["current"],"Current streak")]
    if mobile:
        for i,(value,label) in enumerate(metrics):
            px=28+i*127
            body += text(px,101,str(value),34) + text(px,124,label,11,C["muted"])
        gx,base,height,available = 28,286,109,364
    else:
        body += text(w-28,42,"Rolling 365 days",12,C["muted"],text_anchor="end")
        for i,(value,label) in enumerate(metrics):
            px,py = (567+i*148,111) if i<2 else (567,210)
            body += text(px,py,str(value),44) + text(px,py+24,label,12,C["muted"])
        gx,base,height,available = 28,226,123,470
    months=list(st["monthly"].items())
    peak=max((v for _,v in months),default=0)
    best=max(months,key=lambda m:m[1])[0] if peak else None
    pitch=available/len(months)
    bw=pitch*(.6 if mobile else .62)
    body += rule(gx,base,gx+available)
    for i,(month,count) in enumerate(months):
        px=gx+i*pitch+(pitch-bw)/2
        bh=max(2,round(height*count/max(peak,1),2))
        color=C["blue"] if month==best else "#B1B4AA"
        body += rect(round(px,2),base-bh,round(bw,2),bh,color,2,**{"class":"bar","style":f"--delay:{.5+i*.035:.3f}s"})
        label=(str(int(month[5:])) if mobile else str(int(month[5:]))+'月') if LANG=='zh-TW' else (calendar.month_abbr[int(month[5:])][0] if mobile else calendar.month_abbr[int(month[5:])])
        body += text(round(px+bw/2,2),base+21,label,10,C["muted"],text_anchor="middle")
        body += text(round(px+bw/2,2),base-bh-9,str(count),9 if mobile else 10,C["blue"] if month==best else C["muted"],text_anchor="middle")
    if not mobile and best:
        bd=date.fromisoformat(best+"-01")
        body += text(715,210,f'{bd:%b %Y}',19,C["blue"]) + text(715,234,"Busiest month",12,C["muted"])
    body += text(28,335 if mobile else 276,"Monthly contributions / first & last months are partial",10 if mobile else 11,C["muted"])
    return svg(w,h,body,f'Contributions by month. {st["active"]} active days, longest streak {st["longest"]} days, current streak {st["current"]} days. First and last months are partial.',static)


def tile(item,mobile,static,index):
    w,h=(160,150) if mobile else (284,210)
    fg=C["ink"] if item["color"]=="yellow" else "#FFFFFF"
    x=16 if mobile else 24
    body='<g class="print" style="--delay:'+str(.7+index*.12)+'s">'
    body+=text(x,43 if mobile else 52,item["title"],27 if mobile else 39,fg,family="serif")
    if not mobile:
        for i,line in enumerate(item["lines"]):body+=text(x,86+i*22,line,14,fg)
    body+=icon(item["icon"],x,88 if mobile else 143,fg,.85 if mobile else 1)
    body+=arrow(w-33,112 if mobile else 172,fg)
    body+='</g>'
    return svg(w,h,body,item["title"]+" "+" ".join(item["lines"]),static,bg=item["color"])


def project(p,mobile,static,index):
    w,h=(420,215) if mobile else (880,174)
    x=24 if mobile else 28
    body=f'<g class="print" style="--delay:{1+index*.08}s">'
    body+=text(x,46,p["title"],28 if mobile else 32,family="serif")
    lines=wrap_copy(t(p["description"]),width=38 if mobile else 76)
    for i,line in enumerate(lines):body+=text(x,81+i*(25 if mobile else 23),line,18 if mobile else 16)
    body+=text(x,151 if mobile else 137,p["stack"],11 if mobile else 12,C["muted"])
    body+=text(x,187,p["note"],11,C[p["color"]]) if mobile else text(550,137,p["note"],12,C[p["color"]])
    if not mobile:body+=icon(p["icon"],788,37,C[p["color"]],1.2)
    body+=arrow(w-40,174 if mobile else 124,C[p["color"]])
    body+='</g>'
    return svg(w,h,body,p["title"]+". "+t(p["description"])+" "+p["stack"]+". "+t(p["note"]),static,bg="white")


def footer(mobile,static):
    w,h=(420,115) if mobile else (880,105)
    body=text(28,47,"More things in the making.",27 if mobile else 33,family="serif")
    body+=text(28,81,"Explore the rest on GitHub",12,C["muted"])+arrow(w-42,68,C["blue"])
    return svg(w,h,body,"Explore the rest of Allen's repositories on GitHub.",static)


def picture(name,alt,width="100%"):
    return f'<picture>\n  <source media="(max-width: 600px)" srcset="./cards/{LANG}/{name}-mobile.svg">\n  <img src="./cards/{LANG}/{name}.svg" width="{width}" alt="{esc(alt)}">\n</picture>'


def write_readme(config,data,st,out):
    username=config["username"]
    url=f'https://github.com/{username}'
    zh=LANG=='zh-TW'
    nav='<p>繁體中文 · <a href="./README.en.md">English</a></p>' if zh else '<p><a href="./README.md">繁體中文</a> · English</p>'
    intro='Allen is coding。網頁體驗、攝影工具，還有把想法做成作品的各種實驗。台灣。' if zh else 'Allen is coding. Web experiences, photography tools and experiments in between. Based in Taiwan.'
    summary=f'{data["from"]} 至 {data["to"]}，共 {st["total"]:,} 次 GitHub 貢獻。' if zh else f'{st["total"]:,} contributions from {data["from"]} to {data["to"]}.'
    activity_alt=f'{st["active"]} 個活躍日；最長連續 {st["longest"]} 天；目前連續 {st["current"]} 天。' if zh else f'{st["active"]} active days. Longest streak: {st["longest"]} days. Current streak: {st["current"]} days.'
    parts=[nav,'',picture('hero',intro),'',picture('calendar',summary),'',picture('activity',activity_alt),'','<p align="center">']
    for i,tile_config in enumerate(config["tiles"]):
        href=tile_config["target"] if tile_config["target"].startswith("#") else url+'/'+tile_config["target"]
        if zh and href=='#photography-tools':href='#攝影工具'
        parts.append(f'<a href="{esc(href)}">'+picture(f'tile-{i}',t(tile_config["title"])+' '+' '.join(t(line) for line in tile_config["lines"]),"32%")+'</a>')
    selected='精選作品' if zh else 'Selected work'
    photography='攝影工具' if zh else 'Photography tools'
    web='網頁與自動化' if zh else 'Web & automation'
    parts += ['</p>',"",'## '+selected,"",'### '+photography,""]
    for p in config["projects"]:
        if p["group"]=="photography":parts += [f'<a href="{url}/{p["slug"]}">\n'+picture('project-'+p["slug"],p["title"]+" - "+t(p["description"]))+"\n</a>",""]
    parts += ['### '+web,""]
    for p in config["projects"]:
        if p["group"]!="photography":parts += [f'<a href="{url}/{p["slug"]}">\n'+picture('project-'+p["slug"],p["title"]+" - "+t(p["description"]))+"\n</a>",""]
    snapshot=f'貢獻資料日期：{data["to"]} · GitHub 公開貢獻紀錄 · 由 GitHub Actions 每日更新。' if zh else f'Contribution snapshot: {data["to"]} · Public GitHub calendar · Refreshed daily with GitHub Actions.'
    parts += [f'<a href="{url}?tab=repositories">\n'+picture("footer","到 GitHub 看所有作品" if zh else "Explore all repositories on GitHub")+"\n</a>","",f'<sub>{snapshot}</sub>',""]
    markdown='\n'.join(parts)
    (out/('README.md' if zh else 'README.en.md')).write_text(markdown,'utf-8')
    anchor='攝影工具' if zh else 'photography-tools'
    preview=markdown.replace('## '+selected,'<h2>'+selected+'</h2>').replace('### '+photography,f'<h3 id="{anchor}">{photography}</h3>').replace('### '+web,'<h3>'+esc(web)+'</h3>')
    preview=preview.replace('./README.en.md','./preview.en.html').replace('./README.md','./preview.html')
    (out/('preview.html' if zh else 'preview.en.html')).write_text(f'''<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Allen is coding — README preview</title><style>
      *{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{C['ink']};font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:944px;margin:32px auto;padding:0 32px 32px}}img{{max-width:100%;height:auto;vertical-align:middle}}main>picture,main>a{{display:block;margin-bottom:16px}}main>picture>img,main>a>picture>img{{width:100%}}p[align]{{display:flex;align-items:start;justify-content:space-between;gap:12px;margin:20px 0 42px}}p[align]>a{{display:block;width:32%;flex:1}}p[align] img{{width:100%}}a{{color:{C['blue']};text-underline-offset:.2em}}a:focus-visible{{outline:3px solid {C['blue']};outline-offset:5px;border-radius:14px}}h2{{font-size:24px;margin:40px 0 24px;border-bottom:1px solid #ddd;padding-bottom:10px}}h3{{font-size:17px;font-weight:600;margin:32px 0 16px}}sub{{font-size:11px;color:{C['muted']}}}::selection{{background:#D4DEFF}}@media(max-width:600px){{main{{padding:0 16px 24px;margin:16px auto}}p[align]{{gap:8px;margin:16px 0 32px}}h2{{margin-top:28px}}}}@media(prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}h2{{border-color:#30363d}}sub{{color:#9198a1}}a{{color:#9DB1FF}}}}
    </style></head><body><main>{preview}</main></body></html>''','utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--static',action='store_true',help='Render every animation at its final frame.')
    parser.add_argument('--output-dir',type=Path,default=ROOT)
    args=parser.parse_args()
    static=args.static or os.environ.get('STATIC')=='1'
    config=json.loads((ROOT/'profile.json').read_text('utf-8'))
    data=json.loads((ROOT/'data/contributions.json').read_text('utf-8'))
    if data['username']!=config['username']:raise ValueError('Contribution username differs from profile.json; refresh data first.')
    st=stats(data)
    global FONT_CSS,LANG
    out=args.output_dir.resolve()
    for lang in ('zh-TW','en'):
        LANG=lang
        FONT_CSS=font_css(include_han=(lang=='zh-TW'))
        cards=out/'cards'/lang;cards.mkdir(parents=True,exist_ok=True)
        for mobile in (False,True):
            suffix='-mobile' if mobile else ''
            generated={'hero':hero(config,mobile,static),'calendar':calendar_card(data,st,mobile,static),'activity':activity(data,st,mobile,static),'footer':footer(mobile,static)}
            generated.update({f'tile-{i}':tile(tile_config,mobile,static,i) for i,tile_config in enumerate(config['tiles'])})
            generated.update({'project-'+p['slug']:project(p,mobile,static,i) for i,p in enumerate(config['projects'])})
            for name,content in generated.items():(cards/(name+suffix+'.svg')).write_text(content,'utf-8')
        write_readme(config,data,st,out)
    print(f'Rendered bilingual {"static" if static else "animated"} SVGs and README/preview at {out}')


if __name__=='__main__':main()
