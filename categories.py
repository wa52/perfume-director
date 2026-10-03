"""Explicit category policy shared by planning, critique and ComfyUI submission."""
QUALITY_PROFILE='commercial-v2-aligned-20261003'


def aligned_config(config):
    """All complete ComfyUI director workflows share one acceptance policy."""
    import copy
    result=copy.deepcopy(config)
    profile(result)
    result.update(quality_profile=QUALITY_PROFILE,commercial_v2=True,direction_mode='dynamic',
        campaign_copy_mode='creative',commercial_target='campaign_candidate',retain_rejected_creative_drafts=True)
    # User-approved wording is retained and takes precedence over creative copy.
    return result


PROFILES = {
    'perfume': {'label': '香水', 'subject': 'perfume', 'checks': 'Preserve bottle, cap, label and observed glass transmission; match packshot illumination.'},
    'skincare': {'label': '护肤美妆', 'subject': 'skincare and cosmetics', 'checks': 'Preserve packaging, pump/nozzle and label. Never invent clinical efficacy, ingredient percentages or before/after claims. Convey material and texture without adding cream or liquid to the original product.'},
    'watches': {'label': '腕表珠宝', 'subject': 'watches and jewellery', 'checks': 'Inspect dial, hands, indices, crown, bracelet links, gemstones and metal finish at enlarged scale. Never invent a model number, certification or gemstone grade. A flat-lay packshot must remain flat-lay; do not impose an upright bottle floor.'},
    'footwear': {'label': '鞋履', 'subject': 'footwear', 'checks': 'Preserve sole silhouette, stitching, laces, toe and heel. Use the actual horizontal silhouette rather than a bottle height rule. Check both heel and forefoot contact; do not invent running performance or athlete endorsements.'},
    'beverage': {'label': '饮品', 'subject': 'beverages', 'checks': 'Preserve container, closure, label and liquid appearance. Never invent flavour, ingredients or nutrition claims. Condensation and splashes may surround the product only if coherent; do not repaint its label or add unobserved droplets to the cutout.'},
    'menswear': {'label':'男装','subject':'menswear campaigns','checks':'Preserve actual cut, collar, seams, closures, sleeves, hem, fabric texture and printed graphics. Menswear is the supplied merchandising category, never infer a person\'s gender. Do not invent fabric composition, performance, size, season or sustainability claims. Never generate a wearer or digitally dress a model.'},
    'womenswear': {'label':'女装','subject':'womenswear campaigns','checks':'Preserve actual cut, neckline, seams, closures, sleeves, hem, drape, fabric texture and prints. Womenswear is the supplied merchandising category, never infer a person\'s gender. Do not invent fabric composition, performance, size, season or sustainability claims. Never generate a wearer or digitally dress a model.'},
}

CLOTHING_CATEGORIES=('menswear','womenswear')
GARMENT_TYPES={'auto':'服装','shirt':'衬衫','tshirt':'T恤','knitwear':'针织','tailoring':'西装','outerwear':'外套','trousers':'裤装','dress':'连衣裙','skirt':'半裙','activewear':'运动服'}
DISPLAY_MODES=('auto','flat_lay','hanging','ghost_mannequin','original_model')
GARMENT_CHECKS={
    'auto':'Inspect all visible construction details; do not guess hidden geometry.',
    'shirt':'Inspect collar points, button placket, cuffs and sleeve length.',
    'tshirt':'Inspect neckline ribbing, sleeve/shoulder seams and printed artwork.',
    'knitwear':'Inspect knit stitches, ribbing and yarn texture; never smooth them into synthetic fabric.',
    'tailoring':'Inspect lapel roll, pockets, buttons, shoulder structure and matching pieces.',
    'outerwear':'Inspect closures, lining edges, collar/hood and complete outer silhouette.',
    'trousers':'Inspect waistband, belt loops, fly, seams and full leg/hem proportions.',
    'dress':'Inspect neckline, bodice-to-skirt transition, pleats and complete hem/drape.',
    'skirt':'Inspect waistband, pleats, vents and hem proportions.',
    'activewear':'Inspect panel seams, stretch texture and visible reflective details; no invented athletic benefits.'}


def validate_clothing(config):
    if config.get('product_category') in CLOTHING_CATEGORIES:
        if config.get('garment_type','auto') not in GARMENT_TYPES:raise ValueError('Unsupported garment type')
        if config.get('display_mode','auto') not in DISPLAY_MODES:raise ValueError('Unsupported clothing display mode')
    elif config.get('garment_type','auto')!='auto' or config.get('display_mode','auto')!='auto':
        raise ValueError('Clothing options require a clothing category')


def spec_policy(spec,config):
    validate_clothing(config)
    if config.get('product_category') in CLOTHING_CATEGORIES:
        spec.update(garment_type=config.get('garment_type','auto'),display_mode=config.get('display_mode','auto'))
        if spec['display_mode']!='original_model':
            spec['scene_mode']='graphic'
            spec['shadow']['opacity']=0
    return spec


def profile(config):
    key = config.get('product_category', 'perfume')
    if key not in PROFILES:
        raise ValueError('Unsupported product category')
    validate_clothing(config)
    return PROFILES[key]


def context(config):
    value = profile(config)
    clothing=(' Supplied garment type: '+config.get('garment_type','auto')+'; source presentation: '+config.get('display_mode','auto')+'. '+GARMENT_CHECKS[config.get('garment_type','auto')]+' Preserve this source presentation; no rotation, simulated wearing, regenerated body or altered pose. '+
        ('For original_model preserve the entire supplied person, face, body and outfit; the renderer only composites an already cut-out original photograph.' if config.get('display_mode')=='original_model' else 'Use an editorial graphic/material field with no implied upright floor contact. No ground shadow at the hem, sleeve or hanger; shadow.opacity must remain 0. Auto means preserve the supplied cutout, not infer a new wearer.')) if config.get('product_category') in CLOTHING_CATEGORIES else ''
    return ('\nCampaign category: '+value['subject']+'. Category-specific acceptance: '+value['checks']+clothing+
        ' Empty price and optional copy are intentional when not supplied. Never penalize a poster for omitting price, promotional claims, extra body copy or other information the brief does not authorize. '
        'Judge hierarchy using permitted copy and intentional negative space; the references are aesthetic benchmarks, not mandatory content checklists. '
        'Distinguish silhouette occlusion from canvas clipping: only claim clipping when the supplied bounds actually cross a canvas edge.')


def minimum_height(category, aspect):
    """Wide shoes and low jars occupy the frame by width, not bottle height."""
    if category not in PROFILES:
        raise ValueError('Unsupported product category')
    return .35 if category == 'perfume' else min(.35, .55*1080/(1440*aspect))


def font_family(path):
    name=path.replace('\\','/').rsplit('/',1)[-1].lower()
    return 'serif' if name in ('times.ttf','georgia.ttf','bod_r.ttf','baskvill.ttf','simsun.ttc') else 'sans'


def complete_copy(result, config):
    """A factual category headline is not an invented product/model name."""
    category=config.get('product_category','perfume')
    if category!='perfume' and not result['title'].strip():
        result['observed_product_name']=''
        result['title']={'skincare':'BEAUTY','watches':'TIMEPIECES','footwear':'FOOTWEAR','beverage':'BEVERAGES','menswear':'MENSWEAR','womenswear':'WOMENSWEAR'}[category]
        result['copy_mode']='factual_category_headline'
        result['evidence']+=' No readable model name; the title is an explicit category headline, not an inferred product name.'
    return result
