"""Bounded graphic primitives rendered behind the original product."""
import math
from PIL import Image, ImageColor, ImageDraw


def validate_shapes(shapes, width, height):
    if not isinstance(shapes,list) or len(shapes)>8:
        raise ValueError('Background shapes must be a list of at most eight primitives')
    required={'kind','x','y','width','height','color','opacity'}
    for shape in shapes:
        if not isinstance(shape,dict) or set(shape)!=required:
            raise ValueError('Graphic shape requires exactly kind,x,y,width,height,color,opacity')
        if shape['kind'] not in ('ellipse','rectangle'):
            raise ValueError('Only ellipse and rectangle primitives are supported')
        for key in ('x','y','width','height','opacity'):
            n=shape[key]
            if isinstance(n,bool) or not isinstance(n,(int,float)) or not math.isfinite(n):
                raise ValueError('Graphic coordinates and opacity must be finite numbers')
        x,y,w,h=shape['x'],shape['y'],shape['width'],shape['height']
        if not 1<=w<=width*2 or not 1<=h<=height*2 or not 0<=shape['opacity']<=1:
            raise ValueError('Graphic size or opacity outside safe bounds')
        # Controlled bleed is allowed, but invisible or arbitrarily distant shapes are rejected.
        if not -width*.25<=x<=width or not -height*.25<=y<=height or x+w<=0 or y+h<=0:
            raise ValueError('Graphic primitive lies outside its bounded bleed region')
        if not isinstance(shape['color'],str):raise ValueError('Graphic color must be a string')
        ImageColor.getrgb(shape['color'])
    return shapes


def compose(background, shapes):
    """Paint in list order, once, without altering the caller's background."""
    validate_shapes(shapes,*background.size)
    canvas=background.convert('RGBA').copy()
    for shape in shapes:
        layer=Image.new('RGBA',canvas.size)
        rgba=ImageColor.getrgb(shape['color'])[:3]+(round(255*shape['opacity']),)
        box=(round(shape['x']),round(shape['y']),round(shape['x']+shape['width'])-1,
             round(shape['y']+shape['height'])-1)
        draw=ImageDraw.Draw(layer)
        if shape['kind']=='ellipse':draw.ellipse(box,fill=rgba)
        else:draw.rectangle(box,fill=rgba)
        canvas=Image.alpha_composite(canvas,layer)
    return canvas
