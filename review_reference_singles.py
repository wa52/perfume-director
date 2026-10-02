"""Recheck candidate identity one image per call; batch screening is not final annotation."""
import concurrent.futures
import copy
import hashlib
from pathlib import Path
import poster

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'runtime/reference-singles'

def review(config,row):
    path=OUT/(row['id']+'.json')
    if path.exists():return poster.read(path)
    prompt=('Review ONLY this single image for a perfume campaign design library. Return {accepted:boolean,brand:string,'
        'style:luxury/editorial/minimal/experimental/tech/fashion,reference_kind:campaign_poster/still_life/material_detail,'
        'reason:string,analysis:{composition:string,subject_ratio:number0..1,negative_space:string,lighting:string,color:string[],'
        'typography:string,information_density:string,characteristics:string[],perfume_suitability:number0..100,'
        'has_people:boolean,has_campaign_typography:boolean,renderer_compatibility:number0..100}}. '
        'Accept only a professionally resolved perfume advertisement or perfume still-life, useful as design reference, score>=78. '
        'Reject unrelated skincare/hair oil/watches, plain isolated white-background packshots, logos and low quality. '
        'Brand must be read from THIS image, Unknown if not legible. Never guess. Label lettering on the container is NOT campaign typography. '
        'Only text designed outside the photographed container qualifies as campaign typography. Human-led ads are useful for typography but low cutout-renderer compatibility. '
        'Observe light, subject scale, arrangement, palette. Use concise objective English annotations. A decorative photographic set without text is still_life, not campaign_poster.')
    value=poster.vision(config,prompt,[ROOT/row['path']],OUT/(row['id']+'-call.json'))
    if type(value.get('accepted')) is not bool or not isinstance(value.get('brand'),str):raise ValueError('Invalid annotation')
    a=value['analysis']
    if not isinstance(a.get('subject_ratio'),(int,float)) or not 0<=a['subject_ratio']<=1 or not 0<=a['perfume_suitability']<=100:raise ValueError('Invalid measurements')
    value.update(id=row['id'],image_sha256=row['sha256'],analysis_origin='vision_api',analysis_mode='single_image',analysis_model=config['vision_model'])
    poster.write(path,value);return value

def main():
    OUT.mkdir(parents=True,exist_ok=True);assets={};ids=set()
    for folder in ['reference-expansion','reference-expansion-more']:
        root=ROOT/'runtime'/folder
        assets.update({r['id']:r for r in poster.read(root/'downloads.json') if r['status']=='downloaded'})
        for path in root.glob('call-*.json'):
            ids.update(r['id'] for r in poster.read(path).get('output',{}).get('items',[]) if r.get('accepted') and r['id'] in assets)
    config=poster.read(ROOT/'config.local.json');config['vision_options']={'temperature':.1,'enable_thinking':False,'max_completion_tokens':3072}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        pending={pool.submit(review,copy.deepcopy(config),assets[i]):i for i in sorted(ids)}
        for f in concurrent.futures.as_completed(pending):
            try:r=f.result();print(r['id'],r['accepted'],flush=True)
            except Exception as e:print(pending[f],type(e).__name__,flush=True)

if __name__=='__main__':main()
