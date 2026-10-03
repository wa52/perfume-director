"""Opt-in Commercial V2 contracts. Never infer approval from missing evidence."""
import copy
import math
from PIL import Image, ImageFilter

THRESHOLDS = {'product_fidelity':95, 'physical_integration':88, 'typography':88,
              'composition':88, 'brand_alignment':85, 'creative_coherence':88}
CHECKS = ('logo_correct','shape_preserved','grounding_correct','edges_clean',
          'lighting_consistent','text_uncropped','text_collision_free','fonts_present','brand_spelling_correct')


def validate_creative(value):
    if not isinstance(value,dict) or not isinstance(value.get('brand_analysis'),dict):
        raise ValueError('Brand analysis required')
    brand=value['brand_analysis']
    if set(brand)!={'observed_brand','evidence','expression_hypothesis','unknowns'} or any(not isinstance(v,str) or not v.strip() or len(v)>2000 for v in brand.values()):
        raise ValueError('Brand analysis requires observed brand, evidence, expression hypothesis and unknowns as strings')
    items=value.get('concepts')
    if not isinstance(items,list) or len(items)!=4:raise ValueError('Four advertising propositions required')
    ids=set();mechanisms=set()
    allowed={'id','name','proposition','visual_mechanism','audience','brand_connection','source_constraints'}
    for item in items:
        if not isinstance(item,dict) or set(item)!=allowed:raise ValueError('Creative concepts contain only intent, never coordinates or layout')
        for field in allowed:
            if not isinstance(item[field],str) or not 2<=len(item[field])<=1400:raise ValueError('Invalid creative '+field)
        ids.add(item['id']);mechanisms.add(' '.join(item['visual_mechanism'].casefold().split()))
    if len(ids)!=4 or len(mechanisms)!=4:raise ValueError('Repeated creative IDs or visual mechanisms')
    return value


def creative_stage(engine,config,product,brief,folder,approved_copy):
    prompt=('Act as Brand Analyst then Creative Director, before any layout. Return '
        '{brand_analysis:{observed_brand,evidence,expression_hypothesis,unknowns},concepts:[four objects '
        '{id,name,proposition,visual_mechanism,audience,brand_connection,source_constraints}]}. '
        'All brand analysis and concept fields are nonempty strings (unknowns is a string); IDs unique. Four genuinely different advertising propositions and visual mechanisms, '
        'not four palettes, textures, camera crops or title placements. A contour portrait, honest portrait, cap portrait '
        'and minimal portrait on four neutral floors are ONE advertising idea, not four. '
        'The visual_mechanism field must explain what visual event conveys the proposition, never instructions about '
        'where to place the cutout, title, or negative space. At least three genuinely different visual events, '
        'not product isolation repeated with different scales. No coordinates, fonts, sizes, grids or PosterSpecs. '
        'Separate visible facts from a proposed campaign expression; brand history is unknown without supplied evidence. '
        'Do not invent slogans or factual claims. Work with approved words only. The execution currently preserves the '
        'entire original cutout, labels, shape and RGB illumination; it cannot reconstruct glass transmission, relight material zones, '
        'add droplets on the product, change pose or generate people. Concepts must be feasible with that limitation, '
        'a generated empty set, floor cast/contact shadows and deterministic typography. '
        'Brief: '+engine.json.dumps(brief,ensure_ascii=False)+' Copy: '+engine.json.dumps(approved_copy,ensure_ascii=False)+
        ' Observed source: '+engine.json.dumps(config.get('product_profile',{}),ensure_ascii=False))
    value=engine.vision(config,prompt,[product],folder/'Creative-call.json')
    for attempt in range(3):
        try:
            validate_creative(value)
            review=semantic_review(engine,config,product,value,folder/f'CreativeReview-{attempt+1}.json')
            engine.write(folder/'CreativeGate.json',{'pass':review['distinct'],'review':review,
                'concept_sha256':engine.hashlib.sha256(engine.json.dumps(value,sort_keys=True).encode()).hexdigest()})
            if not review['distinct']:raise ValueError('Advertising propositions collapse: '+engine.json.dumps(review))
            break
        except ValueError as error:
            if attempt==2:raise
            value=engine.vision(config,prompt+' Repair creative diversity and contract: '+str(error)+' Previous: '+engine.json.dumps(value),[product],folder/f'Creative-repair-{attempt+1}-call.json')
    engine.write(folder/'CreativeConcepts.json',value)
    return value


def semantic_review(engine,config,product,value,trace):
    review=engine.vision(config,
        'Act as a skeptical advertising creative reviewer. Independently compare these four propositions. '
        'Return {distinct:boolean,evidence:string,collapse_groups:[[IDs]],required_revision:string}. '
        'Require four materially different advertising ideas; differently sized/positioned portraits, neutral studio floors, '
        'different title columns, palettes or renamed materials do not constitute different concepts. '
        'Contour signature, everyday companion, cap monument, restrained portrait all collapse into one isolated packshot idea '
        'if their actual visual event is the same. Judge the described visual mechanisms, not eloquent names. '
        'Reject impossible product modifications as well. Do not propose new slogans, factual brand history or unsupported relighting. '
        'Campaigns may use source-compatible photographic context, abstract visual metaphor, purposeful brand graphics or an editorial narrative; '
        'these are possibilities, not four compulsory templates. Concepts: '+engine.json.dumps(value,ensure_ascii=False),[product],trace)
    if not isinstance(review,dict) or type(review.get('distinct')) is not bool or not isinstance(review.get('evidence'),str) or not review['evidence'].strip() or not isinstance(review.get('collapse_groups'),list):
        raise ValueError('Creative semantic review requires explicit decision and evidence')
    if review['collapse_groups']:review['distinct']=False
    return review


def validate_integration(plan):
    if not isinstance(plan,dict) or set(plan)!={'source_key_light','ground_material','cast_length_ratio','cast_opacity','cast_blur'}:
        raise ValueError('Integration plan requires observed light, ground and bounded cast shadow')
    if plan['source_key_light'] not in ('left','right','front','overhead','unknown'):raise ValueError('Invalid source light')
    if not isinstance(plan['ground_material'],str) or not 2<=len(plan['ground_material'])<=300:raise ValueError('Invalid ground material')
    for name,low,high in [('cast_length_ratio',0,.20),('cast_opacity',0,.3),('cast_blur',2,60)]:
        value=plan[name]
        if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid '+name)
    if plan['source_key_light']=='unknown' and plan['cast_opacity']!=0:raise ValueError('Unknown source light cannot authorize a directional shadow')
    return plan


def cast_shadow(canvas,product,px,py,plan):
    """Project existing alpha onto the floor; never repaint original RGB or label."""
    validate_integration(plan)
    if not plan['cast_opacity'] or not plan['cast_length_ratio']:return canvas
    length=max(1,canvas.height*plan['cast_length_ratio'])
    dx={'left':length*.6,'right':-length*.6,'front':0,'overhead':0,'unknown':0}[plan['source_key_light']]
    # Camera-side frontal light casts away from the viewer, not toward them.
    if plan['source_key_light']=='front':length=-length
    base=py+product.height
    transform=(1,-dx/length,-px+base*dx/length,0,-product.height/length,product.height+base*product.height/length)
    alpha=product.getchannel('A').transform(canvas.size,Image.Transform.AFFINE,transform,Image.Resampling.BILINEAR)
    alpha=alpha.point(lambda a:round(a*plan['cast_opacity'])).filter(ImageFilter.GaussianBlur(plan['cast_blur']))
    layer=Image.new('RGBA',canvas.size,(0,0,0,0));layer.putalpha(alpha)
    return Image.alpha_composite(canvas,layer)


def gate(result,geometry_issues=()):
    result=copy.deepcopy(result)
    dimensions=result.get('dimensions',{});checks=result.get('commercial_checks',{})
    failures=[]
    for name,minimum in THRESHOLDS.items():
        score=dimensions.get(name)
        if type(score) not in (int,float) or not math.isfinite(score) or not minimum<=score<=100:
            failures.append('dimension:'+name)
    for name in CHECKS:
        item=checks.get(name) if isinstance(checks,dict) else None
        if not isinstance(item,dict) or item.get('ok') is not True or not isinstance(item.get('evidence'),str) or not item['evidence'].strip():
            failures.append('check:'+name)
    failures.extend('geometry:'+issue for issue in geometry_issues)
    if result.get('problems') or result.get('changes'):failures.append('unresolved_review')
    if result.get('pass') is not True:failures.append('critic_not_approved')
    result['commercial_gate']={'version':2,'pass':not failures,'failures':failures,'thresholds':THRESHOLDS,
        'basis':'visual-model evidence plus deterministic geometry; not independent human commercial certification'}
    result['pass']=not failures
    return result


def review_contract():
    return (' Commercial V2: additionally score dimensions.brand_alignment; evaluate against supplied brand evidence, not invented brand history. '
        'Return commercial_checks with EVERY key '+str(CHECKS)+', each {ok:boolean,evidence:string}; unknown or unverifiable means ok:false. '
        'A graphic design can be intentionally suspended: grounding_correct then evaluates declared presentation, not an invented floor. '
        'For every problem include root_cause, affected_layer (scene/product/shadow/typography/brand), and repair_strategy. '
        'Do not assert that a guessed horizon is a contact plane; judge visible physical evidence. '
        'Current renderer preserves original RGB: do not request unsupported true relighting, glass reconstruction or label edits. '
        'For source/background light conflict regenerate the scene to match the source. '
        'Bounded external cast-shadow patches allowed: integration_plan.cast_length_ratio (0..0.20), integration_plan.cast_opacity (0..0.3), integration_plan.cast_blur (2..60); preserve observed source_key_light and ground material. '
        'PASS requires thresholds '+str(THRESHOLDS)+' and every commercial check true with evidence, no remaining problems/changes. '
        'Missing evidence is a veto even at a high average score. ')
