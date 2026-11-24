"""Sample a transparent portrait into real ASCII rows. Requires Pillow once, not at render time."""
from __future__ import annotations

import json
import base64
import html
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAMP=" .,:;irsXA253hMHGS#9B&@"


def sample_ascii(image, box, columns):
    width,height=image.size
    left,top,right,bottom=[round(v*s) for v,s in zip(box,(width,height,width,height))]
    rows=max(1,round(columns*(bottom-top)/(right-left)*.55))
    pixels=image.load()
    samples=[]
    for row in range(rows):
        line=[]
        for col in range(columns):
            alpha_sum=luma_sum=0.0
            for sy in (.2,.5,.8):
                for sx in (.2,.5,.8):
                    px=min(width-1,max(0,int(left+(col+sx)*(right-left)/columns)))
                    py=min(height-1,max(0,int(top+(row+sy)*(bottom-top)/rows)))
                    red,green,blue,alpha=pixels[px,py]
                    a=alpha/255
                    alpha_sum+=a
                    luma_sum+=(.2126*red+.7152*green+.0722*blue)*a
            line.append((alpha_sum/9,luma_sum/max(alpha_sum,.0001)))
        samples.append(line)
    tones=sorted(luma for line in samples for a,luma in line if a>.7)
    if not tones:raise ValueError('No foreground pixels in portrait crop.')
    low=tones[int(len(tones)*.02)]
    high=tones[min(len(tones)-1,int(len(tones)*.97))]
    # Rebalance facial midtones independently of the black hair and white shirt.
    # This changes character selection only; the transparent source is untouched.
    face_tones=[]
    for row,line in enumerate(samples):
        source_y=top+(row+.5)*(bottom-top)/rows
        for col,(a,luma) in enumerate(line):
            source_x=left+(col+.5)*(right-left)/columns
            if a>.7 and .235*width<source_x<.56*width and .15*height<source_y<.35*height:
                face_tones.append(luma)
    face_tones.sort()
    face_low=face_tones[int(len(face_tones)*.04)] if face_tones else low
    face_high=face_tones[min(len(face_tones)-1,int(len(face_tones)*.96))] if face_tones else high
    result=[]
    for row,line in enumerate(samples):
        out=[]
        source_y=top+(row+.5)*(bottom-top)/rows
        for col,(a,luma) in enumerate(line):
            if a<.72:out.append(' ');continue
            source_x=left+(col+.5)*(right-left)/columns
            face_weight=math.exp(-.5*(((source_x-.395*width)/(.16*width))**2+((source_y-.255*height)/(.105*height))**2))
            neighbors=[samples[rr][cc][1] for rr in range(max(0,row-2),min(rows,row+3)) for cc in range(max(0,col-2),min(columns,col+3)) if samples[rr][cc][0]>.7]
            local_mean=sum(neighbors)/len(neighbors) if neighbors else luma
            detail=luma-local_mean
            facial_luma=max(0,min(255,luma+1.15*detail))
            darkness=max(0,min(1,(high-luma)/max(1,high-low)))**1.35
            facial_darkness=max(0,min(1,(face_high-facial_luma)/max(1,face_high-face_low)))**1.65
            darkness=darkness*(1-face_weight)+facial_darkness*face_weight
            index=max(1,round(darkness*(len(RAMP)-1)))
            out.append(RAMP[index])
        result.append(''.join(out))
    return {'columns':columns,'rows':result,'source_crop_normalized':box}


def main():
    from PIL import Image
    source=ROOT/'assets/portrait-cutout.png'
    image=Image.open(source).convert('RGBA')
    alpha=image.getchannel('A')
    if alpha.getextrema()[0]>0:raise ValueError('The cutout must have genuinely transparent background pixels.')
    # Framing is relative to the generated transparent cutout, not the original wall.
    desktop=(170/1024,15/1536,690/1024,665/1536)
    mobile=(170/1024,25/1536,680/1024,535/1536)
    result={'source':source.name,'method':'Alpha-aware printable ASCII with face-focused framing, local detail enhancement and smoothly blended facial midtone normalization. Transparent pixels become spaces.','ramp':RAMP,
            'desktop':sample_ascii(image,desktop,128),'mobile':sample_ascii(image,mobile,96)}
    target=ROOT/'data/portrait-ascii.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf-8')
    (ROOT/'assets/portrait-ascii.txt').write_text('\n'.join(result['desktop']['rows'])+'\n','utf-8')
    font=base64.b64encode((ROOT/'fonts/mono.woff2').read_bytes()).decode()
    rows=result['desktop']['rows'];step=1140/len(rows)
    elements=''.join(f'<text x="0" y="{(i+.82)*step:.3f}" textLength="960" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{html.escape(line)}</text>' for i,line in enumerate(rows) if line.strip())
    standalone=f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="1140" viewBox="0 0 960 1140" role="img" aria-label="Allen, background-free ASCII portrait"><style>@font-face{{font-family:ProfileMono;src:url(data:font/woff2;base64,{font}) format("woff2");font-weight:600}}text{{font-family:ProfileMono,monospace;font-size:{step:.3f}px;font-weight:600;fill:#161812}}</style>{elements}</svg>'
    (ROOT/'assets/portrait-ascii.svg').write_text(standalone,'utf-8')
    print(f'ASCII portrait: {len(result["desktop"]["rows"])} desktop rows; {len(result["mobile"]["rows"])} mobile rows.')


if __name__=='__main__':main()
