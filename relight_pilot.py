"""Run an actual ComfyUI material-edit A/B trial on the existing beverage photograph."""
import argparse
import hashlib
import time
import uuid
from PIL import Image
import poster
import relighting


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    parser.add_argument('--config',default='config.local.json')
    parser.add_argument('--seed',type=int,default=20261003)
    parser.add_argument('--spec',default='samples/relighting/beverage-20261003/SourceSpec.json')
    parser.add_argument('--background',default='samples/relighting/beverage-20261003/source-background.png')
    parser.add_argument('--product',default='assets/products/categories/beverage.png')
    parser.add_argument('--zones',default='samples/relighting/beverage-20261003/IdentityZones.json')
    parser.add_argument('--prompt',help='Override the material-edit instruction for a controlled trial')
    parser.add_argument('--review',action='store_true',help='Use configured paid vision API; always remains a prototype')
    args=parser.parse_args()
    config=poster.read(args.config);config['comfy_url']=args.comfy_url
    spec_path=poster.ROOT/args.spec
    background=poster.ROOT/args.background
    product=poster.ROOT/args.product
    folder=poster.ROOT/'runs/relighting'/uuid.uuid4().hex[:12];folder.mkdir(parents=True)
    # Pilot-specific, conservatively wide bands, reviewed on this photographed bottle.
    # This is not an automatic material-zone detector.
    zones=poster.read(poster.ROOT/args.zones)
    before,alpha,protected,editable=relighting.prepare(poster,poster.read(spec_path),product,background,config['font'],(576,768),zones)
    for image,name in ((before,'before.png'),(alpha,'product-mask.png'),(protected,'identity-mask.png'),(editable,'editable-material-mask.png')):image.save(folder/name)
    poster.write(folder/'IdentityLock.json',{'source_sha256':hashlib.sha256(product.read_bytes()).hexdigest(),'zones':zones,
        'zone_source':'provided manual zones; not inferred material classes',
        'zone_file_sha256':hashlib.sha256((poster.ROOT/args.zones).read_bytes()).hexdigest(),'output_size':[576,768]})
    workflow=poster.read(poster.ROOT/'workflows/material-relight-mage.api.json')
    info=poster.json.loads(poster.comfy_get(args.comfy_url.rstrip('/')+'/object_info',time.monotonic()+30))
    missing=[n['class_type'] for n in workflow.values() if n['class_type'] not in info]
    if missing:raise ValueError('Missing ComfyUI nodes: '+', '.join(missing))
    workflow['1']['inputs']['image']=poster.upload(config,folder/'before.png')
    workflow['6']['inputs']['seed']=args.seed
    if args.prompt:workflow['5']['inputs']['prompt']=args.prompt
    poster.write(folder/'workflow.api.json',workflow)
    poster.log('Relight trial:',folder)
    poster.execute(config,workflow,'8',folder/'raw-material-edit.png')
    with Image.open(folder/'raw-material-edit.png') as raw:
        final,metrics=relighting.protect(before,raw,alpha,protected,editable)
    final.save(folder/'identity-protected-edit.png')
    with Image.open(folder/'raw-material-edit.png') as raw:
        transfer,transfer_metrics=relighting.transfer_illumination(before,raw,alpha)
    transfer.save(folder/'illumination-transfer-edit.png')
    result={'status':'UNREVIEWED','commercial_release_allowed':False,'metrics':metrics,'illumination_transfer':transfer_metrics,'seed':args.seed,
        'model':'Mage-Flow-Edit-Turbo local int8; instruction-based appearance edit, not a measured physical renderer'}
    poster.write(folder/'Result.json',result)
    if args.review:
        try:
            review=poster.vision(config,REVIEW_PROMPT,[folder/'before.png',folder/'raw-material-edit.png',
                folder/'identity-protected-edit.png',folder/'illumination-transfer-edit.png',product],trace_path=folder/'vision-trace.json')
            poster.write(folder/'VisualReview.json',review)
            accepted=all(isinstance(review.get(k),dict) and type(review[k].get('acceptable')) is bool for k in ('raw','protected','transfer'))
            result['status']='PROTOTYPE_ONLY' if accepted and any(review[k]['acceptable'] is True for k in ('protected','transfer')) else 'REJECTED'
        except Exception as error:
            result.update(status='REVIEW_FAILED',review_error_type=type(error).__name__)
            poster.write(folder/'Result.json',result)
            raise
        poster.write(folder/'Result.json',result)
    poster.log('Relight output:',folder,'protected pixel error:',metrics['protected_max_rgb_error'])


REVIEW_PROMPT='''Review this material/lighting experiment strictly. Image 1 original composite;
2 raw AI edit; 3 exact cap/label/boundary pixel restoration with editable interior;
4 source-texture smooth illumination transfer (no generated product RGB, source pixels
may change brightness); 5 original packshot. Check glass highlights, silhouette, label,
cap, liquid level, illumination direction, grounding, halos and band seams. Exact locked
pixels do not prove coherent lighting; retained texture does not prove physical reflection.
Return JSON {raw:{acceptable:boolean,material_improvement:boolean,problems:[{problem,evidence}],next_action:string},
protected:{acceptable:boolean,material_improvement:boolean,problems:[{problem,evidence}],next_action:string},
transfer:{acceptable:boolean,material_improvement:boolean,problems:[{problem,evidence}],next_action:string},conclusion:string}.
Acceptable only means consistent appearance-edit prototype, never commercial readiness.
Do not reward gloss if identity or scene light is wrong. No typography is being tested.'''


if __name__=='__main__':main()
