"""Opt-in Commercial V2 contracts. Never infer approval from missing evidence."""
import copy
import math
from PIL import Image, ImageFilter

THRESHOLDS = {'product_fidelity':95, 'physical_integration':88, 'typography':88,
              'composition':88, 'brand_alignment':85, 'creative_coherence':88}
CHECKS = ('logo_correct','shape_preserved','grounding_correct','edges_clean',
          'lighting_consistent','text_uncropped','text_collision_free','fonts_present','brand_spelling_correct',
          'copy_concept_specific','visual_memory_visible')


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
        'copy_concept_specific checks whether words express THIS visual proposition rather than interchangeable slogans. '
        'visual_memory_visible requires an identifiable memorable relationship/event actually visible in the poster, not merely a beautiful texture or prose intent. '
        'A graphic design can be intentionally suspended: grounding_correct then evaluates declared presentation, not an invented floor. '
        'For every problem include root_cause, affected_layer (scene/product/shadow/typography/brand), and repair_strategy. '
        'Do not assert that a guessed horizon is a contact plane; judge visible physical evidence. '
        'Current renderer preserves original RGB: do not request unsupported true relighting, glass reconstruction or label edits. '
        'For source/background light conflict regenerate the scene to match the source. '
        'When the visual event needs the exact product contour, use a bounded background.shapes product_silhouette primitive derived from original alpha, not a guessed generated vessel. '
        'It accepts the same x,y,width,height,color,opacity fields in canvas pixels, fits source aspect ratio inside width/height anchored at x/y; set background.prompt to EMPTY materials/light to remove any previously generated wrong contour. '
        'Bounded external cast-shadow patches allowed: integration_plan.cast_length_ratio (0..0.20), integration_plan.cast_opacity (0..0.3), integration_plan.cast_blur (2..60); preserve observed source_key_light and ground material. '
        'PASS requires thresholds '+str(THRESHOLDS)+' and every commercial check true with evidence, no remaining problems/changes. '
        'Missing evidence is a veto even at a high average score. ')


def final_art_repair(engine,config,spec,product,poster,refs,folder,decision):
    """Translate an independent veto into bounded edits, never an approval."""
    prompt=(
        'The independent Commercial Art Director rejected this rendered poster. Convert its actual root causes into supported PosterSpec patches. '
        'Return {changes:[{path,op,value}]}. No approval or scores. If no supported repair can solve the issue return changes:[]. '
        'Preserve exact text, logo, price, source product, canvas and seed. Never request label edits or invented relighting. '
        'Allowed numeric product.x/y/width/height, title/subtitle/price/logo.x/y/size/tracking/max_width/line_height, '
        'shadow.opacity/blur/offset_x/offset_y/width_scale, decoration.x/y/width, integration_plan.cast_length_ratio/cast_opacity/cast_blur. '
        'Allowed set strings title/subtitle/price/logo.color/font/align, background.prompt/color, shadow.kind, decoration.color; '
        'set boolean decoration.enabled; set background.shapes as a complete validated list. '
        'Shape x/y are UPPER LEFT, product x/y are CENTER. An ellipse centred at cx,cy uses x=cx-width/2,y=cy-height/2. '
        'Use installed approved fonts only: '+str(engine.FONT_CHOICES)+'. '+review_contract()+
        'Independent veto: '+engine.json.dumps(decision,ensure_ascii=False)+
        'Spec: '+engine.json.dumps(spec,ensure_ascii=False)+
        'Geometry and safe layout bounds: '+engine.json.dumps(engine.review_geometry(config,spec,product))+
        engine.concept_context(config))
    error=''
    for attempt in range(3):
        response=engine.vision(config,prompt+error,[poster,product,*refs],folder/f'CommercialRepair-{attempt+1}-call.json')
        engine.write(folder/f'CommercialRepairAttempt-{attempt+1}.json',response)
        try:
            if not isinstance(response,dict) or set(response)!={'changes'} or not isinstance(response['changes'],list):
                raise ValueError('Commercial repair requires only a changes array')
            engine.validate_change_shapes(response['changes'])
            engine.apply_changes(spec,response['changes'])
            engine.write(folder/'CommercialRepair.json',{'changes':response['changes'],'does_not_grant_pass':True})
            return response['changes']
        except (ValueError,KeyError,TypeError) as exc:
            engine.write(folder/f'CommercialRepairRejected-{attempt+1}.json',{'error':str(exc),'source_identity_preserved':True})
            if attempt==2:raise
            error=' Previous patch rejected without applying any changes. Fix the entire list using this actual error: '+str(exc)+' Previous proposal: '+engine.json.dumps(response,ensure_ascii=False)


def final_art_review(engine,config,spec,product,poster,refs,folder):
    """Independent relative-to-references judgment; do not show numeric scores."""
    decision=engine.vision(config,
        'Act as the final Commercial Art Director, independently of the layout critic. '
        'First image is the finished poster, second the untouched product, remaining images are campaign references. '
        'Return {tier:draft/social_ad/campaign_candidate,evidence:string,problems:[{type,problem,root_cause,affected_layer,repair_strategy}]}. '
        'No numerical scores. Do not approve because the layout is valid or the product is faithfully pasted. '
        'draft includes competent generic templates, decorative target-like circles behind a packshot, disconnected generic serif brand typography, '
        'unconvincing source lighting/edges, under-resolved source photography or an idea expressed only in its written description. '
        'social_ad means genuinely resolved brand-appropriate social advertising; campaign_candidate means comparable art direction, photographic/graphic craft '
        'and typography to the actual supplied campaign references, with a meaningful visual event. '
        'Neither tier implies brand-owner approval. For graphic campaigns do not invent floor-contact requirements. '
        'For photographic campaigns verify the readable contact plane, light agreement and perspective. '
        'Inspect actual source quality: preservation alone does not make a low-quality packshot professionally photographed. '
        'Keep factual identity and approved copy. Evaluate whether copy belongs to this visual event and identify the actually visible memory device. '
        'Generic interchangeable slogans and attractive texture without an expressed advertising event remain draft. '
        'Do not confuse a color/material variation with a campaign idea. '
        'Judge the images first; reject any claimed intent that is invisible. Spec and proposed concept: '+engine.json.dumps(spec,ensure_ascii=False)+
        engine.concept_context(config),[poster,product,*refs],folder/'CommercialArtDirector-call.json')
    if not isinstance(decision,dict) or decision.get('tier') not in ('draft','social_ad','campaign_candidate') or not isinstance(decision.get('evidence'),str) or not decision['evidence'].strip() or not isinstance(decision.get('problems'),list):
        raise ValueError('Final Commercial Art Director requires a tier, evidence and problems')
    for problem in decision['problems']:
        if not isinstance(problem,dict) or any(not isinstance(problem.get(key),str) or not problem[key].strip() for key in ('type','problem','root_cause','affected_layer','repair_strategy')):
            raise ValueError('Final Art Director problems require structured root causes and repair layers')
        if problem['affected_layer'] not in ('scene','product','shadow','typography','brand'):
            raise ValueError('Unsupported final-review repair layer')
    engine.write(folder/'CommercialArtDirector.json',decision)
    return decision
