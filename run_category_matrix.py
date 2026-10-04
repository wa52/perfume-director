"""Exercise the real ComfyUI category node, then export visible reviewed results."""
import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path
import time
import urllib.request
from PIL import Image
import poster
import reference_store
from categories import PROFILES, CLOTHING_CATEGORIES, GARMENT_TYPES

ROOT=Path(__file__).resolve().parent


def case_key(product):
    """Keep subtype fixtures isolated while preserving historic category paths."""
    key=product.get('case_id',product['product_category'])
    if not isinstance(key,str) or not key or not key.replace('-','').replace('_','').isalnum():
        raise ValueError('Invalid case_id')
    return key


def request(base,route,payload=None):
    if payload is None:
        return json.loads(poster.comfy_get(base+route,time.monotonic()+30))
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(base+route,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)


def submit_once(base,product,target):
    """Recover the same Comfy receipt after a monitor restart; never resubmit it."""
    submission=target/'submission.json'
    if submission.exists():
        saved=poster.read(submission)
        if saved.get('input_sha256')!=product['sha256']:raise ValueError('Saved submission input cannot be verified')
        if saved.get('comfy_url')!=base:raise ValueError('Saved submission belongs to a different server')
        return saved['receipt']
    image=(ROOT/product['local_path']).resolve()
    if not image.is_relative_to(ROOT/'assets/products') or hashlib.sha256(image.read_bytes()).hexdigest()!=product['sha256']:
        raise ValueError('Unsafe or changed product input')
    category=product['product_category']
    uploaded=poster.upload({'comfy_url':base},image)
    graph={'1':{'class_type':'LoadImage','inputs':{'image':uploaded}},
           '2':{'class_type':'ProductDirectorLoop','inputs':{'product':['1',0],'product_mask':['1',1],'category':category,'brief':product['brief']}}}
    if category in CLOTHING_CATEGORIES:
        graph['2']['class_type']='ClothingDirectorLoop'
        graph['2']['inputs'].update(garment_type=product['garment_type'],display_mode=product['display_mode'])
    receipt=request(base,'/prompt',{'prompt':graph,'client_id':'category-matrix-'+target.parent.name})
    poster.write(submission,{'prompt':graph,'receipt':receipt,'input_sha256':product['sha256'],'comfy_url':base})
    return receipt


def export(folder,records):
    cards=[]
    for record in records:
        category=record['product_category'];key=case_key(record);items=[]
        for item in record.get('directions',[]):
            run=Path(item.get('run_dir','')).resolve()
            if 'selected' not in item or not run.is_relative_to(ROOT/'runs'):continue
            source=(run/item['selected']['poster']).resolve()
            if not source.is_relative_to(run):raise ValueError('Unsafe selected path')
            target=folder/key/item['id'];target.mkdir(parents=True,exist_ok=True)
            with Image.open(source) as image:image.convert('RGB').save(target/'poster.jpg',quality=95)
            selected=item['selected'];version=run/('v'+str(selected['version']))
            shutil.copyfile(source,target/'poster.png')
            for name in ('PosterSpec.json','Critic.json','CommercialGate.json','CommercialArtDirector.json','CommercialRepair.json'):
                if (version/name).is_file():poster.write(target/name,poster.read(version/name))
            evidence={'status':item['status'],'selected':selected,'versions':item.get('versions',[]),
                'input_sha256':record['input_sha256'],'poster_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'quality_profile':record.get('quality_profile'),
                'commercial_gate':poster.read(version/'CommercialGate.json') if (version/'CommercialGate.json').exists() else None}
            poster.write(target/'evidence.json',evidence)
            items.append('<article><img src="'+key+'/'+item['id']+'/poster.jpg"><p>'+html.escape(item['name'])+'</p><small>'+html.escape(item['status'])+'</small></article>')
        label=PROFILES[category]['label']+(' · '+GARMENT_TYPES[record.get('garment_type','auto')] if category in CLOTHING_CATEGORIES else '')
        cards.append('<section><h2>'+label+'</h2><p>'+html.escape(record.get('stage') or record['status'])+'</p><div class="grid">'+''.join(items)+'</div></section>')
    summary=[{'case_id':case_key(r),'product_category':r['product_category'],'garment_type':r.get('garment_type'),'status':r['status'],'stage':r.get('stage'),'job_id':r.get('job_id'),
        'quality_profile':r.get('quality_profile'),'commercial_target':r.get('commercial_target'),
        'selected_directions':len([d for d in r.get('directions',[]) if 'selected' in d]),
        'model_pass_directions':sum(d['status']=='PASS' for d in r.get('directions',[]))} for r in records]
    poster.write(folder/'summary.json',summary)
    (folder/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>商品海报闭环实测</title><style>body{background:#171918;color:#f2eee3;font:16px/1.7 system-ui;margin:36px}h2{margin-top:40px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}img{width:100%;height:400px;object-fit:contain;background:#242625}small{color:#ddbd86}@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}</style><h1>商品海报 · 四个设计方向</h1><p>真实 ComfyUI 多类别节点 → 千问 Director → 渲染 → 看图 Critic → 修改。NEEDS_REVIEW 表示仍有设计问题；模型 PASS 仍须人工验收。</p>'+''.join(cards),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    parser.add_argument('--tag',default='categories-20261003')
    parser.add_argument('--wait-for-kb',action='store_true')
    parser.add_argument('--categories',nargs='+',choices=list(PROFILES))
    parser.add_argument('--manifest',help='Project-local JSON list; repeated categories require distinct case_id values')
    args=parser.parse_args()
    if not args.tag.replace('-','').isalnum():raise ValueError('Invalid tag')
    folder=ROOT/'samples/categories'/args.tag;folder.mkdir(parents=True,exist_ok=True)
    if args.wait_for_kb:
        deadline=time.monotonic()+3600
        while not (ROOT/'references/categories/summary.json').exists():
            if time.monotonic()>deadline:raise TimeoutError('Category KB preparation did not finish')
            time.sleep(10)
    products=poster.read(ROOT/'assets/products/categories/products.json');records=[]
    if args.manifest:
        manifest=(ROOT/args.manifest).resolve()
        if not manifest.is_relative_to(ROOT/'assets/products'):raise ValueError('Manifest must be inside project assets/products')
        products=poster.read(manifest)
        if not isinstance(products,list) or not products or len({case_key(p) for p in products})!=len(products):raise ValueError('Unique case_id required for each product')
        for product in products:poster.categories_module().profile(product)
    elif args.categories and any(category in CLOTHING_CATEGORIES for category in args.categories):
        products+=poster.read(ROOT/'assets/products/clothing/products.json')
    if args.categories:
        for item in products:
            saved=folder/case_key(item)/'state.json'
            if item['product_category'] not in args.categories and saved.exists():records.append(poster.read(saved))
        products=[item for item in products if item['product_category'] in args.categories]
    for product in products:
        category=product['product_category'];target=folder/case_key(product);target.mkdir(exist_ok=True)
        saved=target/'state.json'
        state=poster.read(saved) if saved.exists() else {**product,'input_sha256':product['sha256'],'status':'QUEUED'}
        if state.get('input_sha256')!=product['sha256']:
            raise ValueError('Saved case uses a different product; use a new test tag')
        records.append(state)
        if state['status'] in ('COMPLETED','PARTIAL','ERROR'):
            if state.get('job_id'):
                live=request(args.comfy_url,'/perfume-director/jobs/'+state['job_id'])
                state.update({k:live[k] for k in ('status','stage','directions') if k in live})
            export(folder,records);continue
        pool=reference_store.planning_pool(ROOT,category=category,garment_type=product.get('garment_type'))
        if len({r['brand'] for r in pool})<3:
            state.update(status='ERROR',stage='Insufficient category references; no perfume fallback')
            poster.write(saved,state);export(folder,records);continue
        if not state.get('job_id'):
            receipt=submit_once(args.comfy_url,product,target)
            deadline=time.monotonic()+180
            while True:
                history=request(args.comfy_url,'/history/'+receipt['prompt_id']).get(receipt['prompt_id'],{})
                output=history.get('outputs',{}).get('2',{})
                if output.get('perfume_job'):
                    state['job_id']=output['perfume_job'][0];break
                if history.get('status',{}).get('completed') or time.monotonic()>deadline:raise RuntimeError('Category node did not submit a job')
                time.sleep(2)
        while True:
            live=request(args.comfy_url,'/perfume-director/jobs/'+state['job_id'])
            # Store operational paths locally; the public summary contains no endpoint or provider trace.
            state.update({k:live[k] for k in ('status','stage','direction_index','direction_name','version','directions','error','run_dir','quality_profile','commercial_target') if k in live})
            poster.write(saved,{k:v for k,v in state.items() if k!='directions'})
            export(folder,records)
            if live['status']!='RUNNING':break
            time.sleep(10)
        # Preserve best selection metadata, and allow an interrupted runner to resume the same job.
        poster.write(saved,{k:v for k,v in state.items() if k!='directions'})
        poster.log(category,state['status'])
    export(folder,records)


if __name__=='__main__':main()
