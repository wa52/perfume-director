"""Plan fresh visual concepts; safety checks never substitute a curated design."""
import copy
import hashlib
import json
import math
import random
from pathlib import Path


def recent(root):
    files = sorted((root/'runs/batches').glob('*/request.json'), key=lambda p:p.stat().st_mtime, reverse=True)
    result = []
    for path in files[:8]:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        for item in data.get('directions', []):
            record={k:item[k] for k in ('name','brief','material','lighting','palette','signature') if k in item}
            if item.get('initial_spec'):
                spec=item['initial_spec']
                record['layout']={k:spec[k] for k in ('canvas','product','title','background')}
            result.append(record)
    return result


def build_spec(engine,config,item,product,approved_copy):
    """Convert model-chosen normalized geometry; no lookup of curated grids."""
    spec=engine.read(engine.ROOT/'examples/PosterSpec.json')
    w,h=spec['canvas']['width'],spec['canvas']['height']
    def numbers(values,length):
        if not isinstance(values,list) or len(values)!=length or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
            raise ValueError('Concept coordinates must be finite numeric arrays')
        return values
    x,y,ratio=numbers(item['product'],3)
    with engine.Image.open(product) as image:
        bounds=image.getchannel('A').getbbox()
    if bounds is None:raise ValueError('Empty product cutout')
    height=round(ratio*h)
    spec['product']={'x':round(x*w),'y':round(y*h),'width':round(height*(bounds[2]-bounds[0])/(bounds[3]-bounds[1]))+2,'height':height}
    palette=item['palette']
    if not isinstance(palette,list) or not 2<=len(palette)<=6 or any(not isinstance(c,str) for c in palette):raise ValueError('Concept palette must contain 2-6 colors')
    for color in palette:engine.ImageColor.getrgb(color)
    spec['palette']=palette;spec['lighting']=item['lighting']
    spec['background'].update(color=palette[0],prompt=item['background_prompt'],revision=0)
    font=item['type']['font']
    for name in engine.TEXT_LAYERS:
        spec[name]['text']=approved_copy[name]
        spec[name].update(font=font,color=palette[1])
        if name in item['type']:
            tx,ty,size=numbers(item['type'][name],3)
            spec[name].update(x=round(tx*w),y=round(ty*h),size=size)
        elif spec[name]['text']:raise ValueError('Missing concept position for '+name)
    spec['shadow'].update(kind='contact',offset_x=0,offset_y=0,opacity=.35,blur=10)
    spec['decoration']['enabled']=False
    line=item.get('line')
    if line is not None:
        lx,ly,length=numbers(line,3)
        if not 0<=lx<=1 or not 0<=ly<=1 or not 0<=length<=1 or lx+length>1:raise ValueError('Decorative line outside canvas')
        spec['decoration'].update(enabled=True,x=round(lx*w),y=round(ly*h),width=round(length*w),color=palette[1])
    return spec


def validate_plans(engine, config, value, product, references, approved_copy):
    items = value.get('directions')
    if not isinstance(items,list) or len(items)!=4:
        raise ValueError('Exactly four new concepts required')
    lookup = {r['id']:r for r in references}
    previous={d['signature'] for d in recent(engine.ROOT) if 'signature' in d}
    directions, grids, colors, fonts, materials = [], set(), set(), set(), set()
    for index,item in enumerate(items,1):
        for field in ('name','brief','material','lighting'):
            if not isinstance(item.get(field),str) or not 2 <= len(item[field]) <= 1400:
                raise ValueError('Invalid concept '+field)
        ids=item.get('reference_ids')
        if not isinstance(ids,list) or len(ids)!=3 or any(not isinstance(i,str) or i not in lookup for i in ids) or len(set(ids))!=3:
            raise ValueError('Each concept requires three supplied reference IDs')
        if len({lookup[i]['brand'] for i in ids})!=3:
            raise ValueError('Reference brands must differ')
        spec=copy.deepcopy(item['spec']) if 'spec' in item else build_spec(engine,config,item,product,approved_copy)
        for layer,text in approved_copy.items():spec[layer]['text']=text
        for layer in engine.TEXT_LAYERS:
            if spec[layer].get('font',config['font']) not in engine.FONT_CHOICES:
                raise ValueError('Concept font must be an approved installed font')
        engine.validate(spec)
        engine.check_concept_background(spec['background']['prompt'])
        spec,_=engine.prepare_layout({**config,'direction_id':f'concept-{index}'},spec,product)
        w,h=spec['canvas']['width'],spec['canvas']['height']
        geometry=engine.rendered_geometry(spec,product,config['font'])
        grid=(round(spec['product']['x']/w,1),round(spec['product']['y']/h,1),
              round(geometry['product_height_ratio'],1),round(spec['title']['x']/w,1),round(spec['title']['y']/h,1))
        grids.add(grid)
        rgb=engine.ImageColor.getrgb(spec['background']['color'])
        colors.add(tuple(c//64 for c in rgb[:3]))
        font=spec['title'].get('font',config['font']);fonts.add(font)
        signature=hashlib.sha256(json.dumps([grid,tuple(c//64 for c in rgb[:3]),font]).encode()).hexdigest()
        if signature in previous:raise ValueError('Concept repeats a recent geometry/color/font signature; invent a new design instead of changing its seed or name')
        materials.add(item['material'].strip().casefold())
        directions.append({**{k:item[k] for k in ('name','brief','material','lighting')},
            'id':f'concept-{index}','signature':signature,'palette':spec.get('palette',[]),'reference_ids':ids,'initial_spec':spec})
    if len({d['name'].strip().casefold() for d in directions})!=4 or len(grids)<3 or len(colors)<3 or len(fonts)<2 or len(materials)<3:
        raise ValueError('Concepts repeat: require four names, >=3 geometry grids, >=3 coarse background colors, >=2 title fonts and >=3 materials; color swaps alone are insufficient')
    return directions


def plan_four(engine,config,product,brief,folder,approved_copy):
    pool=engine.reference_store_module().entries(engine.ROOT)
    random.SystemRandom().shuffle(pool)
    refs=[];brands=set()
    for row in pool:
        if row['brand'] not in brands:
            refs.append(row);brands.add(row['brand'])
        if len(refs)==6:break
    if len(refs)<3:raise ValueError('At least three reference brands required')
    engine.write(folder/'Planning-references.json',refs)
    history=recent(engine.ROOT)
    prompt=('Develop FOUR genuinely different fresh commercial perfume campaign concepts for this product. '
        'Do not reuse the fixed black/gold, cream, burgundy, botanical quartet, nor reproduce the recent plans. '
        'Explore different spatial hierarchy, typography, material, light and visual narrative; random color swaps are insufficient. '
        'Keep the original single upright packshot; no rotation, cropping, generated duplicate, relighting or replaced label. '
        'Renderer supports generated backdrop, original cutout, contact shadow, one thin line decoration and single-line text. '
        'Do not demand features absent from the renderer. You may use graphic, tactile, architectural or experimental empty backdrops. '
        'Background prompt describes ONLY background materials/shapes/illumination. Never use words perfume, fragrance, bottle, product, '
        'logo, label, people, person, woman, man, model, table, tabletop, pedestal, plinth, platform, even in negative phrases. '
        'No raised support, visible light equipment or extra text. Match broad soft frontal light on the existing dark glass. '
        'Product x/y=center; text x/y=upper-left. Actual visible height can be 35-74% of canvas; keep its top >=10%, base <=94%, '
        'sides within 5-95%. Text within x4-96%, y3.5-97%, no text/text or text/product overlap, separation >=2.5%. '
        'Choose at least 3 distinct geometry grids, 3 clearly different background color families, 2 title fonts, 3 materials. '
        'Fonts only '+json.dumps(engine.FONT_CHOICES)+'. Return compact JSON {directions:[{name,brief,material,lighting,reference_ids:[3 supplied IDs with distinct brands],'
        'palette:[background color,ink color,accent color],product:[center_x_fraction,center_y_fraction,visible_height_fraction],'
        'type:{font:approved font path,title:[x_fraction,y_fraction,font_size_px],logo:[x_fraction,y_fraction,font_size_px],subtitle:[x_fraction,y_fraction,font_size_px]},'
        'background_prompt:string,line:null OR [x_fraction,y_fraction,width_fraction]}]}. '
        'Canvas is 1080x1440; positions are fractions of canvas width/height, font sizes are pixel values 16..240. '
        'If approved price is nonempty also supply type.price in the same coordinate format. Colors must be CSS hex colors. '
        'Do not output full PosterSpecs or repeated schema fields. Every creative position, size, palette and material is YOUR decision, not a preset. '
        'Brief: '+json.dumps(brief,ensure_ascii=False)+' Approved copy: '+json.dumps(approved_copy,ensure_ascii=False)+
        ' Recent plans to avoid: '+json.dumps(history,ensure_ascii=False)+
        ' Reference analyses: '+json.dumps(refs,ensure_ascii=False))
    planning=copy.deepcopy(config)
    planning['vision_options']={**config.get('vision_options',{}),'temperature':.8}
    token_key='max_completion_tokens' if 'max_completion_tokens' in planning['vision_options'] else 'max_tokens'
    planning['vision_options'][token_key]=max(8192,planning['vision_options'].get(token_key,0))
    value=engine.vision(planning,prompt,[product,*[engine.ROOT/r['image'] for r in refs]],folder/'Concepts-call.json')
    try:
        plans=validate_plans(engine,config,value,product,refs,approved_copy)
    except (ValueError,KeyError,TypeError) as error:
        value=engine.vision(planning,prompt+' Repair these plans without reverting to a fixed template. Validation error: '+str(error)+
            ' Invalid plans: '+json.dumps(value,ensure_ascii=False),[product,*[engine.ROOT/r['image'] for r in refs]],folder/'Concepts-repair-call.json')
        plans=validate_plans(engine,config,value,product,refs,approved_copy)
    engine.write(folder/'Concepts.json',plans)
    return plans,refs
