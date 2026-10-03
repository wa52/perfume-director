"""One bottled-beverage V2 pilot; planning and actual render are separate stages."""
import argparse
import hashlib
from pathlib import Path
import uuid
import concepts
import poster


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('plan','render'))
    parser.add_argument('--config',default=str(poster.ROOT/'config.local.json'))
    parser.add_argument('--plan-dir')
    parser.add_argument('--direction',type=int,choices=range(1,5),default=1)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    args=parser.parse_args()
    config=poster.read(args.config)
    config.update(product_category='beverage',commercial_v2=True,direction_mode='dynamic',comfy_url=args.comfy_url)
    product=poster.ROOT/'assets/products/categories/beverage.png'
    brief='为这款可乐提出四个真正不同的广告创意。保持原商品，品牌名只排一次。只使用清楚可读的品牌和品类，无价格、促销、新品、营养或成分声明。背景和光线必须匹配原商品棚拍，不能虚构产品重新布光。'
    if args.stage=='plan':
        folder=poster.ROOT/'runs/commercial-pilot'/uuid.uuid4().hex[:12]
        folder.mkdir(parents=True)
        approved=poster.resolve_copy(config,product,brief,folder)
        if approved['title'].strip().casefold()==approved['logo'].strip().casefold():approved['logo']=''
        poster.write(folder/'IdentityLock.json',{'source_sha256':hashlib.sha256(product.read_bytes()).hexdigest(),
            'protected':'original RGB, labels and alpha; aspect-preserving resize/translation only'})
        plans,refs=concepts.plan_four(poster,config,product,brief,folder,approved)
        poster.write(folder/'Pilot.json',{'stage':'PLANNED_NOT_RENDERED','brief':brief,'approved_copy':approved,
            'product_profile':config.get('product_profile',{}),'references':refs,'directions':plans})
        poster.write(folder/'BrandAnalysis.json',config['commercial_creative']['brand_analysis'])
        poster.log('Plan directory:',folder)
    else:
        if not args.plan_dir:parser.error('render requires --plan-dir')
        folder=Path(args.plan_dir).resolve()
        if not folder.is_relative_to(poster.ROOT/'runs/commercial-pilot'):parser.error('Plan must be inside runs/commercial-pilot')
        saved=poster.read(folder/'Pilot.json');identity=poster.read(folder/'IdentityLock.json')
        creative=poster.read(folder/'CreativeConcepts.json')
        gate=poster.read(folder/'CreativeGate.json') if (folder/'CreativeGate.json').is_file() else {}
        if gate.get('pass') is not True or gate.get('concept_sha256')!=hashlib.sha256(poster.json.dumps(creative,sort_keys=True).encode()).hexdigest():
            raise ValueError('Pilot lacks accepted semantic review; re-plan instead of rendering layout variants')
        if hashlib.sha256(product.read_bytes()).hexdigest()!=identity['source_sha256']:raise ValueError('Pilot product changed after planning')
        plan=saved['directions'][args.direction-1]
        config.update(initial_spec=plan['initial_spec'],direction_id=plan['id'],approved_copy=plan.get('approved_copy',saved['approved_copy']),
            product_profile=saved['product_profile'],creative_direction=plan,planning_trace=str(folder/'Concepts-call.json'),
            references=[row for row in saved['references'] if row['id'] in plan['reference_ids']])
        config['commercial_creative']=creative
        node_info=poster.json.loads(poster.comfy_get(config['comfy_url'].rstrip('/')+'/object_info',poster.time.monotonic()+30))
        workflow=poster.read(config['background_workflow'])
        missing=sorted({node['class_type'] for node in workflow.values() if node['class_type'] not in node_info})
        if missing:raise ValueError('ComfyUI service missing configured background node types: '+', '.join(missing))
        run=poster.run(config,product,saved['brief'])
        poster.write(folder/f'Render-{args.direction}.json',{'run_dir':str(run),'result':poster.read(run/'result.json')})
        poster.log('Render directory:',run)


if __name__=='__main__':main()
