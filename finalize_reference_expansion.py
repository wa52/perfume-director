"""Prepare a reviewed100 shortlist with visual duplicates and raw analysis provenance."""
import collections
import hashlib
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import poster
import reference_store

ROOT=Path(__file__).resolve().parent

def perceptual_hash(path):
    with Image.open(path) as im:array=np.asarray(im.convert('L').resize((32,32)),dtype=float)
    axis=np.arange(32);basis=np.cos(np.pi*(2*axis[None,:]+1)*axis[:,None]/64)
    low=(basis@array@basis.T)[:8,:8].flatten()[1:]
    return sum(int(v>np.median(low))<<i for i,v in enumerate(low))

def main():
    existing=poster.read(ROOT/'references/curated.json')
    downloads=poster.read(ROOT/'references/downloads.json')
    candidates={};annotations={}
    for name in ('reference-expansion','reference-expansion-more'):
        folder=ROOT/'runtime'/name
        for row in poster.read(folder/'downloads.json'):
            if row['status']=='downloaded':candidates[row['id']]=row
    for path in (ROOT/'runtime/reference-singles').glob('ref-*.json'):
        if path.name.endswith('-call.json'):continue
        row=poster.read(path)
        if row.get('id') in candidates and row.get('accepted') is True and row.get('analysis',{}).get('perfume_suitability',0)>=78:
            if row['image_sha256']!=candidates[row['id']]['sha256']:raise ValueError('Annotation/image mismatch')
            annotations[row['id']]={**row,'analysis_call':path.with_name(path.stem+'-call.json').relative_to(ROOT).as_posix()}
    selected=[];collections_count=collections.Counter();brand_count=collections.Counter();hashes={r.get('sha256') for r in downloads}
    visual_hashes={r['id']:perceptual_hash(ROOT/r['image']) for r in reference_store.entries(ROOT)}
    def rank(row):
        a=row['analysis'];return a['perfume_suitability']+8*bool(a.get('has_campaign_typography'))+a.get('renderer_compatibility',50)*.1
    rejected=[]
    for row in sorted(annotations.values(),key=rank,reverse=True):
        asset=candidates[row['id']]
        brand=row['brand'].lower().strip()
        if asset['sha256'] in hashes:continue
        if collections_count[asset['collection']] >= (2 if asset['collection']=='pasaric-vacay' else 26) or brand_count[brand]>=(8 if brand=='unknown' else 4):continue
        phash=perceptual_hash(ROOT/asset['path'])
        near=[identity for identity,other in visual_hashes.items() if (other^phash).bit_count()<=6]
        if near:
            rejected.append({'id':row['id'],'near_duplicates':near});continue
        selected.append(row);hashes.add(asset['sha256']);visual_hashes[row['id']]=phash;collections_count[asset['collection']]+=1;brand_count[brand]+=1
        if len(selected)==80:break
    if len(selected)<80:raise ValueError(f'Only{len(selected)} unique qualified additions; do not pad the library')
    output=ROOT/'references/expansion-review';output.mkdir(exist_ok=True)
    poster.write(output/'shortlist.json',selected)
    poster.write(output/'duplicate-rejections.json',rejected)
    poster.write(output/'shortlist-downloads.json',[candidates[r['id']] for r in selected])
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    for page in range(5):
        sheet=Image.new('RGB',(1400,1520),'#222222');draw=ImageDraw.Draw(sheet)
        for i,row in enumerate(selected[page*16:(page+1)*16]):
            asset=candidates[row['id']];im=Image.open(ROOT/asset['path']).convert('RGB');im.thumbnail((330,325))
            x=(i%4)*350+(350-im.width)//2;y=(i//4)*380
            sheet.paste(im,(x,y));draw.text(((i%4)*350+8,y+330),row['id'],font=font,fill='white')
            draw.text(((i%4)*350+8,y+352),row['brand'][:30],font=font,fill='white')
        sheet.save(output/f'shortlist-{page+1}.jpg',quality=90)
    print('Shortlisted80',dict(collections_count),'with campaign typography',sum(r['analysis'].get('has_campaign_typography',False) for r in selected),flush=True)

if __name__=='__main__':main()
