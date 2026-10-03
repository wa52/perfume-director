"""Real ComfyUI transport fault injection; this does not assess poster aesthetics."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.error
from unittest.mock import patch
from PIL import Image,ImageChops
import poster


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    parser.add_argument('--cycles',type=int,default=2,choices=range(1,6))
    args=parser.parse_args()
    root=poster.ROOT;folder=root/'runs/live-transport-20261003';folder.mkdir(parents=True,exist_ok=True)
    public=root/'samples/stability/multicategory-20261003';records=[]
    products=poster.read(root/'assets/products/categories/products.json')+poster.read(root/'assets/products/clothing/products.json')
    products.insert(0,{'product_category':'perfume','local_path':'assets/products/dior-jadore-retailer.png'})
    config={'comfy_url':args.comfy_url,'render_timeout_seconds':900}
    original_http=poster.http
    for cycle in range(args.cycles):
        for item in products:
            category=item['product_category'];source=root/item['local_path']
            target=folder/(category+'-'+str(cycle+1)+'.png')
            started=time.monotonic();injected=set();submissions=[]
            try:
                uploaded=poster.upload(config,source)
                graph={'1':{'class_type':'LoadImage','inputs':{'image':uploaded}},
                       '2':{'class_type':'SaveImage','inputs':{'images':['1',0],'filename_prefix':'stability-transport/'+category}}}
                def exchange(url,data=None,headers=None,timeout=60):
                    kind='history' if '/history/' in url else 'download' if '/view?' in url else None
                    if kind and kind not in injected:
                        injected.add(kind);raise urllib.error.URLError('injected read disconnect')
                    response=original_http(url,data,headers,timeout)
                    if url.endswith('/prompt'):submissions.append(json.loads(response)['prompt_id'])
                    return response
                with patch.object(poster,'http',side_effect=exchange),patch('builtins.print',side_effect=BrokenPipeError('injected closed output')):
                    poster.log('advisory progress')
                    poster.execute(config,graph,'2',target)
                with Image.open(source) as before,Image.open(target) as after:
                    assert before.size==after.size,'Image size changed'
                    extrema=ImageChops.difference(before.convert('RGB'),after.convert('RGB')).getextrema()
                    assert max(high for low,high in extrema)<=1,'Roundtrip changed RGB content'
                assert len(submissions)==1 and injected=={'history','download'},'Duplicate submit or incomplete injection'
                record={'category':category,'cycle':cycle+1,'status':'TRANSPORT_VERIFIED','prompt_ids':submissions,
                    'injected_faults':sorted(injected)+['closed_console'],'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'rgb_roundtrip_max_error':max(high for low,high in extrema),
                    'duration_seconds':round(time.monotonic()-started,2),'generative_render':False,'aesthetic_pass':False}
            except Exception as error:
                record={'category':category,'cycle':cycle+1,'status':'FAILED','error_type':type(error).__name__,'prompt_ids':submissions,
                    'injected_faults':sorted(injected),'generative_render':False,'aesthetic_pass':False}
            records.append(record)
            poster.write(public/'transport.json',{'cases':records,'requested_cases':len(products)*args.cycles,
                'passed':sum(r['status']=='TRANSPORT_VERIFIED' for r in records),'failed':sum(r['status']=='FAILED' for r in records),
                'does_not_validate_director_critic_or_commercial_quality':True,
                'source_sha256':hashlib.sha256(Path(poster.__file__).read_bytes()).hexdigest()})
            poster.log(category,cycle+1,record['status'])
    if any(r['status']=='FAILED' for r in records):raise SystemExit(1)


if __name__=='__main__':main()
