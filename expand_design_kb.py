"""Download discovered public references and keep auditable, image-grounded screening."""
import concurrent.futures
import hashlib
import io
import json
import os
import argparse
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import requests
from PIL import Image
import poster

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'runtime/reference-expansion'

def download(row):
    identity=hashlib.sha256(row['image_url'].encode()).hexdigest()[:12]
    row={**row,'id':'ref-'+identity}
    metadata=WORK/(row['id']+'.json')
    if metadata.exists():return poster.read(metadata)
    try:
        response=requests.get(row['image_url'],headers={'User-Agent':'Mozilla/5.0','Referer':row['source_url']},timeout=40)
        response.raise_for_status()
        content=response.content
        if len(content)>20_000_000:raise ValueError('oversized')
        im=Image.open(io.BytesIO(content));im.load()
        if min(im.size)<380 or max(im.size)/min(im.size)>3:raise ValueError('small_or_banner')
        suffix={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}[im.format]
        path=ROOT/'references/candidates'/(row['id']+suffix);path.write_bytes(content)
        small=im.convert('L').resize((9,8));px=list(small.getdata())
        dhash=sum((px[y*9+x]>px[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8))
        row.update(status='downloaded',path=path.relative_to(ROOT).as_posix(),width=im.width,height=im.height,
                   sha256=hashlib.sha256(content).hexdigest(),dhash=f'{dhash:016x}')
    except Exception as e:row.update(status='failed',error=type(e).__name__)
    poster.write(metadata,row)
    return row

def analyze(config,rows,index):
    path=WORK/f'analysis-{index:03d}.json'
    if path.exists():return poster.read(path)
    ids=[r['id'] for r in rows]
    prompt=('Screen these images individually for a perfume art-direction reference library. Each image corresponds in order to these IDs: '+json.dumps(ids)+
        '. Return {items:[{id,accepted:boolean,brand:string,style:luxury/editorial/minimal/experimental/tech/fashion,'
        'reference_kind:string,reason:string,analysis:{composition:string,subject_ratio:number0..1,negative_space:string,'
        'lighting:string,color:string[],typography:string,information_density:string,characteristics:string[],'
        'perfume_suitability:number0..100,has_people:boolean,has_campaign_typography:boolean,renderer_compatibility:number0..100}}]}. '
        'Observe pixels, never infer content from source metadata. Brand only if legible, otherwise Unknown. '
        'Accept only excellent perfume campaign posters or professionally resolved perfume still-life compositions with useful lighting/material/design. '
        'Reject plain white-background isolated packshots, unrelated makeup/skincare/food/fashion, logos, contact sheets, blurry thumbnails and amateur work. '
        'A well photographed perfume still-life with no campaign text is useful but must be named still_life and typography=none; do not call it a finished poster. '
        'Do not count tiny bottle-label text as campaign typography. Flag people-led adverts as low renderer compatibility; current renderer is one upright cutout, background and editable type. '
        'Keep each analysis compact, reason concrete and visual. Score quality honestly; accepted should be >=78 suitability. No need to accept a target number.')
    value=poster.vision(config,prompt,[ROOT/r['path'] for r in rows],WORK/f'call-{index:03d}.json')
    items=value.get('items',[])
    if len(items)!=len(rows) or {r.get('id') for r in items}!=set(ids):raise ValueError('Missing or mismatched image analysis')
    for r in items:
        a=r['analysis']
        if type(r.get('accepted')) is not bool or not isinstance(r.get('brand'),str) or not 0<=a['subject_ratio']<=1 or not 0<=a['perfume_suitability']<=100:raise ValueError('Invalid analysis')
    poster.write(path,value)
    return value

def main():
    global WORK
    parser=argparse.ArgumentParser()
    parser.add_argument('--more',action='store_true')
    args=parser.parse_args()
    if args.more:WORK=ROOT/'runtime/reference-expansion-more'
    WORK.mkdir(parents=True,exist_ok=True)
    rows=poster.read(ROOT/'references/discovered-more.json') if args.more else poster.read(ROOT/'references/portfolio-links.json')+poster.read(ROOT/'references/discovered.json')
    unique={}
    for row in rows:
        u=urlsplit(row['image_url']);key=urlunsplit((u.scheme,u.netloc,u.path,'',''))
        unique.setdefault(key,row)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        downloaded=list(pool.map(download,unique.values()))
    good=[];seen=set()
    old=poster.read(ROOT/'references/downloads.json')
    seen.update(r.get('sha256') for r in old if r.get('status')=='downloaded')
    for row in downloaded:
        if row['status']=='downloaded' and row['sha256'] not in seen:
            good.append(row);seen.add(row['sha256'])
    poster.write(WORK/'downloads.json',downloaded)
    poster.write(WORK/'screening-input.json',good)
    print('Downloaded unique candidates:',len(good),flush=True)
    config=poster.read(ROOT/'config.local.json')
    config['vision_options']={**config.get('vision_options',{}),'temperature':.1,'thinking_budget':512,'max_completion_tokens':8192}
    batches=[good[i:i+6] for i in range(0,len(good),6)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending={pool.submit(analyze,config,b,i):i for i,b in enumerate(batches)}
        for future in concurrent.futures.as_completed(pending):
            try:
                result=future.result();print('Screened',pending[future],sum(x['accepted'] for x in result['items']),flush=True)
            except Exception as e:print('Analysis failed',pending[future],type(e).__name__,flush=True)
    print('Screening finished; review before import.',flush=True)

if __name__=='__main__':main()
