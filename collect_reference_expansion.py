"""Discover public portfolio/archive image links with source provenance; never crawl login pages."""
from pathlib import Path
import concurrent.futures
import json
from urllib.parse import urljoin, urlparse
import re
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parent
SOURCES=[
 ('howlett','https://www.howlettphoto.com/blog/still-life-product-photographer-london'),
 ('lux-cartier','https://luxstudio.london/cartier-perfume'),
 ('pasaric-vacay','https://apasaric.com/work/kayali-vacay-in-a-bottle/'),
 ('favero','https://www.adriannafavero.com/still-life-photographer-nyc'),
 ('paul-zak','https://www.katyniker.com/paul-zak-portfolio'),
 ('knowles007','https://jknowles.com/photography/advertising/007-fragrance/'),
 ('chanel-chance','https://www.designscene.net/2024/01/chanel-chance-2024-steven-meisel.html'),
 ('versace-eros','https://www.malemodelscene.net/ad-campaigns/brian-shimansky-versace/'),
 ('gaultier','https://www.malemodelscene.net/agencies/wilhelmina-models/chris-bunn-jean-paul-gaultier/'),
 ('dg-homme','https://www.malemodelscene.net/agencies/wilhelmina-models/noah-mills-laetitia-casta-dolce-gabbana-pour-homme-fragrance/'),
 ('lanvin','https://www.malemodelscene.net/agencies/select-models/alex-dunstan-lanvin-avant-garde-fragrance/'),
 ('versace-homme','https://www.malemodelscene.net/ad-campaigns/michael-gstoettner-versace-men-fragrance/'),
 ('givenchy','https://www.malemodelscene.net/agencies/mega-models/chalker-givenchy-pour-homme-fragrance/'),
]

def fetch(item):
    name,url=item
    r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=35)
    r.raise_for_status()
    folder=ROOT/'runtime/reference-pages';folder.mkdir(parents=True,exist_ok=True)
    (folder/(name+'.html')).write_text(r.text,encoding='utf-8')
    soup=BeautifulSoup(r.text,'html.parser')
    found=[]
    for el in soup.find_all(['img','a']):
        for attr in ('src','data-src','data-original','data-image','href'):
            value=el.get(attr,'')
            if not value or value.startswith('data:'):continue
            if not re.search(r'\.(?:jpg|jpeg|png|webp)(?:\?|$)',value,re.I) and not ('images.squarespace-cdn.com' in value and attr!='href'):continue
            absolute=urljoin(url,value)
            if any(x in absolute.lower() for x in ('logo','icon','favicon','banner-ad')):continue
            found.append({'image_url':absolute,'source_url':url,'caption':el.get('alt','') or el.get('title',''),'collection':name})
    # WordPress articles contain unrelated recent-story thumbnails outside the article body.
    if 'designscene.net' in url or 'malemodelscene.net' in url:
        found=[r for r in found if not re.search(r'-\d{2,4}x\d{2,4}\.',r['image_url'])]
    unique={r['image_url']:r for r in found}
    return list(unique.values())

if __name__=='__main__':
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,item):item for item in SOURCES}
        for f in concurrent.futures.as_completed(futures):
            try:
                result=f.result();rows+=result
                print(futures[f][0],len(result),flush=True)
            except Exception as e:print(futures[f][0],type(e).__name__,flush=True)
    (ROOT/'references/discovered.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
