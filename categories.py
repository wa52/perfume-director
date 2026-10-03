"""Explicit category policy shared by planning, critique and ComfyUI submission."""
PROFILES = {
    'perfume': {'label': '香水', 'subject': 'perfume', 'checks': 'Preserve bottle, cap, label and observed glass transmission; match packshot illumination.'},
    'skincare': {'label': '护肤美妆', 'subject': 'skincare and cosmetics', 'checks': 'Preserve packaging, pump/nozzle and label. Never invent clinical efficacy, ingredient percentages or before/after claims. Convey material and texture without adding cream or liquid to the original product.'},
    'watches': {'label': '腕表珠宝', 'subject': 'watches and jewellery', 'checks': 'Inspect dial, hands, indices, crown, bracelet links, gemstones and metal finish at enlarged scale. Never invent a model number, certification or gemstone grade. A flat-lay packshot must remain flat-lay; do not impose an upright bottle floor.'},
    'footwear': {'label': '鞋履', 'subject': 'footwear', 'checks': 'Preserve sole silhouette, stitching, laces, toe and heel. Use the actual horizontal silhouette rather than a bottle height rule. Check both heel and forefoot contact; do not invent running performance or athlete endorsements.'},
    'beverage': {'label': '饮品', 'subject': 'beverages', 'checks': 'Preserve container, closure, label and liquid appearance. Never invent flavour, ingredients or nutrition claims. Condensation and splashes may surround the product only if coherent; do not repaint its label or add unobserved droplets to the cutout.'},
}


def profile(config):
    key = config.get('product_category', 'perfume')
    if key not in PROFILES:
        raise ValueError('Unsupported product category')
    return PROFILES[key]


def context(config):
    value = profile(config)
    return ('\nCampaign category: '+value['subject']+'. Category-specific acceptance: '+value['checks']+
        ' Empty price and optional copy are intentional when not supplied. Never penalize a poster for omitting price, promotional claims, extra body copy or other information the brief does not authorize. '
        'Judge hierarchy using permitted copy and intentional negative space; the references are aesthetic benchmarks, not mandatory content checklists. '
        'Distinguish silhouette occlusion from canvas clipping: only claim clipping when the supplied bounds actually cross a canvas edge.')


def minimum_height(category, aspect):
    """Wide shoes and low jars occupy the frame by width, not bottle height."""
    if category not in PROFILES:
        raise ValueError('Unsupported product category')
    return .35 if category == 'perfume' else min(.35, .55*1080/(1440*aspect))
