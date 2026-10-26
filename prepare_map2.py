from pathlib import Path
import re,sys,urllib.request,urllib.parse,shutil,json
import pypdfium2 as pdfium
ROOT=Path(__file__).parent; OUT=ROOT/'sources'/'map-2';OUT.mkdir(parents=True,exist_ok=True)
local=ROOT.parent/'OEJN-Noise-Fuel-Capacity'/'A1'
for f in local.glob('*.pdf'):
    runway=re.search(r'RWY (34\w)',f.name)[1];n=re.search(r'tabulation (\d)',f.name)[1]
    dst=OUT/f'{runway}-table-{n}.pdf'
    if not dst.exists():shutil.copy2(f,dst)
page=(ROOT/'sources/OEJN-AIP-2026-10-01.html').read_text(encoding='utf-8')
links=re.findall(r'href="([^"]*SID RNAV RWY 34R[^"]*)"',page)
base='https://aimss.sans.com.sa/assets/FileManagerFiles/AIRAC%20AIP%20AMDT%2010_26_2026_10_01/eAIP/'
manifest=[]
for link in links:
    url=urllib.parse.quote(urllib.parse.urljoin(base,link),safe=':/%')
    print(url,flush=True)
    n=re.search(r'tabulation (\d)',link)
    if n:
        dst=OUT/f'34R-table-{n[1]}.pdf'
        if '--fetch' in sys.argv and not dst.exists():
            with urllib.request.urlopen(url,timeout=60) as response:dst.write_bytes(response.read())
        manifest.append({'file':dst.name,'url':url})
(OUT/'34R-sources.json').write_text(json.dumps(manifest,indent=2))
for f in OUT.glob('*.pdf'):
    pdf=pdfium.PdfDocument(str(f));p=pdf[0]
    p.render(scale=2).to_pil().save(str(f.with_suffix('.png')))
    text=p.get_textpage().get_text_range()
    (f.with_suffix('.txt')).write_text(text,encoding='utf-8')
    print(f.name,'text length',len(text),flush=True)
