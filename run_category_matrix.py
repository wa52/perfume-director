"""Exercise the real ComfyUI category node, then export visible reviewed results."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import time
import urllib.request
from PIL import Image
import poster
import reference_store
from categories import PROFILES

ROOT=Path(__file__).resolve().parent


def request(base,route,payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(base+route,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)


def export(folder,records):
    cards=[]
    for record in records:
        category=record['product_category'];items=[]
        for item in record.get('directions',[]):
            run=Path(item.get('run_dir','')).resolve()
            if 'selected' not in item or not run.is_relative_to(ROOT/'runs'):continue
            source=(run/item['selected']['poster']).resolve()
            if not source.is_relative_to(run):raise ValueError('Unsafe selected path')
            target=folder/category/item['id'];target.mkdir(parents=True,exist_ok=True)
            with Image.open(source) as image:image.convert('RGB').save(target/'poster.jpg',quality=95)
            selected=item['selected'];version=run/('v'+str(selected['version']))
            for name in ('PosterSpec.json','Critic.json'):
                if (version/name).is_file():poster.write(target/name,poster.read(version/name))
            evidence={'status':item['status'],'selected':selected,'versions':item.get('versions',[]),
                'input_sha256':record['input_sha256'],'poster_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
            poster.write(target/'evidence.json',evidence)
            items.append('<article><img src="'+category+'/'+item['id']+'/poster.jpg"><p>'+html.escape(item['name'])+'</p><small>'+html.escape(item['status'])+'</small></article>')
        cards.append('<section><h2>'+PROFILES[category]['label']+'</h2><p>'+html.escape(record.get('stage') or record['status'])+'</p><div class="grid">'+''.join(items)+'</div></section>')
    summary=[{'product_category':r['product_category'],'status':r['status'],'stage':r.get('stage'),'job_id':r.get('job_id'),
        'selected_directions':len([d for d in r.get('directions',[]) if 'selected' in d]),
        'model_pass_directions':sum(d['status']=='PASS' for d in r.get('directions',[]))} for r in records]
    poster.write(folder/'summary.json',summary)
    (folder/'gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>四类商品海报实测</title><style>body{background:#171918;color:#f2eee3;font:16px/1.7 system-ui;margin:36px}h2{margin-top:40px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}img{width:100%;height:400px;object-fit:contain;background:#242625}small{color:#ddbd86}@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}</style><h1>四类商品 · 四个设计方向</h1><p>真实 ComfyUI 多类别节点 → 千问 Director → 渲染 → 看图 Critic → 修改。NEEDS_REVIEW 表示仍有设计问题；模型 PASS 仍须人工验收。</p>'+''.join(cards),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    parser.add_argument('--tag',default='categories-20261003')
    parser.add_argument('--wait-for-kb',action='store_true')
    parser.add_argument('--categories',nargs='+',choices=['watches','footwear','beverage','skincare'])
    args=parser.parse_args()
    if not args.tag.replace('-','').isalnum():raise ValueError('Invalid tag')
    folder=ROOT/'samples/categories'/args.tag;folder.mkdir(parents=True,exist_ok=True)
    if args.wait_for_kb:
        deadline=time.monotonic()+3600
        while not (ROOT/'references/categories/summary.json').exists():
            if time.monotonic()>deadline:raise TimeoutError('Category KB preparation did not finish')
            time.sleep(10)
    products=poster.read(ROOT/'assets/products/categories/products.json');records=[]
    if args.categories:
        for item in products:
            saved=folder/item['product_category']/'state.json'
            if item['product_category'] not in args.categories and saved.exists():records.append(poster.read(saved))
        products=[item for item in products if item['product_category'] in args.categories]
    for product in products:
        category=product['product_category'];target=folder/category;target.mkdir(exist_ok=True)
        saved=target/'state.json'
        state=poster.read(saved) if saved.exists() else {**product,'input_sha256':product['sha256'],'status':'QUEUED'}
        records.append(state)
        if state['status'] in ('COMPLETED','PARTIAL','ERROR'):
            if state.get('job_id'):
                live=request(args.comfy_url,'/perfume-director/jobs/'+state['job_id'])
                state.update({k:live[k] for k in ('status','stage','directions') if k in live})
            export(folder,records);continue
        pool=reference_store.planning_pool(ROOT,category=category)
        if len({r['brand'] for r in pool})<3:
            state.update(status='ERROR',stage='Insufficient category references; no perfume fallback')
            poster.write(saved,state);export(folder,records);continue
        if not state.get('job_id'):
            graph={'1':{'class_type':'LoadImage','inputs':{'image':category+'.png'}},
                '2':{'class_type':'ProductDirectorLoop','inputs':{'product':['1',0],'product_mask':['1',1],'category':category,'brief':product['brief']}}}
            receipt=request(args.comfy_url,'/prompt',{'prompt':graph,'client_id':'category-matrix-'+args.tag})
            poster.write(target/'submission.json',{'prompt':graph,'receipt':receipt})
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
            state.update({k:live[k] for k in ('status','stage','direction_index','direction_name','version','directions','error') if k in live})
            poster.write(saved,{k:v for k,v in state.items() if k!='directions'})
            export(folder,records)
            if live['status']!='RUNNING':break
            time.sleep(10)
        # Preserve best selection metadata, and allow an interrupted runner to resume the same job.
        poster.write(saved,{k:v for k,v in state.items() if k!='directions'})
        print(category,state['status'],flush=True)
    export(folder,records)


if __name__=='__main__':main()
