"""Bounded primary-source clothing campaign references with individual vision admission."""
import argparse
import concurrent.futures
from contextlib import closing
from datetime import datetime,timezone
import json
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import poster
import reference_store
from prepare_category_kb import analyze

ROOT=poster.ROOT
PAGES={
 'menswear':[
  ('Hugo Boss','https://www.juliengallico.com/projects/hugo-boss-campaign-ss-2017/'),
  ('Tommy Hilfiger','https://www.kimberlybrower.com/project/tommy-hilfiger'),
  ('Diesel','https://kioskproductions.co.uk/ss-folio')],
 'womenswear':[
  ('Claudie','https://www.juliengallico.com/projects/claudie-campaign-ss-25/'),
  ('Monsoon','https://kioskproductions.co.uk/fashion-shoot-production/monsoon-ireland'),
  ('Max Mara','https://www.stefanbeckman.com/campaign')]
}


def discover():
    rows=[]
    for category,pages in PAGES.items():
        for brand,page in pages:
            try:
                response=requests.get(page,headers={'User-Agent':'Mozilla/5.0'},timeout=25);response.raise_for_status()
                soup=BeautifulSoup(response.text,'html.parser');seen=set();accepted=[]
                for element in soup.select('img'):
                    caption=element.get('alt','')
                    if 'placeholder' in caption.lower():continue
                    if page.endswith('/ss-folio') or page.endswith('/campaign'):
                        if brand.replace(' ','').casefold() not in caption.replace(' ','').casefold():continue
                    src=element.get('data-src') or element.get('src','')
                    if element.get('srcset'):src=element['srcset'].split(',')[-1].strip().split()[0]
                    url=urljoin(page,src)
                    if not url.startswith('https://') or url in seen or any(t in url.lower() for t in ('favicon','.svg','.gif','avatar')):continue
                    # Campaign photographs may include a printed logo in their file name.
                    if any(t in url.lower() for t in ('logo','icon')) and 'campaign' not in caption.lower():continue
                    seen.add(url)
                    accepted.append({'product_category':category,'source_url':page,'image_url':url,'caption':brand+' campaign from the credited creative/production studio portfolio; '+caption,'audience_basis':'curated wardrobe reference, not a personal gender attribute'})
                rows.extend(accepted[:4]);print(category,brand,'candidates',min(4,len(accepted)),flush=True)
            except requests.RequestException as error:print(category,brand,type(error).__name__,flush=True)
    return list({row['image_url']:row for row in rows}.values())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--discover-only',action='store_true');args=parser.parse_args()
    rows=discover();folder=ROOT/'references/clothing';folder.mkdir(parents=True,exist_ok=True)
    poster.write(folder/'candidates.json',rows)
    if args.discover_only:return
    config=poster.read(ROOT/'config.local.json')
    config['vision_options']={**config.get('vision_options',{}),'enable_thinking':False,'max_tokens':4096,'temperature':.2}
    for key in ('thinking_budget','max_completion_tokens'):config['vision_options'].pop(key,None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda row:analyze(row,config),rows))
    with closing(reference_store.connect(ROOT)) as conn,conn:
        for row in results:
            if not row['accepted']:continue
            analysis={**row['analysis'],'category_suitability':row['analysis']['quality_score']}
            conn.execute('INSERT OR IGNORE INTO reference_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (row['id'],analysis['brand'],'editorial','commercial_reference',row['source_url'],row['image_url'],row['local_path'],row['width'],row['height'],row['sha256'],
                 (ROOT/row['local_path']).read_bytes(),analysis['reason'],json.dumps(analysis,ensure_ascii=False),'vision_api',row['rights_status'],datetime.now(timezone.utc).isoformat()))
            existing=conn.execute('SELECT id FROM reference_images WHERE sha256=?',(row['sha256'],)).fetchone()[0]
            if existing==row['id']:conn.execute('INSERT OR IGNORE INTO reference_categories VALUES (?,?)',(existing,row['product_category']))
    poster.write(folder/'review.json',results)
    summary={category:{'references':len(reference_store.entries(ROOT,category)),
      'brands':len({row['brand'] for row in reference_store.entries(ROOT,category)}),
      'garment_counts':{kind:sum(kind in row['analysis'].get('garment_types',[]) for row in reference_store.entries(ROOT,category)) for kind in poster.categories_module().GARMENT_TYPES if kind!='auto'}} for category in PAGES}
    poster.write(folder/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
