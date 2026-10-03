"""Conservative 2D harmonization from source RGBA and a clean scene.

Generated RGB is never copied into the product. This is not inverse rendering.
"""
import copy
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def linear(rgb):
    rgb=np.asarray(rgb,dtype=np.float64)/255
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)


def encoded(rgb):
    rgb=np.clip(rgb,0,1)
    value=np.where(rgb<=.0031308,rgb*12.92,1.055*rgb**(1/2.4)-.055)
    return np.clip(np.rint(value*255),0,255).astype(np.uint8)


def linear_composite(background,product):
    if background.size!=product.size:raise ValueError('Composite dimensions must match')
    values=np.asarray(product.convert('RGBA'))
    alpha=values[:,:,3:4]/255
    return Image.fromarray(encoded(linear(values[:,:,:3])*alpha+linear(background.convert('RGB'))*(1-alpha)))


def clean_matte(product):
    """Replace only partially transparent edge RGB with nearby opaque RGB.

    Never erode the alpha contour or rewrite opaque labels.
    Does not assume the whole bottle is transparent glass based on pixel color.
    """
    values=np.asarray(product.convert('RGBA')).copy()
    rgb=values[:,:,:3].astype(np.float64);alpha=values[:,:,3]
    valid=alpha>=250;original=rgb.copy()
    # Propagate nearby foreground color at most six pixels, with no wraparound.
    for _ in range(6):
        padded=np.pad(rgb,((1,1),(1,1),(0,0)),mode='edge')
        known=np.pad(valid,1,constant_values=False)
        total=np.zeros_like(rgb);count=np.zeros(valid.shape)
        for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
            flag=known[1+dy:1+dy+rgb.shape[0],1+dx:1+dx+rgb.shape[1]]
            total+=padded[1+dy:1+dy+rgb.shape[0],1+dx:1+dx+rgb.shape[1]]*flag[:,:,None]
            count+=flag
        fill=(~valid)&(count>0)
        rgb[fill]=total[fill]/count[fill,None];valid|=fill
    edge=(alpha>0)&(alpha<250)&valid
    original[edge]=rgb[edge]
    values[:,:,:3]=np.clip(np.rint(original),0,255).astype(np.uint8)
    return Image.fromarray(values)


def guide_field(before,guide,alpha,protected,strength):
    """Robust smooth scalar field over source geometry, excluding identity bands."""
    if type(strength) not in (int,float) or not math.isfinite(strength) or not 0<=strength<=1:
        raise ValueError('Guide strength must be finite and within 0..1')
    if any(image.size!=before.size for image in (guide,alpha,protected)):
        raise ValueError('Guide and masks must have identical dimensions')
    h,w=before.height,before.width
    if strength==0:return np.ones((h,w),dtype=np.float64)
    mask=np.asarray(alpha)>=250
    safe=np.asarray(alpha.filter(ImageFilter.MinFilter(9)))>=250
    safe&=np.asarray(protected.filter(ImageFilter.MaxFilter(9)))==0
    if safe.sum()<30:raise ValueError('Insufficient visible material pixels for guide fit')
    source=np.asarray(before.convert('RGB'))
    reference=np.asarray(guide.convert('RGB')).copy()
    # Remove invented label glyphs before any smoothing, not merely after fitting.
    locked=np.asarray(protected.filter(ImageFilter.MaxFilter(9)))>0
    reference[locked]=source[locked]
    def luminance(array):return linear(array)@np.array([.2126,.7152,.0722])
    base=luminance(source);edited=luminance(reference)
    # A quadratic field cannot reproduce AI lettering, rims or local ghost shadows.
    y,x=np.indices((h,w));bounds=alpha.getbbox()
    if bounds is None:raise ValueError('Empty source product')
    x=(x-(bounds[0]+bounds[2])/2)/max(1,bounds[2]-bounds[0])*2
    y=(y-(bounds[1]+bounds[3])/2)/max(1,bounds[3]-bounds[1])*2
    design=np.stack([np.ones_like(x),x,y,x*x,x*y,y*y],axis=-1)
    indices=np.flatnonzero(safe)[::max(1,int(safe.sum()/12000))]
    matrix=design.reshape(-1,6)[indices]
    targets=np.log(np.clip((edited.ravel()[indices]+.015)/(base.ravel()[indices]+.015),.6,1.6))
    keep=np.ones(len(targets),dtype=bool)
    for _ in range(4):
        if keep.sum()<12:raise ValueError('Unstable guide illumination fit')
        coeff=np.linalg.lstsq(matrix[keep],targets[keep],rcond=None)[0]
        residual=targets-matrix@coeff
        median=np.median(residual);mad=np.median(np.abs(residual-median))
        keep=np.abs(residual-median)<=max(.03,3*1.4826*mad)
    field=np.clip(np.exp(design@coeff*strength),.85,1.15)
    return field


def compose(engine,spec,product,background,font,zones,guide_before=None,guide=None,
            strength=.35,ground_top=.72,contact_opacity=.5,cast_ratio=.055,edge_cleanup=True,
            contour_contact=True,spill_zones=None,refine_alpha=False,wrap_zones=None,reflection_strength=0):
    """Recompose source texture at output resolution, then draw deterministic type."""
    engine.validate(spec)
    for name,value,lo,hi in [('ground_top',ground_top,0,1),('contact_opacity',contact_opacity,0,.7),('cast_ratio',cast_ratio,0,.15)]:
        if type(value) not in (int,float) or not math.isfinite(value) or not lo<=value<=hi:raise ValueError('Invalid '+name)
    if any(type(v) is not bool for v in (edge_cleanup,contour_contact,refine_alpha)):raise ValueError('Boolean compositor options required')
    if type(reflection_strength) not in (int,float) or not math.isfinite(reflection_strength) or not 0<=reflection_strength<=.25:raise ValueError('Reflection strength must be 0..0.25')
    if reflection_strength and guide is None:raise ValueError('Reflections require an actual guide and reviewed material protection')
    if guide is not None and not zones:raise ValueError('Reviewed identity zones required for guided light')
    if spec.get('scene_mode','photographic')!='photographic':raise ValueError('2D harmonization requires a photographic ground plane')
    if any(spec['layers'].index(layer)<spec['layers'].index('product') for layer in (*engine.TEXT_LAYERS,'decoration')):raise ValueError('This compositor requires text/decorations above product')
    canvas_size=(spec['canvas']['width'],spec['canvas']['height'])
    source=product.convert('RGBA');bounds=source.getchannel('A').getbbox()
    if not bounds:raise ValueError('Empty source product')
    source=source.crop(bounds)
    source.thumbnail((round(spec['product']['width']),round(spec['product']['height'])),Image.Resampling.LANCZOS)
    px=round(spec['product']['x']-source.width/2);py=round(spec['product']['y']-source.height/2)
    if px<0 or py<0 or px+source.width>canvas_size[0] or py+source.height>canvas_size[1]:raise ValueError('Source product outside canvas')
    foots=engine.contact_footprints(source);base=max(py+foot[1] for foot in foots)
    ground=round(canvas_size[1]*ground_top)
    if ground>=base:raise ValueError('Product contact is above the declared ground plane')
    original_alpha=source.getchannel('A').tobytes()
    corrected=clean_matte(source) if edge_cleanup else source.copy()
    if spill_zones:corrected=clean_spill(corrected,spill_zones)
    if refine_alpha:corrected=refine_edge_alpha(corrected)
    field=np.ones((canvas_size[1],canvas_size[0]))
    if (guide_before is None)!=(guide is None):raise ValueError('Both guide images required')
    if guide is not None:
        expected_spec=copy.deepcopy(spec)
        for layer in engine.TEXT_LAYERS:expected_spec[layer]['text']=''
        expected_spec['decoration']['enabled']=False
        expected=engine.render(expected_spec,product,font,background).resize(guide_before.size,Image.Resampling.LANCZOS).convert('RGB')
        if guide_before.size!=guide.size or np.abs(np.asarray(expected,dtype=np.int16)-np.asarray(guide_before.convert('RGB'),dtype=np.int16)).max()>2:
            raise ValueError('Guide baseline must match this source, clean background and PosterSpec; use the lossless original composite')
        alpha_full=Image.new('L',canvas_size);alpha_full.paste(source.getchannel('A'),(px,py))
        lock=Image.new('L',canvas_size);draw=ImageDraw.Draw(lock)
        for zone in zones:
            bbox=zone.get('bbox') if isinstance(zone,dict) else None
            if not isinstance(bbox,list) or len(bbox)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in bbox):raise ValueError('Invalid identity zone')
            x0,y0,x1,y1=bbox
            if x0>=x1 or y0>=y1:raise ValueError('Empty identity zone')
            draw.rectangle((px+x0*source.width,py+y0*source.height,px+x1*source.width,py+y1*source.height),fill=255)
        field_low=guide_field(guide_before,guide,alpha_full.resize(guide.size,Image.Resampling.LANCZOS),lock.resize(guide.size,Image.Resampling.NEAREST),strength)
        field=np.asarray(Image.fromarray(field_low.astype(np.float32)).resize(canvas_size,Image.Resampling.BILINEAR))
    values=np.asarray(corrected).copy()
    surface=linear(values[:,:,:3])*field[py:py+source.height,px:px+source.width,None]
    gloss_max=0
    if reflection_strength:
        gloss=reflection_field(guide_before,guide,alpha_full.resize(guide.size,Image.Resampling.LANCZOS),lock.resize(guide.size,Image.Resampling.NEAREST),reflection_strength)
        gloss=np.asarray(Image.fromarray(gloss.astype(np.float32)).resize(canvas_size,Image.Resampling.BILINEAR))[py:py+source.height,px:px+source.width]
        gloss_max=float(gloss.max())
        # Neutral additive reflection approximation: never copy edited RGB/labels.
        surface+=gloss[:,:,None]
    values[:,:,:3]=encoded(surface)
    corrected=Image.fromarray(values)
    scene=background.convert('RGB').resize(canvas_size,Image.Resampling.LANCZOS)
    if spec['background'].get('shapes'):
        scene=engine.graphic_module().compose(scene,spec['background']['shapes'],product.convert('RGBA')).convert('RGB')
    if wrap_zones:corrected=ambient_wrap(corrected,scene,px,py,wrap_zones)
    # Preserve the clean background: guide-generated wall shadows never enter this scene.
    cast=Image.new('RGBA',canvas_size,(0,0,0,0))
    plan=copy.deepcopy(spec.get('integration_plan',{'source_key_light':'unknown','ground_material':'declared plane','cast_length_ratio':0,'cast_opacity':0,'cast_blur':18}))
    if spec.get('scene_mode','photographic')=='photographic' and plan['source_key_light']!='unknown':
        plan.update(cast_length_ratio=min(cast_ratio,(base-ground-4)/canvas_size[1]),cast_opacity=.16,cast_blur=18)
        if plan['cast_length_ratio']>0:cast=engine.commercial_module().cast_shadow(cast,corrected,px,py,plan)
    near=Image.new('L',canvas_size);core=Image.new('L',canvas_size)
    for cx,fy,fw in foots:
        cx+=px;fy+=py
        radius=max(2,fw*.48)
        ImageDraw.Draw(near).ellipse((cx-radius,fy-4,cx+radius,fy+5),fill=round(255*contact_opacity))
        if not contour_contact:
            ImageDraw.Draw(core).ellipse((cx-radius*.88,fy-2,cx+radius*.88,fy+2),fill=round(255*min(.65,contact_opacity*1.25)))
    if contour_contact:
        core=contour_shadow(source,canvas_size,px,py,min(.65,contact_opacity*1.25))
    cast_mask=np.asarray(cast.getchannel('A'))/255
    near_mask=np.asarray(near.filter(ImageFilter.GaussianBlur(6)))/255
    core_mask=np.asarray(core.filter(ImageFilter.GaussianBlur(1.2)))/255
    attenuation=(1-cast_mask)*(1-near_mask)*(1-core_mask)
    attenuation[:ground]=1
    scene=Image.fromarray(encoded(linear(scene)*attenuation[:,:,None]))
    full=Image.new('RGBA',canvas_size);full.alpha_composite(corrected,(px,py))
    scene=linear_composite(scene,full)
    final=scene.convert('RGBA')
    for layer in spec['layers']:
        if layer in engine.TEXT_LAYERS:
            text=spec[layer]
            if not engine.quality_module().font_supports_text(str(text.get('font',font)),text['text']):raise ValueError('Unsupported typography glyphs')
            bbox=engine.typography_module().text_layout(text,font)['bbox']
            if bbox[2]>canvas_size[0] or bbox[3]>canvas_size[1]:raise ValueError('Typography outside canvas')
            engine.typography_module().draw_text(final,text,font)
        elif layer=='decoration' and spec[layer]['enabled']:
            d=spec[layer];ImageDraw.Draw(final).line((d['x'],d['y'],d['x']+d['width'],d['y']),fill=d['color'],width=2)
    source_a=np.asarray(source.getchannel('A'),dtype=np.int16);corrected_a=np.asarray(corrected.getchannel('A'),dtype=np.int16)
    return scene,final.convert('RGB'),{'source_alpha_unchanged':original_alpha==corrected.getchannel('A').tobytes(),
        'alpha_changed_pixels':int((source_a!=corrected_a).sum()),
        'alpha_mean_absolute_change':float(np.abs(source_a-corrected_a).mean()),
        'generated_product_rgb_copied':False,'generated_background_rgb_copied':False,
        'illumination_gain_range':[float(field[py:py+source.height,px:px+source.width][np.asarray(source.getchannel('A'))>0].min()),float(field[py:py+source.height,px:px+source.width][np.asarray(source.getchannel('A'))>0].max())],
        'identity_policy':'original lettering texture; brightness can change; no generated label or exact RGB guarantee',
        'ground_top_y':ground,'product_base_y':base,'key_light':plan['source_key_light'],
        'shadow_plan':plan,'edge_cleanup':edge_cleanup,'contour_contact':contour_contact,'refine_alpha':refine_alpha,'manual_spill_zones':spill_zones or [],'manual_wrap_zones':wrap_zones or [],'reflection_strength':reflection_strength,'maximum_additive_reflection_linear':gloss_max,'output_size':list(canvas_size),
        'limitations':'2D source-compatible appearance and projected shadows; not new physical reflections, refraction, intrinsic decomposition or source-detail restoration.'}


def contour_shadow(product,canvas_size,px,py,opacity):
    """Contact core immediately beneath each visible bottom-support column.

    Only the lowest 3% of the silhouette contributes; taller raised portions do
    not manufacture contact beneath an unsupported shoe sole or bottle shoulder.
    """
    alpha=np.asarray(product.getchannel('A'))
    solid=alpha>=160
    points=[]
    for x in range(product.width):
        rows=np.flatnonzero(solid[:,x])
        if len(rows):points.append((x,int(rows[-1])))
    mask=Image.new('L',canvas_size)
    if not points:return mask
    lowest=max(y for _,y in points);tolerance=max(2,round(product.height*.03))
    draw=ImageDraw.Draw(mask)
    for x,y in points:
        if y>=lowest-tolerance:
            draw.line((px+x,py+y-1,px+x,py+y+3),fill=round(255*opacity),width=1)
    return mask


def clean_spill(product,zones):
    """Desaturate warm source-background remnants only in reviewed edge regions.

    RGB changes are deliberately explicit. No alpha choke, invented texture,
    global brand recolor, or automatic material classification is performed.
    """
    values=np.asarray(product.convert('RGBA')).copy()
    rgb=values[:,:,:3].astype(np.float64)
    alpha=product.getchannel('A')
    ring=np.asarray(alpha)>np.asarray(alpha.filter(ImageFilter.MinFilter(7)))
    warm=(rgb[:,:,0]>rgb[:,:,2]*1.3)&(rgb[:,:,1]>rgb[:,:,2]*1.15)&(rgb[:,:,1]>rgb[:,:,0]*.3)
    weight=np.zeros((product.height,product.width))
    for zone in zones:
        bbox=zone.get('bbox') if isinstance(zone,dict) else None
        amount=zone.get('strength') if isinstance(zone,dict) else None
        if not isinstance(bbox,list) or len(bbox)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in bbox):raise ValueError('Invalid spill region')
        if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<=amount<=1:raise ValueError('Invalid spill amount')
        x0,y0,x1,y1=bbox
        if x0>=x1 or y0>=y1:raise ValueError('Empty spill region')
        mask=Image.new('L',product.size);ImageDraw.Draw(mask).rectangle((x0*product.width,y0*product.height,x1*product.width,y1*product.height),fill=255)
        weight=np.maximum(weight,np.asarray(mask.filter(ImageFilter.GaussianBlur(.6)))/255*amount)
    weight*=ring&warm
    source=linear(rgb);grey=(source@np.array([.2126,.7152,.0722]))[:,:,None]
    values[:,:,:3]=encoded(source*(1-weight[:,:,None])+grey*weight[:,:,None])
    return Image.fromarray(values)


def refine_edge_alpha(product):
    """Opt-in 0.55px boundary refinement; source core and RGB remain unchanged.

    Alpha may shrink at the boundary but never expands beyond original support.
    This is a declared matte repair, not exact silhouette identity.
    """
    values=np.asarray(product.convert('RGBA')).copy()
    original=product.getchannel('A')
    core=np.asarray(original.filter(ImageFilter.MinFilter(3)))>=250
    smooth=np.asarray(original.filter(ImageFilter.GaussianBlur(.55)))
    values[:,:,3]=np.minimum(values[:,:,3],smooth)
    values[:,:,3][core]=np.asarray(original)[core]
    return Image.fromarray(values)


def ambient_wrap(product,scene,px,py,zones):
    """Bounded environment color wrap in reviewed one-pixel contour regions."""
    values=np.asarray(product.convert('RGBA')).copy()
    alpha=product.getchannel('A')
    ring=np.clip((np.asarray(alpha,dtype=float)-np.asarray(alpha.filter(ImageFilter.MinFilter(3)),dtype=float))/255,0,1)
    weights=np.zeros((product.height,product.width))
    for zone in zones:
        bbox=zone.get('bbox') if isinstance(zone,dict) else None
        amount=zone.get('strength') if isinstance(zone,dict) else None
        if not isinstance(bbox,list) or len(bbox)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in bbox):raise ValueError('Invalid wrap region')
        if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<=amount<=.3:raise ValueError('Wrap strength must be 0..0.3')
        x0,y0,x1,y1=bbox
        if x0>=x1 or y0>=y1:raise ValueError('Empty wrap region')
        mask=Image.new('L',product.size);ImageDraw.Draw(mask).rectangle((x0*product.width,y0*product.height,x1*product.width,y1*product.height),fill=255)
        weights=np.maximum(weights,np.asarray(mask)/255*amount)
    weights*=ring
    ambient=np.asarray(scene.filter(ImageFilter.GaussianBlur(6)).crop((px,py,px+product.width,py+product.height)))
    values[:,:,:3]=encoded(linear(values[:,:,:3])*(1-weights[:,:,None])+linear(ambient)*weights[:,:,None])
    return Image.fromarray(values)


def reflection_field(before,guide,alpha,protected,strength):
    """Positive neutral highlight guidance confined to unlocked material interior.

    Reflections remain an appearance approximation and can still be implausible.
    No spatial warp, source-texture blur or edited product RGB is introduced.
    """
    if any(im.size!=before.size for im in (guide,alpha,protected)):raise ValueError('Reflection guide dimensions must match')
    if type(strength) not in (int,float) or not math.isfinite(strength) or not 0<=strength<=.25:raise ValueError('Invalid reflection strength')
    source=linear(before.convert('RGB'))@np.array([.2126,.7152,.0722])
    target=linear(guide.convert('RGB'))@np.array([.2126,.7152,.0722])
    safe=np.asarray(alpha.filter(ImageFilter.MinFilter(9)))>=250
    safe&=np.asarray(protected.filter(ImageFilter.MaxFilter(13)))==0
    # Antialias a conservative highlight weight without leaking into locked zones.
    weights=np.asarray(Image.fromarray((safe*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)))/255*safe
    return np.minimum(np.maximum(target-source,0),.5)*weights*strength
