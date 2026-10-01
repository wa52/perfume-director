"""Deterministic composition checks; these are not an aesthetic model or a PASS."""
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageStat


def layout_issues(spec, geometry):
    w, h = spec['canvas']['width'], spec['canvas']['height']
    box = geometry['product_bbox']
    issues = []
    if box[3] > h*.91 or box[1] < h*.16 or box[0] < w*.05 or box[2] > w*.95:
        issues.append('product_outside_safe_area')
    if not .48 <= (box[3]-box[1])/h <= .68:
        issues.append('product_scale_outside_hero_range')
    if spec['shadow'].get('kind') == 'contact' and (abs(spec['shadow']['offset_y']) > 16 or abs(spec['shadow']['offset_x']) > 32):
        issues.append('contact_shadow_detached')
    for name, bounds in geometry['text_bbox'].items():
        if bounds[0] < w*.04 or bounds[1] < h*.035 or bounds[2] > w*.96 or bounds[3] > h*.97:
            issues.append(name+'_outside_safe_area')
        if geometry['text_product_overlap'].get(name):
            issues.append(name+'_overlaps_product')
    return issues


def background_issues(path, direction):
    with Image.open(path) as source:
        image = source.convert('RGB').resize((64, 96))
    stats = ImageStat.Stat(image)
    r, g, b = stats.mean
    edges = [image.crop(box) for box in ((0,0,64,1), (0,95,64,96), (0,0,1,96), (63,0,64,96))]
    white_edges = sum(min(ImageStat.Stat(edge).mean) > 243 and max(ImageStat.Stat(edge).stddev) < 12 for edge in edges)
    issues = []
    if direction != 'cream-minimal' and white_edges >= 3 and min(stats.mean) < 220:
        issues.append('unexpected_white_frame')
    if direction == 'black-gold' and image.convert('L').getextrema()[0] > 110:
        issues.append('black_direction_too_bright')
    if direction == 'burgundy-editorial' and not (r > g*1.2 and r > b*1.1):
        issues.append('burgundy_direction_color_mismatch')
    return issues


def luminance(rgb):
    values = [v/255 for v in rgb[:3]]
    linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in values]
    return sum(v*k for v,k in zip(linear, (.2126,.7152,.0722)))


def contrast_adjustments(spec, geometry, background):
    """Choose legible ink; never change words, size or position here."""
    with Image.open(background) as source:
        image = source.convert('RGB').resize((spec['canvas']['width'], spec['canvas']['height']))
    changes = []
    for name, box in geometry['text_bbox'].items():
        area = image.crop(tuple(map(int, box)))
        if area.width < 1 or area.height < 1:
            continue
        light = luminance(ImageStat.Stat(area).mean)
        ink = luminance(ImageColor.getrgb(spec[name]['color']))
        contrast = (max(light, ink)+.05)/(min(light, ink)+.05)
        if contrast < 3:
            candidates = [spec[name]['color'], '#261E16', '#F9F4E9']
            color = max(candidates, key=lambda c: (max(light,luminance(ImageColor.getrgb(c)))+.05)/(min(light,luminance(ImageColor.getrgb(c)))+.05))
            changes.append({'path':name+'.color','old':spec[name]['color'],'value':color,'reason':'text_background_contrast_below_3'})
    return changes


def fallback_background(spec, direction):
    """Explicit renderer fallback after failed AI attempts, recorded in the run."""
    w, h = spec['canvas']['width'], spec['canvas']['height']
    palettes = {'black-gold':('#141519','#37383B'), 'cream-minimal':('#DCCCAE','#FAF2E4'),
                'burgundy-editorial':('#58192C','#A45F6B'), 'botanical':('#BECDB5','#E4EBDB')}
    left, right = [ImageColor.getrgb(c) for c in palettes[direction]]
    small = Image.new('RGB', (128, 192)); pixels = small.load()
    for y in range(192):
        for x in range(128):
            t = .65*x/127+.35*y/191
            pixels[x,y] = tuple(round(a+(b-a)*t) for a,b in zip(left,right))
    image = small.resize((w,h),Image.Resampling.BICUBIC)
    if direction == 'burgundy-editorial':
        ImageDraw.Draw(image).polygon([(w*.3,0),(w*.5,0),(w,h*.65),(w,h*.83)],fill='#4A1525')
    if direction == 'botanical':
        leaves = Image.new('RGBA',(w,h))
        draw = ImageDraw.Draw(leaves)
        for x,y in [(w*.94,h*.08),(w*.99,h*.20),(w*.04,h*.48)]:
            draw.ellipse((x-45,y-80,x+45,y+80),fill=(58,91,49,50))
        image = Image.alpha_composite(image.convert('RGBA'),leaves.filter(ImageFilter.GaussianBlur(24))).convert('RGB')
    return image
