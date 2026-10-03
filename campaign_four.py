"""Four directed beverage poster studies; fresh Comfy scenes and original product.

This is a guided art-direction experiment, not evidence of autonomous commercial PASS.
"""
import argparse
import copy
import hashlib
import math
from pathlib import Path
import uuid
from PIL import Image, ImageDraw
import poster
import harmonization


def review(folder):
    config=poster.read(poster.ROOT/'config.local.json')
    ids=['ice','diner','motion','sculpture']
    refs=['references/categories/beverage/f1cbf5fa14975844.jpg',
          'references/categories/beverage/66d09d8fb962ae89.jpg',
          'references/categories/beverage/f885fea5a325ffbb.webp']
    product=poster.ROOT/'samples/harmonization/beverage-clean-20261003/product.png'
    paths=[product,*[folder/id/'poster.png' for id in ids],*[poster.ROOT/ref for ref in refs]]
    prompt='''Review four complete beverage campaign poster studies, not background tests.
Image 1 original packshot; images 2-5 ice, diner, motion, sculpture in that order;
images 6-8 professional references for craft calibration, not copying.
Check the actual whole poster: coherent advertising idea, typography and copy, readability,
visual hierarchy, product integration, brand tone. Motion is intentional flat graphic
presentation; do not invent a floor requirement. Other three require convincing contact.
Look for generated nonsense lettering, frames, distracting props and pasted edges.
Product is retained source RGB at native 180x650; source has white-baked neck transmission.
Do not reward an invariant as quality or call this measured physical glass.
Proposed copy is creative demonstration, not an officially endorsed Coca-Cola campaign.
Return JSON {versions:[{id,scores:{product_fidelity,physical_integration,typography,
composition,brand_alignment,creative_coherence},problems:[{problem,evidence,repair}],
acceptable:boolean}],preferred:id,reason:string}. Exactly four versions, scores 0..100.
Acceptable requires fidelity>=95, physical>=88, typography>=88, composition>=88,
brand>=85, creative>=88 and no problems. Generated nonsense text, incorrect label,
cropped or unreadable text, photographic floating/light conflict are vetoes.
Do not inflate ratings for adding headlines. If none pass, clearly reject all.
Plans and actual geometry: '''+poster.json.dumps([
        {'id':id,'spec':poster.read(folder/id/'PosterSpec.json'),
        'geometry':poster.read(folder/id/'Geometry.json'),
        'actual_integration':poster.read(folder/id/'Integration.json'),
        'actual_parameters':poster.read(folder/id/'RenderParameters.json') if (folder/id/'RenderParameters.json').exists() else None} for id in ids],ensure_ascii=False)
    hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    value=poster.vision(config,prompt,paths,trace_path=folder/'Review-private-trace.json')
    if any(hashlib.sha256(path.read_bytes()).hexdigest()!=hashes[str(path)] for path in paths):raise ValueError('Review images changed during evaluation')
    poster.write(folder/'Review-image-hashes.json',hashes)
    poster.write(folder/'VisualReview.json',value)
    rows=value.get('versions',[]) if isinstance(value,dict) else []
    thresholds={'product_fidelity':95,'physical_integration':88,'typography':88,
                'composition':88,'brand_alignment':85,'creative_coherence':88}
    if len(rows)!=4 or {r.get('id') for r in rows}!=set(ids):raise ValueError('Four complete reviews required')
    approved=[]
    for r in rows:
        scores=r.get('scores',{})
        if set(scores)!=set(thresholds) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=100 for v in scores.values()):raise ValueError('Invalid campaign scores')
        if type(r.get('acceptable')) is not bool or not isinstance(r.get('problems'),list):raise ValueError('Explicit decisions required')
        if any(not isinstance(p,dict) or not p.get('problem') or not p.get('evidence') for p in r['problems']):raise ValueError('Visual problem evidence required')
        if r['acceptable'] and not r['problems'] and all(scores[k]>=limit for k,limit in thresholds.items()):approved.append(r['id'])
    if value.get('preferred') not in ids or not value.get('reason'):raise ValueError('Preference evidence required')
    result=poster.read(folder/'Result.json');result.update(status='MODEL_ACCEPTED_STUDY' if approved else 'NEEDS_REVIEW',
        model_accepted=approved,preferred=value['preferred'],commercial_release_allowed=False,
        release_limit='Guided creative study; limited packshot resolution; no commercial delivery acceptance.')
    poster.write(folder/'Result.json',result)
    poster.write(folder/'References.json',refs)


def plans():
    base = poster.read(poster.ROOT/'samples/harmonization/beverage-clean-20261003/SourceSpec.json')
    data = [
        ('ice', '冰爽凝结', '冰爽，即刻。', '打开这一刻', '#152a34',
         'Still life photograph of several small clear melting ice cubes on a pale blue icy marble surface, cubes grouped only at far left edge and bottom right corner, tiny water droplets, cold mist over a silver blue seamless wall, diffuse broad frontal illumination. Continuous horizontal marble plane across the lower third, completely empty central-right area. Quiet bright upper half. Straight-on camera. The only objects are small ice cubes. No drinking glasses, cups, vases, containers, products, lettering, people or logos.',
         (490, 635), (54, 85, 86, 700), (58, 210, 25), 'C:/Windows/Fonts/msyhbd.ttc', .69),
        ('diner', '复古餐馆', 'GOOD TIMES.', '相聚，总有好时光。', '#52251e',
         'An EMPTY American diner counter photographed straight-on for a nostalgic premium beverage campaign, cream and burgundy color palette, soft out-of-focus red vinyl booth and warm chrome details in the distant background, ivory laminate horizontal countertop across the lower third, diffuse frontal daylight with warm ambient tone, restrained analog film character; EMPTY clear standing spot at the right side of the counter, quiet cream wall at left and above. No products, containers, food, people, lettering, logos or studio equipment.',
         (575, 620), (55, 325, 88, 340), (59, 585, 25), 'C:/Windows/Fonts/georgiab.ttf', .70),
        ('motion', '红色动感', '停一下。', '让此刻，有滋有味。', '#fff7ee',
         'Extreme close-up photograph of deep vermilion and scarlet satin fabric swirling diagonally from lower left to upper right, full frame red fabric extending beyond every edge, tactile fluid folds, gentle motion blur only at outer edges, saturated coral smooth central-right zone and quiet deep red upper-left zone. Only abstract textile texture is visible. No border, white margins, letters, words, logos, labels, captions, objects or room.',
         (495, 650), (57, 90, 116, 690), (63, 248, 27), 'C:/Windows/Fonts/msyhbd.ttc', None),
        ('sculpture', '极简雕塑', '经典，自有形。', '一瓶，恰到好处。', '#42352d',
         'An EMPTY sculptural still-life advertising set, ivory limestone floor across lower third and warm off-white seamless wall, a large softly blurred arched travertine architectural recess at far left, meticulous fine stone texture, broad diffuse frontal daylight, soft shadow gradients, gallery-like calm and understated premium material; clear empty standing area at center-left on continuous horizontal floor, quiet right and upper wall for dark typography. No pedestal, products, containers, people, lettering, logos or equipment.',
         (275, 620), (48, 83, 74, 720), (470, 466, 25), 'C:/Windows/Fonts/msyh.ttc', .70),
    ]
    result=[]
    for index,(id,name,title,subtitle,ink,prompt,xy,t,sub,font,ground) in enumerate(data):
        s=copy.deepcopy(base);s['canvas']={'width':810,'height':1080};s['seed']=2026100311+index*101
        s['product'].update(x=xy[0],y=xy[1],width=180,height=650)
        s['background'].update(prompt=prompt,revision=0,shapes=[])
        s['scene_mode']='photographic' if ground is not None else 'graphic'
        for k in poster.TEXT_LAYERS:
            s[k].update(text='',x=55,y=1010,size=18,font=font,color=ink,tracking=0,max_width=0)
        s['title'].update(text=title,x=t[0],y=t[1],size=t[2],max_width=t[3],line_height=1.13)
        s['subtitle'].update(text=subtitle,x=sub[0],y=sub[1],size=sub[2],max_width=290,line_height=1.4,font='C:/Windows/Fonts/msyh.ttc')
        s['price'].update(text='COCA-COLA  /  ORIGINAL TASTE',x=55,y=1015,size=15,font='C:/Windows/Fonts/arial.ttf',tracking=1,max_width=690)
        if id=='diner':
            s['subtitle']['color']='#fff7ee';s['price']['color']='#fff7ee'
        s['shadow'].update(opacity=.4 if ground is not None else 0,blur=9,offset_x=0,offset_y=0)
        s['integration_plan'].update(source_key_light='front',cast_length_ratio=.025 if ground is not None else 0,cast_opacity=.10 if ground is not None else 0,cast_blur=16)
        result.append({'id':id,'name':name,'spec':s,'ground_top':ground})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output');parser.add_argument('--resume',action='store_true');parser.add_argument('--review-only',action='store_true');args=parser.parse_args()
    folder=Path(args.output) if args.output else poster.ROOT/'runs/campaign-four'/uuid.uuid4().hex[:12]
    if args.review_only:
        if not args.output or not (folder/'Result.json').is_file():parser.error('--review-only requires a completed --output directory')
        review(folder);return
    folder.mkdir(parents=True,exist_ok=args.resume)
    config=poster.read(poster.ROOT/'config.local.json');config['comfy_url']='http://127.0.0.1:8191'
    product_path=poster.ROOT/'samples/harmonization/beverage-clean-20261003/product.png'
    zones=poster.read(poster.ROOT/'samples/harmonization/beverage-clean-20261003/IdentityZones.json')
    all_plans=plans();poster.write(folder/'Plans.json',all_plans)
    with Image.open(product_path) as source:
        for p in all_plans:
            dest=folder/p['id'];dest.mkdir(exist_ok=args.resume);s=p['spec'];poster.validate(s)
            for k in poster.TEXT_LAYERS:
                if not poster.quality_module().font_supports_text(s[k]['font'],s[k]['text']):raise ValueError('Font lacks '+k+' glyphs')
            previous=poster.read(dest/'PosterSpec.json') if (dest/'PosterSpec.json').exists() else None
            if previous and (dest/'background.png').exists() and (previous['background']['prompt']!=s['background']['prompt'] or previous['seed']!=s['seed']):raise ValueError('Cannot reuse scene with changed scene plan')
            poster.write(dest/'PosterSpec.json',s)
            workflow=poster.read(poster.ROOT/config['background_workflow'])
            workflow['5']['inputs']['text']=s['background']['prompt'];workflow['8']['inputs']['seed']=s['seed']
            workflow['7']['inputs'].update(width=768,height=1024)
            poster.write(dest/'workflow.api.json',workflow);poster.log('Generating campaign scene:',p['id'])
            if not (args.resume and (dest/'background.png').exists()):
                poster.execute(config,workflow,config['background_output_node'],dest/'background.png')
            with Image.open(dest/'background.png') as bg:
                if p['ground_top'] is not None:
                    scene,final,audit=harmonization.compose(poster,s,source,bg,config['font'],zones,strength=0,
                        ground_top=p['ground_top'],contour_contact=True,refine_alpha=True,contact_opacity=.56,cast_ratio=.025)
                else:
                    final=poster.render(s,source,config['font'],bg);blank=copy.deepcopy(s)
                    for k in poster.TEXT_LAYERS:blank[k]['text']=''
                    scene=poster.render(blank,source,config['font'],bg)
                    audit={'scene_mode':'graphic','physical_floor_not_claimed':True,'generated_product_RGB_copied':False}
                scene.save(dest/'scene.png');final.save(dest/'poster.png');poster.write(dest/'Integration.json',audit)
                geometry=poster.rendered_geometry(s,product_path,config['font']);poster.write(dest/'Geometry.json',geometry)
    board=Image.new('RGB',(1620,1130),'#ece7de')
    for index,p in enumerate(all_plans):
        im=Image.open(folder/p['id']/'poster.png');im.thumbnail((405,540));board.paste(im,(index*405,45))
        ImageDraw.Draw(board).text((index*405+12,12),p['id'],fill='#333333',font_size=20)
    board=board.crop((0,0,1620,585));board.save(folder/'overview.png')
    poster.write(folder/'Result.json',{'status':'UNREVIEWED','commercial_release_allowed':False,'guided_direction':True,
        'product_sha256':hashlib.sha256(product_path.read_bytes()).hexdigest(),'actual_scene_generations':4,
        'source_limitations':'Native cropped 180x650 packshot; baked white glass transmission, limited print resolution.'})
    poster.log('Campaign outputs:',folder)


if __name__=='__main__':main()
