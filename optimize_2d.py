"""Reproducible source-preserving 2D lighting/composite comparison."""
import argparse
import copy
import hashlib
from pathlib import Path
import uuid
from PIL import Image,ImageDraw
import poster
import harmonization


PROMPT='''Compare a controlled 2D product integration experiment. Image 1 baseline original
compositor; images 2,3,4 candidates A,B,C; image 5 original transparent product flattened
onto a neutral background; image 6 enlarged contact/neck/label details for baseline,A,B,C
in that exact row order. The same product, canvas, clean background and typography are
used. No generated product RGB is copied in the candidates. Do not reward that invariant
as visual quality; critically inspect original-edge remnants, label texture, liquid level,
glass light, scene agreement, floor contact and shadow direction. New candidates use
linear-light RGBA composition and source-compatible frontal light, not the raw AI beam.
No hard directional beam exists in their background: do not demand a dramatic hard shadow
for diffuse frontal light. The product base is not required to be on the floor horizon.
The enlarged contact detail is authoritative for whether an actual soft shadow exists.
Evaluate the visual source quality honestly; retain defects even if they existed in source.
Return JSON {versions:[{id:"baseline"|"A"|"B"|"C",scores:{product_fidelity:number,
edge_quality:number,lighting_coherence:number,grounding:number},problems:[{problem,evidence,
root_cause,repair}],integration_acceptable:boolean}],preferred:"baseline"|"A"|"B"|"C",
reason:string,next_repairs:[{target,action}]}. All scores are 0..100. Integration acceptable
requires all four scores >=88, fidelity>=95 and no unresolved problems. This is not
commercial typography, creative or overall campaign approval. Compare actual images
without assuming a new version is better. If every candidate is worse prefer baseline.'''


def render_batch(config,folder,spec,product,background,zones,guide_before,guide,contour_contact=False,spill_zones=None,refine_alpha=False,wrap_zones=None,contact_opacity=.5,reflection_trial=False):
    folder.mkdir(parents=True,exist_ok=False)
    blank=copy.deepcopy(spec)
    for layer in poster.TEXT_LAYERS:blank[layer]['text']=''
    blank['decoration']['enabled']=False
    poster.render(blank,product,config['font'],background).save(folder/'baseline.png')
    poster.render(spec,product,config['font'],background).save(folder/'baseline-poster.png')
    results={}
    candidates=[('A',.35,0),('B',.35,.12),('C',.35,.24)] if reflection_trial else [('A',0,0),('B',.35,0),('C',.65,0)]
    for id,strength,reflection in candidates:
        scene,final,metrics=harmonization.compose(poster,spec,product,background,config['font'],zones,
            guide_before,guide,strength=strength,contour_contact=contour_contact,spill_zones=spill_zones,refine_alpha=refine_alpha,wrap_zones=wrap_zones,contact_opacity=contact_opacity,reflection_strength=reflection)
        scene.save(folder/(id+'.png'));final.save(folder/(id+'-poster.png'))
        results[id]=metrics
    poster.write(folder/'Metrics.json',results)
    # Contact, neck and label crops retain 1:1 output detail before display resizing.
    p=spec['product'];rgba=product.convert('RGBA');rgba=rgba.crop(rgba.getchannel('A').getbbox())
    rgba.thumbnail((round(p['width']),round(p['height'])),Image.Resampling.LANCZOS)
    px,py=round(p['x']-rgba.width/2),round(p['y']-rgba.height/2)
    boxes=[(px-24,py+rgba.height-48,px+rgba.width+70,py+rgba.height+70),
        (px-18,py-10,px+rgba.width+18,py+round(rgba.height*.39)),
        (px-18,py+round(rgba.height*.37),px+rgba.width+18,py+round(rgba.height*.65))]
    details=Image.new('RGB',(1080,960),'#e7e5e1');draw=ImageDraw.Draw(details)
    preview=Image.new('RGB',(1584,552),'#ecebe6');labels=['baseline','A','B','C']
    for row,id in enumerate(labels):
        with Image.open(folder/(id+'.png')) as im:
            draw.text((4,row*240+4),id,fill='black',font_size=20)
            for col,box in enumerate(boxes):
                tile=im.crop(box);tile.thumbnail((340,210));details.paste(tile,(16+col*360,row*240+28))
            im.thumbnail((384,512));preview.paste(im,(8+row*396,32))
            labels_map={'baseline':'Original compositor','A':'Reflection control: 0','B':'Protected reflections: 0.12','C':'Protected reflections: 0.24'} if reflection_trial else {'baseline':'Original compositor','A':'Clean source / linear light','B':'Smooth guide: 0.35','C':'Smooth guide: 0.65'}
            ImageDraw.Draw(preview).text((8+row*396,8),labels_map[id],fill='black',font_size=18)
    details.save(folder/'Details.png');preview.save(folder/'comparison.jpg',quality=94)
    return results


def select_review(review):
    # Explicit schema and all dimensions, never promote an average or string boolean.
    ids={'baseline','A','B','C'}
    versions=review.get('versions') if isinstance(review,dict) else None
    if not isinstance(versions,list) or len(versions)!=4:raise ValueError('Four reviewed versions required')
    seen=set();approved=[]
    for item in versions:
        if not isinstance(item,dict) or item.get('id') not in ids or item['id'] in seen:raise ValueError('Invalid version identity')
        seen.add(item['id']);scores=item.get('scores')
        if not isinstance(scores,dict) or set(scores)!={'product_fidelity','edge_quality','lighting_coherence','grounding'}:raise ValueError('Four explicit scores required')
        import math
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100 for v in scores.values()):raise ValueError('Invalid review scores')
        if type(item.get('integration_acceptable')) is not bool or not isinstance(item.get('problems'),list):raise ValueError('Explicit decision/problems required')
        if item['integration_acceptable'] and not item['problems'] and scores['product_fidelity']>=95 and min(scores.values())>=88:approved.append(item['id'])
    preferred=review.get('preferred')
    if preferred not in ids:raise ValueError('Invalid preferred candidate')
    return {'status':'INTEGRATION_ONLY' if preferred in approved else 'NEEDS_REVIEW',
        'preferred':preferred,'integration_approved':approved,'commercial_release_allowed':False}


def review_batch(config,folder,product_path):
    prompt=PROMPT+'\nDeterministic renderer evidence (appearance still requires visual inspection): '+poster.json.dumps(poster.read(folder/'Metrics.json'))+'\nNo rotation/shear or product-texture blur is performed. All candidates use the same resized source and contact geometry. Report perceived artifacts, but do not invent a new rotation, extra source resample or omitted shadow as engineering root cause.'
    review_id=uuid.uuid4().hex[:8]
    for attempt in (1,2):
        review=poster.vision(config,prompt,[folder/(id+'.png') for id in ['baseline','A','B','C']]+[product_path,folder/'Details.png'],trace_path=folder/f'vision-trace-{review_id}-{attempt}.json')
        poster.write(folder/f'Review-attempt-{review_id}-{attempt}.json',review)
        try:
            result=select_review(review)
        except ValueError as error:
            if attempt==2:raise
            prompt+='\nPrevious response was rejected for schema error: '+str(error)+'. Return all FOUR version objects, each with the exact four score names, explicit boolean integration_acceptable, and a problems list. Never return placeholders or a partial baseline object. Assess the actual six images again.'
            continue
        poster.write(folder/'VisualReview.json',review)
        poster.write(folder/'Result.json',result)
        return result


def select_independent(review):
    rows=review.get('candidates') if isinstance(review,dict) else None
    if not isinstance(rows,list) or len(rows)!=3:raise ValueError('Three independent candidates required')
    seen=set();accepted=[]
    import math
    for row in rows:
        id=row.get('id') if isinstance(row,dict) else None
        if id not in ('X','Y','Z') or id in seen:raise ValueError('Invalid independent candidate identity')
        seen.add(id)
        for key in ('product_fidelity','physical_integration','edge_quality'):
            value=row.get(key)
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=100:raise ValueError('Invalid independent score')
        problems=row.get('blocking_problems')
        if not isinstance(problems,list) or any(not isinstance(p,dict) or any(not isinstance(p.get(k),str) or not p[k].strip() for k in ('problem','evidence')) for p in problems):raise ValueError('Independent defects require actual evidence')
        if type(row.get('acceptable_integration')) is not bool:raise ValueError('Explicit independent decision required')
        if row['acceptable_integration'] and not problems and row['product_fidelity']>=95 and row['physical_integration']>=88 and row['edge_quality']>=88:accepted.append(id)
    if review.get('preferred') not in seen or not isinstance(review.get('reason'),str) or not review['reason'].strip():raise ValueError('Independent preference/evidence missing')
    return {'status':'INTEGRATION_ONLY' if review['preferred'] in accepted else 'NEEDS_REVIEW',
        'preferred':review['preferred'],'integration_approved':accepted,'commercial_release_allowed':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config.local.json')
    parser.add_argument('--spec',default='samples/relighting/beverage-20261003/SourceSpec.json')
    parser.add_argument('--product',default='assets/products/categories/beverage.png')
    parser.add_argument('--background',default='samples/relighting/beverage-20261003/source-background.png')
    parser.add_argument('--zones',default='samples/relighting/beverage-20261003/IdentityZones.json')
    parser.add_argument('--guide-before',default='samples/relighting/beverage-20261003/trial-2/before.png')
    parser.add_argument('--guide',default='samples/relighting/beverage-20261003/trial-2/raw-material-edit.png')
    parser.add_argument('--output',help='Output directory; otherwise creates a unique ignored run')
    parser.add_argument('--review',action='store_true')
    parser.add_argument('--review-only',action='store_true',help='Review an existing output directory without replacing images')
    parser.add_argument('--contour-contact',action='store_true',help='Build the contact core from actual bottom-support contour')
    parser.add_argument('--spill-zones',help='Optional reviewed source-edge RGB cleanup regions; never use another product\'s regions')
    parser.add_argument('--refine-alpha',action='store_true',help='Optional measured subpixel matte repair; no longer exact-alpha identity')
    parser.add_argument('--wrap-zones',help='Optional reviewed contour light-wrap regions (strength <=0.3)')
    parser.add_argument('--contact-opacity',type=float,default=.5)
    parser.add_argument('--reflection-trial',action='store_true',help='Compare 0/0.12/0.24 protected additive reflection strength; requires correct protected zones')
    args=parser.parse_args();config=poster.read(args.config)
    folder=Path(args.output) if args.output else poster.ROOT/'runs/harmonization'/uuid.uuid4().hex[:12]
    product_path=poster.ROOT/args.product
    if args.review_only:
        if not args.output or not (folder/'Provenance.json').is_file():raise ValueError('--review-only requires an existing output with provenance')
        if poster.read(folder/'Provenance.json')['product_sha256']!=hashlib.sha256(product_path.read_bytes()).hexdigest():raise ValueError('Review source product changed')
        if (folder/'VisualReview.json').exists():
            history=folder/('PreviousReview-'+uuid.uuid4().hex[:8]+'.json')
            history.write_bytes((folder/'VisualReview.json').read_bytes())
    else:
        with Image.open(product_path) as product,Image.open(poster.ROOT/args.background) as bg,Image.open(poster.ROOT/args.guide_before) as before,Image.open(poster.ROOT/args.guide) as guide:
            render_batch(config,folder,poster.read(poster.ROOT/args.spec),product,bg,poster.read(poster.ROOT/args.zones),before,guide,args.contour_contact,poster.read(args.spill_zones) if args.spill_zones else None,args.refine_alpha,poster.read(args.wrap_zones) if args.wrap_zones else None,args.contact_opacity,args.reflection_trial)
        poster.write(folder/'Provenance.json',{'product_sha256':hashlib.sha256(product_path.read_bytes()).hexdigest(),
            'spec_sha256':hashlib.sha256((poster.ROOT/args.spec).read_bytes()).hexdigest(),
            'guide_sha256':hashlib.sha256((poster.ROOT/args.guide).read_bytes()).hexdigest(),
            'guide_source':'previous actually executed ComfyUI appearance-edit trial; not another generation'})
        poster.write(folder/'Result.json',{'status':'UNREVIEWED','commercial_release_allowed':False})
    if args.review or args.review_only:
        try:
            review_batch(config,folder,product_path)
        except Exception as error:
            poster.write(folder/'Result.json',{'status':'REVIEW_FAILED','error_type':type(error).__name__,'commercial_release_allowed':False})
            raise
    poster.log('2D optimization:',folder)


if __name__=='__main__':main()
