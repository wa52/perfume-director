"""Resumable live product matrix: Qwen Director/Critic and real ComfyUI rendering."""
import argparse
import concurrent.futures
import copy
import hashlib
import shutil
from pathlib import Path
import time
import poster
import reference_store

ROOT=Path(__file__).resolve().parent
ENGINE_HASHES={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
               ('poster.py','concepts.py','quality.py','typography.py','reference_store.py','graphic_shapes.py')}


def resumable_batch(state):
    completed={d.get('run_dir') for d in state.get('directions',[]) if d.get('run_dir')}
    for path in sorted((ROOT/'runs/batches').glob('*/result.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        data=poster.read(path)
        if completed & {d.get('run_dir') for d in data.get('directions',[])}:
            return path.parent
    return None


def resume_four(config, product, brief, batch, previous, progress):
    request=poster.read(batch/'request.json');refs=poster.read(batch/'Planning-references.json')
    approved=poster.read(batch/'Product-copy.json')
    prior={d['id']:d for d in previous.get('directions',[])}
    if previous.get('direction_index') and previous.get('run_dir'):
        active=Path(previous['run_dir']);path=active/'result.json'
        if path.exists():
            plan=request['directions'][previous['direction_index']-1]
            prior[plan['id']]={**plan,'run_dir':str(active),**poster.read(path)}
    directions=[]
    for index,plan in enumerate(request['directions'],1):
        old=prior.get(plan['id'])
        if old and old.get('selected') and (Path(old['run_dir'])/old['selected']['poster']).is_file():
            reused=dict(old)
            if 'engine_source_sha256' not in reused and previous.get('source_sha256'):
                reused['engine_source_sha256']=previous['source_sha256']
            directions.append(reused)
            progress({'stage':'DIRECTION_REUSED','direction_index':index,'direction_name':plan['name'],'directions':list(directions)})
            continue
        child_record={}
        def report(values):
            if values.get('run_dir'):child_record['run_dir']=values['run_dir']
            progress({**values,'direction_index':index,'direction_count':4,'direction_name':plan['name'],'directions':list(directions)})
        child=copy.deepcopy(config)
        child.update(direction_seed_offset=(int(batch.name,16)+index*1009)%(2**63),direction_id=plan['id'],
            approved_copy={n:approved[n] for n in poster.TEXT_LAYERS},product_profile=approved.get('product_profile',{}),
            initial_spec=plan['initial_spec'],references=[r for r in refs if r['id'] in plan['reference_ids']],
            creative_direction={k:plan[k] for k in ('name','brief','material','lighting','palette','layout_relation','title_family','scene_mode') if k in plan},
            planning_trace=str(batch/'Concepts-call.json'))
        try:
            run=poster.run(child,product,brief+'\n'+plan['brief'],progress=report)
            result=poster.read(run/'result.json')
            item={**plan,'run_dir':str(run),**result,'engine_snapshot':config.get('_matrix_engine_session')}
            if previous.get('direction_index')==index:item['interrupted_run_dir']=previous.get('run_dir')
        except Exception as error:item={**plan,**child_record,'status':'ERROR','error':type(error).__name__}
        directions.append(item)
        poster.write(batch/'result.json',{'status':'COMPLETED' if len(directions)==4 and all(d['status']!='ERROR' for d in directions) else 'PARTIAL','directions':directions})
        report({'stage':'DIRECTION_FINISHED'})
    poster.write(batch/'result.json',{'status':'COMPLETED' if len(directions)==4 and all(d['status']!='ERROR' for d in directions) else 'PARTIAL','directions':directions})
    progress({'stage':'FINISHED','run_dir':str(batch),'directions':directions})
    return batch

def product_trial(item, config, output, retry=False):
    target=output/item['id'];target.mkdir(parents=True,exist_ok=True)
    result_file=target/'result.json'
    if result_file.exists() and not retry:return poster.read(result_file)
    previous=poster.read(target/'state.json') if (target/'state.json').exists() else {}
    batch=resumable_batch(previous) if previous.get('status')=='RUNNING' else None
    if previous:
        poster.write(target/f'prior-state-{time.time_ns()}.json',{**previous,'interruption_note':'Previous runner no longer active; preserved before explicit resume'})
    product=ROOT/item['local_path']
    if hashlib.sha256(product.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Product checksum mismatch')
    started=time.time();state={'product_id':item['id'],'status':'RUNNING','started_at':started,
        'input_sha256':item['sha256'],'reference_count':len(reference_store.entries(ROOT)),
        'source_sha256':ENGINE_HASHES, 'source_hash_basis':'process_start',
        'engine_snapshot':config.get('_matrix_engine_session'),
        'rounds_per_direction':config['max_rounds']}
    poster.write(target/'state.json',state)
    def progress(values):
        state.update(values);poster.write(target/'state.json',state)
        print(item['id'],values.get('stage'),values.get('direction_index',''),values.get('version',''),flush=True)
    try:
        folder=resume_four(config,product,item['brief'],batch,previous,progress) if batch else poster.run_four(copy.deepcopy(config),product,item['brief'],progress=progress)
        result=poster.read(folder/'result.json')
        record={**state,'status':result['status'],'batch_dir':folder.relative_to(ROOT).as_posix(),
                'directions':result['directions'],'duration_seconds':round(time.time()-started,1)}
    except Exception as error:
        record={**state,'status':'ERROR','error_type':type(error).__name__,
                'error':str(error),'duration_seconds':round(time.time()-started,1)}
    poster.write(result_file,record);poster.write(target/'state.json',record)
    return record

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag',required=True);p.add_argument('--ids',nargs='*');p.add_argument('--rounds',type=int,default=2)
    p.add_argument('--workers',type=int,choices=(1,2),default=1);p.add_argument('--retry',action='store_true')
    p.add_argument('--wait-for-100',action='store_true')
    args=p.parse_args()
    output=ROOT/'runs/matrix'/args.tag;output.mkdir(parents=True,exist_ok=True)
    snapshot=output/'engine-source';snapshot.mkdir(exist_ok=True)
    for name in ('poster.py','concepts.py','quality.py','typography.py','reference_store.py','graphic_shapes.py'):
        target=snapshot/name
        if not target.exists():shutil.copy2(ROOT/name,target)
    for name in ('poster.py','typography.py'):
        target=snapshot/('comfy-renderer-'+name)
        source=ROOT/'runtime/custom_nodes/perfume_director'/name
        if source.exists() and not target.exists():shutil.copy2(source,target)
    if args.wait_for_100:
        deadline=time.time()+3600
        while len(reference_store.entries(ROOT))<100:
            if time.time()>deadline:raise TimeoutError('Reference library did not reach100; no tests misreported')
            time.sleep(10)
    config=poster.read(ROOT/'config.local.json');config.update(max_rounds=args.rounds,direction_mode='dynamic',render_timeout_seconds=1500)
    session=hashlib.sha256(''.join(ENGINE_HASHES.values()).encode()).hexdigest()[:12]
    config['_matrix_engine_session']='engine-source/'+session
    for name in ENGINE_HASHES:
        target=snapshot/session/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(ROOT/name,target)
    for name in ('poster.py','typography.py','graphic_shapes.py'):
        target=snapshot/session/('comfy-renderer-'+name)
        origin=ROOT/'runtime/custom_nodes/perfume_director'/name
        if origin.exists() and not target.exists():shutil.copy2(origin,target)
    products=poster.read(ROOT/'assets/products/test-products-15.json')['products']
    if not args.ids and (output/'execution.json').exists():
        args.ids=poster.read(output/'execution.json').get('requested_products')
    if args.ids:products=[r for r in products if r['id'] in args.ids]
    if not products:raise ValueError('No matching products')
    poster.write(output/'execution.json',{'requested_products':[r['id'] for r in products],
                 'rounds_per_direction':args.rounds,'source_sha256':ENGINE_HASHES})
    result=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(product_trial,item,config,output,args.retry):item['id'] for item in products}
        for future in concurrent.futures.as_completed(pending):
            record=future.result();result.append(record)
            poster.write(output/'summary.json',{'requested_products':[r['id'] for r in products],
                'finished':len(result),'products':result})
            print('FINISHED',pending[future],record['status'],flush=True)

if __name__=='__main__':main()
