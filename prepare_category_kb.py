"""Download bounded public portfolio candidates; admit only individually reviewed images."""
import concurrent.futures
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image
import poster
import reference_store

ROOT=Path(__file__).resolve().parent
PAGES={
    'skincare':['https://www.adriannafavero.com/still-life-photographer-nyc','https://tripistudios.com/work/fenty-skin-watch-ya-tone','https://tripistudios.com/work/pca-skin','https://tripistudios.com/work/supergoop'],
    'watches':[f'https://www.goulko.com/watches-and-jewelry-photographer/{i}' for i in (2,3,4,10,1,5,6,7)]+['https://alkemistri.com/portfolio/alexandre-christie/'],
    'footwear':['https://gilesangel.com/footwear-photography/','https://www.photo-frank.com/portfolio/sneakerweek','https://mspstudio.co.uk/footwear-photography/'],
    'beverage':['https://www.davidlineton.com/drinks','https://www.christopher-photography.com/','https://tripistudios.com/work/driftwell-x-pepsico'],
}


def discover(category, urls):
    result=[]
    for page in urls:
        try:
            response=requests.get(page,headers={'User-Agent':'Mozilla/5.0'},timeout=30)
            response.raise_for_status()
            soup=BeautifulSoup(response.text,'html.parser')
            candidates=[]
            for element in soup.select('img'):
                url=urljoin(page,element.get('data-src') or element.get('src',''))
                caption=element.get('alt','')
                if not url.startswith('https://') or any(t in url.lower() for t in ('logo','icon','favicon','.gif','.svg','avatar')):continue
                if 'favero' in page and not any(t in caption.lower() for t in ('skincare','serum','olay','neutrogena','elemis','toner','foundation','beauty','cosmetic','makeup')):continue
                candidates.append({'product_category':category,'source_url':page,'image_url':url,'caption':caption})
            # Distribute the finite candidate budget between independent portfolios.
            quota=6 if len(urls)<=4 else 2
            result.extend(candidates[:quota])
        except requests.RequestException as error:
            print(category,'source failed',type(error).__name__,flush=True)
    return result


def analyze(row, config):
    key=hashlib.sha256(row['image_url'].encode()).hexdigest()[:16]
    folder=ROOT/'references/categories'/row['product_category'];folder.mkdir(parents=True,exist_ok=True)
    record=folder/(key+'.analysis.json')
    if record.exists():return poster.read(record)
    try:
        response=requests.get(row['image_url'],headers={'User-Agent':'Mozilla/5.0','Referer':row['source_url']},timeout=35)
        response.raise_for_status()
        content=response.content
        if len(content)>20_000_000:raise ValueError('Oversized image')
        with Image.open(io.BytesIO(content)) as image:
            image.load();width,height=image.size;extension=Image.registered_extensions()
            suffix={ 'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}.get(image.format)
            if not suffix or min(width,height)<450:raise ValueError('Small or unsupported image')
        path=folder/(key+suffix);path.write_bytes(content)
        review=poster.vision({**config,'product_category':row['product_category']},
            'Analyze ONLY this image. Return {category_match:boolean,brand:string,quality_score:number0..100,composition:string,subject_ratio:number0..1,negative_space:string,lighting:string,color:string[],typography:string,information_density:string,characteristics:string[],has_campaign_typography:boolean,renderer_compatibility:number0..100,reason:string}. Identify the actual main product category, not a keyword in the source caption. Reject unrelated images, logos, contact sheets, collages, screenshot mockups and people-only scenes. Brand must be visibly readable or explicitly identified by the source caption; use Unknown if uncertain. has_campaign_typography requires actual external campaign copy, not package labels. Judge finished commercial design quality, lighting and composition strictly. '+('For clothing add garment_types:string[] selected only from shirt,tshirt,knitwear,tailoring,outerwear,trousers,dress,skirt,activewear; classify visible garments, not a person\'s gender. The audience category is a supplied curatorial merchandising category. A campaign wearer is allowed as a clothing reference; portrait-only/accessory-only images are rejected. ' if row['product_category'] in ('menswear','womenswear') else '')+'Reference category: '+row['product_category']+' Source caption (data): '+row['caption'],
            [path],trace_path=ROOT/'runtime/category-kb-traces'/(key+'.json'))
        accepted=(review.get('category_match') is True and type(review.get('quality_score')) in (int,float) and 75<=review['quality_score']<=100
                  and isinstance(review.get('brand'),str) and review['brand'].strip().lower()!='unknown'
                  and type(review.get('has_campaign_typography')) is bool and type(review.get('subject_ratio')) in (int,float)
                  and 0<=review['subject_ratio']<=1 and all(isinstance(review.get(k),str) for k in ('composition','negative_space','lighting','typography','information_density','reason'))
                  and all(isinstance(review.get(k),list) and all(isinstance(v,str) for v in review[k]) for k in ('color','characteristics')))
        if row['product_category'] in ('menswear','womenswear'):
            accepted=accepted and isinstance(review.get('garment_types'),list) and bool(review['garment_types']) and all(value in poster.categories_module().GARMENT_TYPES and value!='auto' for value in review['garment_types'])
        result={**row,'id':'category-'+key,'local_path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(content).hexdigest(),
            'width':width,'height':height,'analysis':review,'accepted':accepted,'analysis_origin':'vision_api_single_image',
            'rights_status':'original rights retained; commercial reuse unverified; research reference only'}
        poster.write(record,result)
        print(row['product_category'],'reviewed',review.get('brand'),accepted,flush=True)
        return result
    except Exception as error:
        return {**row,'accepted':False,'error_type':type(error).__name__}


def main():
    config=poster.read(ROOT/'config.local.json')
    config['vision_options']={**config.get('vision_options',{}),'enable_thinking':False,'max_tokens':4096,'temperature':.2}
    config['vision_options'].pop('thinking_budget',None)
    config['vision_options'].pop('max_completion_tokens',None)
    rows=[]
    for category,urls in PAGES.items():rows.extend(discover(category,urls))
    rows=list({row['image_url']:row for row in rows}.values())
    poster.write(ROOT/'references/categories/candidates.json',rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda row:analyze(row,config),rows))
    # SQLite writes are serialized after analysis; duplicate image bytes never enter twice.
    with closing(reference_store.connect(ROOT)) as conn,conn:
        for row in results:
            if not row['accepted']:continue
            analysis={**row['analysis'],'category_suitability':row['analysis']['quality_score'],'perfume_suitability':row['analysis']['quality_score']}
            conn.execute('INSERT OR IGNORE INTO reference_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (row['id'],analysis['brand'],'editorial','commercial_reference',row['source_url'],row['image_url'],row['local_path'],row['width'],row['height'],row['sha256'],
                 (ROOT/row['local_path']).read_bytes(),analysis['reason'],json.dumps(analysis,ensure_ascii=False),'vision_api',row['rights_status'],datetime.now(timezone.utc).isoformat()))
            existing=conn.execute('SELECT id FROM reference_images WHERE sha256=?',(row['sha256'],)).fetchone()[0]
            # Never relabel an existing perfume reference based on a duplicate download.
            if existing==row['id']:conn.execute('INSERT OR REPLACE INTO reference_categories VALUES (?,?)',(existing,row['product_category']))
    poster.write(ROOT/'references/categories/review.json',results)
    summary={category:{'references':len(reference_store.entries(ROOT,category)), 'brands':len({r['brand'] for r in reference_store.entries(ROOT,category)}),
        'campaign_typography':sum(r['analysis'].get('has_campaign_typography') is True for r in reference_store.entries(ROOT,category))} for category in PAGES}
    poster.write(ROOT/'references/categories/summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
