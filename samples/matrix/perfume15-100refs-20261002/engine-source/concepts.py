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
            record={k:item[k] for k in ('name','brief','material','lighting','palette','signature','layout_relation') if k in item}
            if item.get('initial_spec'):
                spec=item['initial_spec']
                record['layout']={k:spec[k] for k in ('canvas','product','title','background')}
            result.append(record)
    return result


def build_spec(engine,config,item,product,approved_copy):
    """Convert model-chosen normalized geometry; no lookup of curated grids."""
    spec=engine.read(engine.ROOT/'examples/PosterSpec.json')
    spec['scene_mode']=item.get('scene_mode','photographic')
    w,h=spec['canvas']['width'],spec['canvas']['height']
    def numbers(values,length):
        if not isinstance(values,list) or len(values)!=length or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in values):
            raise ValueError('Concept coordinates must be finite numeric arrays')
        return values
    x,y,ratio=numbers(item['product'],3)
    with engine.Image.open(product) as image:
        bounds=image.getchannel('A').getbbox()
    if bounds is None:raise ValueError('Empty product cutout')
    aspect=(bounds[2]-bounds[0])/(bounds[3]-bounds[1])
    requested={'x':round(x*w),'y':round(y*h),'height':round(ratio*h)}
    height=min(requested['height'],int((w*.9-4)/aspect),int(h*.74))
    if height<h*.35:raise ValueError('Requested product too small for safe hero layout')
    width=round(height*aspect)+2
    cx=round(max(w*.05+width/2,min(w*.95-width/2,requested['x'])))
    cy=round(max(h*.10+height/2,min(h*.94-height/2,requested['y'])))
    spec['product']={'x':cx,'y':cy,'width':width,'height':height}
    if any(spec['product'][k]!=v for k,v in requested.items()):
        spec['layout_fit']={'requested_product':requested,'reason':'fit_actual_cutout_aspect_within_canvas_safe_area'}
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
        style=item['type'].get('styles',{}).get(name,{})
        if not isinstance(style,dict) or set(style)-{'font','tracking','max_width','line_height','align'}:
            raise ValueError('Unsupported text style')
        spec[name].update(style)
    spec['shadow'].update(kind='contact',offset_x=0,offset_y=0,opacity=.35,blur=10)
    spec['decoration']['enabled']=False
    line=item.get('line')
    if line is not None:
        lx,ly,length=numbers(line,3)
        if not 0<=lx<=1 or not 0<=ly<=1 or not 0<=length<=1 or lx+length>1:raise ValueError('Decorative line outside canvas')
        spec['decoration'].update(enabled=True,x=round(lx*w),y=round(ly*h),width=round(length*w),color=palette[2] if len(palette)>2 else palette[1])
    return spec


def title_relationship(geometry):
    title=geometry['text_bbox'].get('title')
    if title is None:raise ValueError('A visible title is required to assess layout diversity')
    product=geometry['product_bbox']
    if title[3]<=product[1]:return 'above'
    if title[1]>=product[3]:return 'below'
    if title[2]<=product[0] or title[0]>=product[2]:return 'beside'
    raise ValueError('Title must have a clear safe spatial relation to the product')


def title_family(font):
    return 'serif' if font.replace('\\','/').rsplit('/',1)[-1].lower() in ('times.ttf','georgia.ttf','bod_r.ttf','baskvill.ttf') else 'sans'


def validate_plans(engine, config, value, product, references, approved_copy):
    items = value.get('directions')
    if not isinstance(items,list) or len(items)!=4:
        raise ValueError('Exactly four new concepts required')
    lookup = {r['id']:r for r in references}
    previous={d['signature'] for d in recent(engine.ROOT) if 'signature' in d}
    directions, grids, colors, fonts, materials, relations = [], set(), set(), set(), set(), set()
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
        try:
            spec,_=engine.prepare_layout({**config,'direction_id':f'concept-{index}'},spec,product)
        except ValueError as error:
            try:geometry=engine.rendered_geometry(spec,product,config['font'])
            except ValueError:geometry={'product':spec['product'],'text':'text frame cannot fit words'}
            raise ValueError(f'Concept {index} ({item["name"]}): {error}. Actual geometry: {json.dumps(geometry)}. '
                'For a side layout reduce visible height of a wide cutout toward35% to free a real text column; resizing type alone cannot fix text origins inside the product.') from error
        w,h=spec['canvas']['width'],spec['canvas']['height']
        geometry=engine.rendered_geometry(spec,product,config['font'])
        relation=title_relationship(geometry);relations.add(relation)
        grid=(round(spec['product']['x']/w,1),round(spec['product']['y']/h,1),
              round(geometry['product_height_ratio'],1),round(spec['title']['x']/w,1),round(spec['title']['y']/h,1))
        grids.add(grid)
        rgb=engine.ImageColor.getrgb(spec['background']['color'])
        colors.add(tuple(c//64 for c in rgb[:3]))
        font=spec['title'].get('font',config['font']);fonts.add(title_family(font))
        signature=hashlib.sha256(json.dumps([grid,tuple(c//64 for c in rgb[:3]),font]).encode()).hexdigest()
        if signature in previous:raise ValueError('Concept repeats a recent geometry/color/font signature; invent a new design instead of changing its seed or name')
        materials.add(item['material'].strip().casefold())
        directions.append({**{k:item[k] for k in ('name','brief','material','lighting')},
            'id':f'concept-{index}','signature':signature,'scene_mode':spec.get('scene_mode','photographic'),'layout_relation':relation,'title_family':title_family(font),'palette':spec.get('palette',[]),'reference_ids':ids,'initial_spec':spec})
    if len({d['name'].strip().casefold() for d in directions})!=4 or len(grids)<3 or len(colors)<3 or len(fonts)<2 or len(materials)<3:
        raise ValueError('Concepts repeat: require four names, >=3 geometry grids, >=3 coarse background colors, both serif and sans title families and >=3 materials; color swaps alone are insufficient')
    if relations!={'above','below','beside'}:
        raise ValueError('Layout topology repeats: four concepts must include title ABOVE, BELOW and BESIDE the visible product. Moving upper titles by a few pixels is not a new layout. Reposition/resize the product and text together so every design remains safe; choose your own coordinates, no preset grids.')
    return directions


def plan_four(engine,config,product,brief,folder,approved_copy):
    store=engine.reference_store_module()
    pool=store.planning_pool(engine.ROOT,limit=8) if hasattr(store,'planning_pool') else store.entries(engine.ROOT)
    if not hasattr(store,'planning_pool'):random.SystemRandom().shuffle(pool)
    refs=[];brands=set()
    for row in pool:
        if row['brand'] not in brands:
            refs.append(row);brands.add(row['brand'])
        if len(refs)==8:break
    if len(refs)<3:raise ValueError('At least three reference brands required')
    engine.write(folder/'Planning-references.json',refs)
    history=recent(engine.ROOT)
    with engine.Image.open(product) as image:bounds=image.getchannel('A').getbbox()
    aspect=(bounds[2]-bounds[0])/(bounds[3]-bounds[1])
    type_metrics={}
    for font in engine.FONT_CHOICES:
        type_metrics[font]={}
        for layer,text in approved_copy.items():
            if text:
                box=engine.ImageFont.truetype(font,64).getbbox(text)
                type_metrics[font][layer]={'width_at_64px':box[2]-box[0],'height_at_64px':box[3]-box[1]}
    prompt=('Develop FOUR genuinely different fresh commercial perfume campaign concepts for this product. '
        'Do not reuse the fixed black/gold, cream, burgundy, botanical quartet, nor reproduce the recent plans. '
        'Explore different spatial hierarchy, typography, material, light and visual narrative; random color swaps are insufficient. '
        'Keep the original single upright packshot; no rotation, cropping, generated duplicate, relighting or replaced label. '
        'Renderer supports generated backdrop, original cutout, measured contact shadow, editable line decoration and tracked/wrapped typography. '
        'Do not demand features absent from the renderer. You may use graphic, tactile, architectural or experimental empty backdrops. '
        'Background prompt describes ONLY background materials/shapes/illumination. Never use words perfume, fragrance, bottle, product, '
        'logo, label, people, person, woman, man, model, table, tabletop, pedestal, plinth, platform, even in negative phrases. '
        'No raised support, visible light equipment or extra text. Match the ACTUAL product photograph and its observation profile, never assume dark glass or frontal light. '
        'A material texture alone is not a campaign idea. Develop distinct narratives through light, bold graphic shapes, natural forms, spatial hierarchy and typography. '
        'Avoid four variations of a bottle on a wall texture. In photographic scenes, show a believable horizontal continuous ground at the actual base position; all text areas need calm negative space. '
        'Declare scene_mode=graphic for a flat graphic campaign: it needs intentional shapes and silhouette integration but no photographic floor/horizon. '
        'Declare photographic for a real environment with matched illumination and convincing ground. Do not confuse a flat poster with a badly integrated photograph. '
        'Product x/y=center; text x/y=upper-left. Actual visible height can be 35-74% of canvas; keep its top >=10%, base <=94%, '
        'sides within 5-95%. Text within x4-96%, y3.5-97%, no text/text or text/product overlap, separation >=2.5%. '
        'Choose at least 3 distinct geometry grids, 3 clearly different background color families, both serif (Times/Georgia/Bodoni/Baskerville) and sans (Arial/Arial Narrow/Century Gothic/MSYH) title families, 3 materials. '
        'The four layouts MUST include all THREE spatial relationships: title ABOVE product, title BELOW product, and title BESIDE product with vertical overlap but horizontal separation. '
        'An upper-left title is still ABOVE if it ends above the product top; shifting it sideways does not count as BESIDE. '
        'Choose your own coordinates and sizes. For lower titles move the product upward and reserve a lower text band; for a side title use a deliberate wrapped column instead of making a long name tiny. '
        'Fonts only '+json.dumps(engine.FONT_CHOICES)+'. Return compact JSON {directions:[{name,brief,material,lighting,scene_mode:graphic/photographic,reference_ids:[3 supplied IDs with distinct brands],'
        'palette:[background color,ink color,accent color],product:[center_x_fraction,center_y_fraction,visible_height_fraction],'
        'type:{font:approved font path,title:[x_fraction,y_fraction,font_size_px],logo:[x_fraction,y_fraction,font_size_px],subtitle:[x_fraction,y_fraction,font_size_px],'
        'styles:{title:{font,tracking,max_width,line_height,align},logo:{tracking},subtitle:{tracking}}},'
        'background_prompt:string,line:null OR [x_fraction,y_fraction,width_fraction]}]}. '
        'Canvas is 1080x1440; positions are fractions of canvas width/height, font sizes are pixel values 16..240. '
        'styles fields are optional: tracking pixels -1..24 (restrained letterspacing for small uppercase), max_width pixels 0=single line otherwise wordwrap up to4 lines, line_height1..2 default1.15, align left/center/right. '
        'Different text layers can use different approved font families. Never rewrite approved words. If approved price is nonempty also supply type.price in the same coordinate format. Colors must be CSS hex colors. '
        'Do not output full PosterSpecs or repeated schema fields. Every creative position, size, palette and material is YOUR decision, not a preset. '
        'Measured visible cutout width/height ratio: '+str(round(aspect,5))+'. Product width fraction equals height_fraction * (1440/1080) * this ratio. '
        'ABSOLUTE maximum allowed visible height fraction for this actual width is '+str(round(min(.74,.89*1080/(1440*aspect)),3))+'. '
        'For a side column reserve enough width for BOTH the full cutout and text; a wide triangular/star bottle may need height near35%, not60%. '
        'Measured text bounds at 64px (scale approximately by requested_size/64), use these to fit side columns and lower title bands: '+json.dumps(type_metrics)+'. '
        'Tracking adds approximately (character_count-1)*tracking pixels to every line; account for it especially in long brand names. '
        'Brief: '+json.dumps(brief,ensure_ascii=False)+' Approved copy: '+json.dumps(approved_copy,ensure_ascii=False)+
        ' Actual product observation: '+json.dumps(config.get('product_profile',{}),ensure_ascii=False)+
        ' Recent plans to avoid: '+json.dumps(history,ensure_ascii=False)+
        ' Reference analyses: '+json.dumps(refs,ensure_ascii=False))
    planning=copy.deepcopy(config)
    planning['vision_options']={**config.get('vision_options',{}),'temperature':.8}
    if planning['vision_options'].get('enable_thinking'):
        planning['vision_options']['thinking_budget']=4096
    token_key='max_completion_tokens' if 'max_completion_tokens' in planning['vision_options'] else 'max_tokens'
    planning['vision_options'][token_key]=max(12288,planning['vision_options'].get(token_key,0))
    value=engine.vision(planning,prompt,[product,*[engine.ROOT/r['image'] for r in refs]],folder/'Concepts-call.json')
    for attempt in range(3):
        try:
            plans=validate_plans(engine,config,value,product,refs,approved_copy)
            break
        except (ValueError,KeyError,TypeError) as error:
            if attempt==2:raise
            trace='Concepts-repair-call.json' if attempt==0 else 'Concepts-repair-2-call.json'
            value=engine.vision(planning,prompt+' Repair these plans without reverting to a fixed template. Preserve valid concepts; correct the failing geometry in its named concept. Return all four. Validation error: '+str(error)+
                ' Invalid plans: '+json.dumps(value,ensure_ascii=False),[product,*[engine.ROOT/r['image'] for r in refs]],folder/trace)
    engine.write(folder/'Concepts.json',plans)
    return plans,refs
