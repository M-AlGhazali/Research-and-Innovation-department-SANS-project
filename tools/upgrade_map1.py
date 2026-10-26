"""Rebuild the branded offline companion and geographic report plates, preserving data."""
from pathlib import Path
import re, json, math, html, base64, shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'map-1'
REPORT = OUT / 'report-assets'
REPORT.mkdir(exist_ok=True)
NAVY, BLUE, MINT = '#222b55', '#387aff', '#65ffa0'
COLORS = {'34C': '#008c95', '34L': '#d45883', '34R': '#b58329'}
AIP = 'https://aimss.sans.com.sa/assets/FileManagerFiles/AIRAC%20AIP%20AMDT%2010_26_2026_10_01/eAIP/AD%202%20OEJN%20JEDDAH%20-%20KING%20ABDULAZIZ%20INTERNATIONAL-en-US.html'
# Expand inherited gradients for Qt SVG rendering, preserving supplied artwork.
logo_text = (ROOT.parent / 'logo-on-dark.svg').read_text(encoding='utf-8')
stops = re.search(r'<linearGradient id="linear-gradient"[^>]*>(.*?)</linearGradient>',logo_text,re.S).group(1)
logo_text = re.sub(r'(<linearGradient[^>]+) xlink:href="#linear-gradient"/>',lambda m:m.group(1)+' gradientUnits="userSpaceOnUse">'+stops+'</linearGradient>',logo_text)
LOGO = logo_text.encode('utf-8')
LOGO_URI = 'data:image/svg+xml;base64,' + base64.b64encode(LOGO).decode()
(OUT / 'sans-logo.svg').write_bytes(LOGO)
data = json.loads((ROOT / 'map-2/data.json').read_text(encoding='utf-8'))

def esc(s): return html.escape(str(s))
def txt(x, y, s, size=16, color=NAVY, weight=400):
    return f'<text x="{x}" y="{y}" font-family="Segoe UI,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{esc(s)}</text>'
def lines(x, y, values, size=16, color='#677284', gap=25):
    return ''.join(txt(x, y+i*gap, s, size, color) for i,s in enumerate(values))
def rect(x,y,w,h,fill,stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>'
def path(points, fill, stroke='none', width=.6, closed=True):
    return '<path d="M'+'L'.join(f'{x:.2f},{y:.2f}' for x,y in points)+('Z' if closed else '')+f'" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'

def scene(focus=None, angle=-.35, w=880, h=485):
    """Orthographic 3D massing from retained metric footprints; no invented geography."""
    if focus:
        r=next(r for r in data['runways'] if r['id']==focus)
        cx=(r['start'][0]+r['finish'][0])/2; cz=(r['start'][1]+r['finish'][1])/2
        bounds=(cx-2.1,cz-2.9,cx+2.1,cz+2.9)
    else: bounds=(-4,-4,4,3.7)
    cx=(bounds[0]+bounds[2])/2; cz=(bounds[1]+bounds[3])/2
    def raw(p, z=0):
        x,y=p[0]-cx,p[1]-cz
        a=x*math.cos(angle)-y*math.sin(angle)
        b=x*math.sin(angle)+y*math.cos(angle)
        return a,b*.66-z*4
    corners=[raw(p) for p in [(bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[2],bounds[3]),(bounds[0],bounds[3])]]
    minx,maxx=min(x for x,y in corners),max(x for x,y in corners)
    miny,maxy=min(y for x,y in corners),max(y for x,y in corners)
    scale=min((w-55)/(maxx-minx),(h-60)/(maxy-miny))
    def proj(p,z=0):
        x,y=raw(p,z);return (w/2+(x-(minx+maxx)/2)*scale,h/2+(y-(miny+maxy)/2)*scale)
    def inside(p):return bounds[0]<=p[0]<=bounds[2] and bounds[1]<=p[1]<=bounds[3]
    out=['<g aria-label="Geographic airport building massing">',rect(0,0,w,h,'#f4f6f8')]
    base=[proj(p) for p in [(bounds[0],bounds[1]),(bounds[2],bounds[1]),(bounds[2],bounds[3]),(bounds[0],bounds[3])]]
    out += [path([(x,y+9) for x,y in base],'#d4dae2'),path(base,'#e9e9e1','#d8ddd9')]
    palette={'airport_boundary':'#efeee7','land_use':'#e9e7de','water':'#c3dbe4','green_spaces':'#d7e3ce','aprons_and_stopways':'#d1d5d7','roads':'#d6d2c8','railway':'#b3aaa0','taxiways':'#a3afb4'}
    buildings=[]
    for g in data['ground']:
        layer=g['layer']; kind=g['kind']; rings=g['coords'] if kind=='polygon' else [g['coords']]
        if not rings or not rings[0] or not all(inside(p) for p in rings[0]):continue
        if layer in ('buildings','terminals_and_hangars'):
            buildings.append(g);continue
        if layer=='runway_surfaces':
            key=g['name'].split(' / ')[0]; fill=COLORS[key] if not focus or key==focus else '#bbc2c7'
            for ring in rings:out.append(path([proj(p) for p in ring],fill))
        elif layer in palette:
            for ring in rings:out.append(path([proj(p) for p in ring],palette[layer] if kind=='polygon' else 'none',palette[layer],1.5 if layer=='taxiways' else .7,kind=='polygon'))
    buildings.sort(key=lambda g:sum(raw(p)[1] for p in g['coords'][0])/len(g['coords'][0]))
    for g in buildings:
        ring=g['coords'][0];z=.020 if g['layer']=='terminals_and_hangars' else .012
        top=[proj(p,z) for p in ring];ground=[proj(p) for p in ring]
        for i in range(len(ring)-1):out.append(path([ground[i],ground[i+1],top[i+1],top[i]],'#b4bfca','#a8b5c0',.3))
        out.append(path(top,'#fff' if z==.012 else '#dce6f1','#9eacb9',.45))
    for r in data['runways']:
        if not all(inside(p) for p in [r['start'],r['finish']]):continue
        c=COLORS[r['id']] if not focus or r['id']==focus else '#88949e'
        for key,p in [(r['id'],r['start']),(r['end'],r['finish'])]:
            x,y=proj(p);out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{c}" stroke="white"/>')
            out.append(f'<text x="{x+9:.1f}" y="{y-8:.1f}" font-family="Segoe UI,Arial" font-size="17" font-weight="700" fill="{c}" stroke="white" stroke-width="3" paint-order="stroke">{key}</text>')
    # North direction is transformed with the scene, rather than a fixed upward arrow.
    n0=proj((bounds[2]-.6,bounds[1]+1));n1=proj((bounds[2]-.6,bounds[1]+.3))
    out.append(path([n0,n1],'none',NAVY,2,False));out.append(txt(n1[0]-5,n1[1]-8,'N',13,NAVY,700))
    out.append(txt(18,h-15,'Geographic footprints · illustrative heights 12 / 20 m · vertical emphasis 4×',11,'#637384'))
    out.append('</g>');return ''.join(out)

def sheet_header(num,title,sub):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1400 990" role="img" aria-label="{esc(title)}">',
        '<defs><linearGradient id="brand"><stop stop-color="#387aff"/><stop offset="1" stop-color="#65ffa0"/></linearGradient></defs>',
        rect(0,0,1400,990,'white'),
        txt(42,46,'SANS / RESEARCH & INNOVATION / AIRFIELD ATLAS',13,'#758397',600),txt(42,89,title,32,NAVY,600),
        txt(1260,53,f'01 / {num:02}',18,BLUE,600),rect(42,118,1316,2,'url(#brand)'),txt(42,155,sub,15,'#6d788a')]
def footer(num):
    return [rect(42,920,1316,1,'#dce2eb'),txt(42,945,'SOURCE  SANS eAIP · AIRAC 10/26 · effective 01 Oct 2026 · AD 2.12 / 2.13 / 2.22',12,'#68778a'),
        txt(42,966,'© OpenStreetMap contributors / ODbL · snapshot 25 Oct 2026 · reference study / not for navigation',12,'#68778a'),txt(1290,958,f'{num:02}',23,BLUE,700),'</svg>']

def airport_sheet():
    s=sheet_header(1,'King Abdulaziz International Airport','JEDDAH, SAUDI ARABIA     /     OEJN     /     AIRPORT CONTEXT & STUDY SCOPE')
    s += [txt(42,202,'01   AIRFIELD IN THREE DIMENSIONS',16,BLUE,700),f'<g transform="translate(42,224)">{scene(w=865,h=493)}</g>']
    for x,val,label in [(940,'3','PHYSICAL RUNWAYS'),(1150,'2','STUDY RUNWAYS')]:
        s += [rect(x,224,195,130,'#f3f8f7'),rect(x,224,195,2,'#a7e4d2'),txt(x+20,286,val,48,'#008c95',700),txt(x+20,327,label,12,'#65758a',600)]
    s += [txt(940,398,'Three runways. Six named ends.',22,NAVY,600),lines(940,430,['Opposite designators refer to the same','physical strip, not separate runways.'],16),
        txt(940,510,'INITIAL STUDY FOCUS',13,BLUE,700)]
    for y,key,ends,dim in [(551,'34C','34C / 16C','4,000 × 60 m'),(621,'34L','34L / 16R','3,800 × 60 m'),(691,'34R','34R / 16L','4,000 × 60 m')]:
        s += [rect(940,y-22,5,44,COLORS[key]),txt(960,y,ends,23,COLORS[key],700),txt(1160,y,dim,16),txt(960,y+22,'Airport context only' if key=='34R' else 'Included in the initial study',12,'#6d788a')]
    s += [txt(42,766,'02   HOW THE STUDY IS BOUNDED',16,BLUE,700),lines(42,800,['The research concentrates on the central and western runways: 34C/16C and 34L/16R.',
        'The eastern runway, 34R/16L, remains visible to explain the full airport system.',
        'Building forms follow mapped footprints. Heights and flat terrain are illustrative, not surveyed.'],17),
        rect(940,765,405,126,'#f0f4fa'),txt(960,796,'READING THE MODEL',13,BLUE,700),lines(960,825,['Teal / rose: study runways','Ochre: third runway · white: buildings'],15)]
    return ''.join(s+footer(1))

def runway_sheet(key,num):
    center=key=='34C';ends='34C / 16C' if center else '34L / 16R';length=4000 if center else 3800;c=COLORS[key]
    s=sheet_header(num,('Central' if center else 'Western')+' runway / '+ends,'STUDY RUNWAY     /     PHYSICAL CHARACTERISTICS, GROUND CONTEXT & MOVEMENT LOGIC')
    s += [txt(42,202,'01   RUNWAY & SURROUNDING BUILDING MASSING',16,BLUE,700),f'<g transform="translate(42,220)">{scene(key,w=865,h=425)}</g>',
        rect(940,220,405,115,'#f3f8f7'),rect(940,220,405,2,'#a7e4d2'),txt(963,274,f'{length:,} m',43,c,700),txt(963,308,'PUBLISHED LENGTH   /   60 m WIDE',14,'#65758a',600),
        txt(940,378,'ASPHALT SURFACE',14,BLUE,700),txt(940,413,'340° / 160° true bearings',23,NAVY,600),
        lines(940,448,['Full-length TORA / TODA / ASDA / LDA:',f'{length:,} m in each direction (AD 2.13).','Intersection departures may be shorter.'],15),
        txt(940,549,'ONE STRIP, TWO DIRECTIONS',14,BLUE,700),lines(940,581,['The two labels identify opposite ends.','They do not create two physical runways.','ATC sequences movements and applies','runway and wake-turbulence separation.'],15),
        txt(42,689,'02   LENGTH & WIDTH',16,BLUE,700)]
    # Equal horizontal scale for both plates. Width is visibly exaggerated and explicitly labeled.
    rw=740*length/4000
    s += [rect(100,753,rw,38,c),f'<path d="M 125 772 H {100+rw-25}" stroke="white" stroke-width="2" stroke-dasharray="18 14"/>',
        txt(100,736,ends.split(' / ')[1],16,c,700),txt(100+rw-35,736,key,16,c,700),
        f'<path d="M 100 811 H {100+rw}" stroke="{NAVY}"/><path d="M 100 803 V 819 M {100+rw} 803 V 819" stroke="{NAVY}"/>',
        txt(100+rw/2-45,836,f'{length:,} m',18,NAVY,700),txt(100,873,'60 m wide · diagram width exaggerated for legibility · length scale shared across study sheets',13,'#6d788a'),
        rect(940,684,405,210,'#f0f4fa'),txt(960,716,'PARALLEL OPERATIONS',14,BLUE,700),
        lines(960,748,['AIP AD 2.22.2.6.1 lists independent','departures on specified runway pairs.','34C + 34L is not a listed pair.','Do not infer capacity from width or count.','No fixed aircraft/hour value is assumed.'],15,gap=26)]
    return ''.join(s+footer(num))

plates=[('airport-overview',airport_sheet()),('runway-34C',runway_sheet('34C',2)),('runway-34L',runway_sheet('34L',3))]
for name,svg in plates:(REPORT/(name+'.svg')).write_text(svg,encoding='utf-8')

def main():
    target=OUT/'Open-ground-map.html'
    original=target.read_text(encoding='utf-8')
    svg=re.search(r'<svg id="map".*?</svg>',original,re.S).group()
    template=(ROOT/'viewer-template.html').read_text(encoding='utf-8')
    template=template.replace('<!--MAP-->',svg).replace('<!--LOGO-->',LOGO_URI).replace('<!--AIP-->',AIP)
    template=template.replace('<!--REPORT-->',''.join(f'<article class="report-sheet" id="{name}">{plate}</article>' for name,plate in plates))
    target.write_text(template,encoding='utf-8')
    print('Updated offline atlas and 3 embedded geographic report sheets.')

if __name__=='__main__':main()
