"""Identity-protected experimental material editing; not inverse physical rendering."""
import copy
from PIL import Image,ImageDraw,ImageChops,ImageFilter
import numpy as np


def prepare(engine,spec,product,background,font,size,zones):
    if not zones:raise ValueError('Reviewed identity zones are required')
    spec=copy.deepcopy(spec)
    for name in engine.TEXT_LAYERS:spec[name]['text']=''
    spec['decoration']['enabled']=False
    with Image.open(product) as source,Image.open(background) as scene:
        before=engine.render(spec,source,font,scene).resize(size,Image.Resampling.LANCZOS).convert('RGB')
        cutout=source.convert('RGBA')
        box=cutout.getchannel('A').getbbox()
        if box is None:raise ValueError('Empty product')
        cutout=cutout.crop(box)
        p=spec['product'];cutout.thumbnail((round(p['width']),round(p['height'])),Image.Resampling.LANCZOS)
        px,py=round(p['x']-cutout.width/2),round(p['y']-cutout.height/2)
        alpha=Image.new('L',(spec['canvas']['width'],spec['canvas']['height']))
        alpha.paste(cutout.getchannel('A'),(px,py))
        protected=Image.new('L',alpha.size)
        draw=ImageDraw.Draw(protected)
        for zone in zones:
            if not isinstance(zone,dict) or not isinstance(zone.get('name'),str):raise ValueError('Named protected zone required')
            bounds=zone.get('bbox')
            if not isinstance(bounds,list) or len(bounds)!=4 or any(type(v) not in (int,float) or not 0<=v<=1 for v in bounds):raise ValueError('Protected bounds must be normalized')
            x0,y0,x1,y1=bounds
            if x0>=x1 or y0>=y1:raise ValueError('Empty protected zone')
            draw.rectangle((px+x0*cutout.width,py+y0*cutout.height,px+x1*cutout.width,py+y1*cutout.height),fill=255)
        protected=ImageChops.multiply(protected,alpha.point(lambda a:255 if a else 0))
    alpha=alpha.resize(size,Image.Resampling.LANCZOS)
    protected=protected.resize(size,Image.Resampling.NEAREST)
    # Keep the source boundary, including partially transparent pixels, fixed.
    interior=alpha.point(lambda a:255 if a>=250 else 0).filter(ImageFilter.MinFilter(5))
    editable=ImageChops.subtract(interior,protected)
    if not protected.getbbox() or not editable.getbbox():raise ValueError('Nonempty identity and editable regions required')
    return before,alpha,protected,editable


def protect(before,candidate,alpha,protected,editable):
    if candidate.size!=before.size or any(mask.size!=before.size for mask in (alpha,protected,editable)):
        raise ValueError('Relighting images and masks must have identical dimensions; no silent resizing')
    # Background gets a bounded low-frequency illumination transfer, not newly invented geometry.
    base=np.asarray(before.convert('RGB'),dtype=np.float32)
    low_base=np.asarray(before.convert('RGB').filter(ImageFilter.GaussianBlur(24)),dtype=np.float32)
    low_raw=np.asarray(candidate.convert('RGB').filter(ImageFilter.GaussianBlur(24)),dtype=np.float32)
    ratio=np.clip((low_raw+8)/(low_base+8),.75,1.25)
    shade=Image.fromarray(np.clip(base*ratio,0,255).astype(np.uint8),'RGB')
    # Entire source product remains original until editable interior is blended.
    shaded=Image.composite(before,shade,alpha.point(lambda a:255 if a else 0))
    weights=editable.filter(ImageFilter.GaussianBlur(2))
    weights=ImageChops.multiply(weights,editable)
    result=Image.composite(candidate.convert('RGB'),shaded,weights)
    result=Image.composite(before,result,protected)
    final=np.asarray(result,dtype=np.int16);original=np.asarray(before,dtype=np.int16)
    locked=np.asarray(protected)>0;body=np.asarray(editable)>0
    metrics={'protected_max_rgb_error':int(np.abs(final-original)[locked].max()) if locked.any() else None,
        'protected_pixels':int(locked.sum()),'editable_pixels':int(body.sum()),
        'editable_mean_rgb_change':float(np.abs(final-original)[body].mean()) if body.any() else 0,
        'source_silhouette_mask_unchanged':True,
        'limitations':'Original mask/boundary and protected bands are held fixed; internal material/geometry can still drift and requires visual rejection. No PBR, measured material segmentation, or glass transmission reconstruction.'}
    return result,metrics


def transfer_illumination(before,candidate,alpha):
    """Transfer smooth scalar illumination, retaining source texture and geometry.

    This is a conservative sRGB appearance approximation, not material reconstruction.
    Unlike protect(), identity pixels may change brightness; lettering is never generated.
    """
    if before.size!=candidate.size or alpha.size!=before.size:
        raise ValueError('Illumination transfer requires identical dimensions')
    base=np.asarray(before.convert('RGB'),dtype=np.float32)
    raw=np.asarray(candidate.convert('RGB'),dtype=np.float32)
    mask=np.asarray(alpha)>0
    if not mask.any():raise ValueError('Nonempty product mask required')
    def background_only(values):
        # Interpolate across the foreground before blur: glass highlights must
        # not become a luminous aura in the background illumination estimate.
        result=values.copy();xs=np.arange(values.shape[1])
        for y in range(values.shape[0]):
            keep=~mask[y]
            if not keep.any():raise ValueError('Product covers entire scanline; background light is unobservable')
            for channel in range(3):result[y,:,channel]=np.interp(xs,xs[keep],values[y,keep,channel])
        return np.asarray(Image.fromarray(result.astype(np.uint8)).filter(ImageFilter.GaussianBlur(16)),dtype=np.float32)
    bg_ratio=np.clip((background_only(raw)+8)/(background_only(base)+8),.75,1.25)
    def light(values):
        gray=Image.fromarray(values.astype(np.uint8)).convert('L').filter(ImageFilter.GaussianBlur(8))
        return np.asarray(gray,dtype=np.float32)
    product_ratio=np.clip((light(raw)+12)/(light(base)+12),.7,1.4)
    weights=np.asarray(alpha,dtype=np.float32)/255
    ratio=bg_ratio*(1-weights[:,:,None])+product_ratio[:,:,None]*weights[:,:,None]
    output=Image.fromarray(np.clip(base*ratio,0,255).astype(np.uint8))
    return output,{'mode':'source_texture_smooth_illumination_transfer',
        'generated_product_pixels_used':False,'exact_identity_rgb_lock':False,
        'product_brightness_factor_bounds':[.7,1.4],'background_factor_bounds':[.75,1.25],
        'limitations':'Brightness changes original label/cap pixels. Source lettering/geometry retained, but smooth sRGB shading does not reconstruct physical reflections or glass transmission. Visual review mandatory.'}
