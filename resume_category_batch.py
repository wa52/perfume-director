"""Resume a failed real Qwen plan after deterministic compiler fixes, without replanning."""
import argparse
import copy
import hashlib
import importlib.util
from pathlib import Path
import re
import shutil
import time
import uuid
import poster
import concepts
from test_product_matrix import resume_four
from run_category_matrix import export, request

ROOT=poster.ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-batch',required=True)
    parser.add_argument('--job-id',required=True)
    parser.add_argument('--category',choices=['watches','footwear','beverage','skincare'],required=True)
    parser.add_argument('--tag',default='categories-recovery-20261003')
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{12}',args.source_batch) or not re.fullmatch('[a-f0-9]{32}',args.job_id) or not re.fullmatch('[a-zA-Z0-9-]+',args.tag):raise ValueError('Invalid saved identity')
    source=(ROOT/'runs/batches'/args.source_batch).resolve()
    if not source.is_relative_to(ROOT/'runs/batches'):raise ValueError('Unsafe batch path')
    config=poster.read(ROOT/'config.local.json');config.update(product_category=args.category,comfy_url=args.comfy_url)
    product=next(row for row in poster.read(ROOT/'assets/products/categories/products.json') if row['product_category']==args.category)
    image=ROOT/product['local_path']
    if hashlib.sha256(image.read_bytes()).hexdigest()!=product['sha256']:raise ValueError('Input image changed')
    approved=poster.categories_module().complete_copy(poster.read(source/'Product-copy.json'),config)
    refs=poster.read(source/'Planning-references.json')
    trace=next(path for path in (source/'Concepts-repair-2-call.json',source/'Concepts-repair-call.json',source/'Concepts-call.json') if path.is_file())
    value=concepts.resolve_reference_ids(poster.read(trace)['output'],refs)
    plans=concepts.validate_plans(poster,config,value,image,refs,{name:approved[name] for name in poster.TEXT_LAYERS})
    # Initialize the server's job manager while all jobs are terminal, before
    # announcing this independent worker. Otherwise a first read can mistake it for an orphan.
    existing=request(args.comfy_url,'/perfume-director/jobs/'+args.job_id)
    if existing['status']=='RUNNING':raise ValueError('Original job still running')
    for state in (ROOT/'runtime/director-jobs').glob('*/state.json'):
        if poster.read(state).get('status')=='RUNNING':raise ValueError('Wait for the other loop')
    module_spec=importlib.util.spec_from_file_location('category_recovery_jobs',ROOT/'comfy_node/jobs.py')
    module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    manager=module.DirectorJobs(ROOT,poster)
    saved=manager.state_path(args.job_id)
    shutil.copy2(saved,saved.parent/('prior-state-'+str(time.time_ns())+'.json'))
    batch=ROOT/'runs/batches'/uuid.uuid4().hex[:12];batch.mkdir(parents=True)
    for name,data in [('Concepts.json',plans),('Planning-references.json',refs),('Product-copy.json',approved)]:poster.write(batch/name,data)
    shutil.copy2(trace,batch/'Concepts-call.json')
    poster.write(batch/'request.json',{'product_category':args.category,'brief':product['brief'],'directions':plans,
        'recovery_source':source.relative_to(ROOT).as_posix(),'new_planning_api_calls':0,
        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('poster.py','categories.py','concepts.py','quality.py')}})
    record={**product,'job_id':args.job_id,'input_sha256':product['sha256'],'status':'RUNNING','stage':'RESUME_VALIDATED_PLANS','directions':[]}
    report=ROOT/'samples/categories'/args.tag;target=report/args.category;target.mkdir(parents=True,exist_ok=True)
    manager.save_state(saved,{'id':args.job_id,'status':'RUNNING','stage':'CONCEPTS','mode':'automatic_planning_recovery',
        'product_category':args.category,'vision_model':config['vision_model'],'run_dir':str(batch),'started_at':time.time(),'directions':[]})
    def progress(values):
        manager.update(args.job_id,values)
        record.update(values)
        poster.write(target/'state.json',record);export(report,[record])
        print(args.category,values.get('stage'),values.get('direction_index'),values.get('version'),flush=True)
    try:
        result_folder=resume_four(copy.deepcopy(config),image,product['brief'],batch,{},progress)
        result=poster.read(result_folder/'result.json')
        progress({'status':result['status'],'stage':'FINISHED','run_dir':str(result_folder),'directions':result['directions']})
    except Exception as error:
        progress({'status':'ERROR','stage':'FAILED','error':type(error).__name__})
        raise


if __name__=='__main__':main()
