"""Copy this directory and poster.py to ComfyUI/custom_nodes/perfume_director/."""
import json
from pathlib import Path
import numpy as np
import torch
from PIL import Image
from .poster import render
from . import poster as engine
from .jobs import DirectorJobs

WEB_DIRECTORY = './web'
_jobs = None


def director_jobs():
    global _jobs
    if _jobs is None:
        marker = Path(__file__).parent/'project.json'
        if not marker.is_file():
            raise ValueError('Missing project.json; install this node with the project start_comfy.ps1')
        root = Path(json.loads(marker.read_text(encoding='utf-8-sig'))['project_root']).resolve()
        if not (root/'examples/PosterSpec.json').is_file():
            raise ValueError('Perfume Director project directory is missing')
        engine.ROOT = root
        _jobs = DirectorJobs(root, engine)
    return _jobs


class PerfumeDirectorLoop:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'product': ('IMAGE',), 'product_mask': ('MASK',),
            'brief': ('STRING', {'multiline': True, 'default': '为 Dior J’adore 做暖白香槟金极简品牌海报。瓶身为大幅主视觉，实际高度占画布约55-65%，柔和无接缝摄影棚背景。标题 J’ADORE，品牌 DIOR，副标题 EAU DE PARFUM，拉丁文字采用精细衬线字体，光线匹配商品原图。无价格、新品或促销声明。避免烟雾、复杂石台和杂乱装饰。'})}}

    RETURN_TYPES = ('STRING',)
    RETURN_NAMES = ('job_id',)
    FUNCTION = 'execute'
    CATEGORY = 'Perfume Director'
    OUTPUT_NODE = True
    DESCRIPTION = 'Submit an independent vision Director/ComfyUI/Critic loop (four independent styles, max 3 rounds each). Images are sent to the configured vision API. Progress and final preview appear here; the STRING output is a job ID, not an image.'

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float('nan')

    def execute(self, product, product_mask, brief):
        if product.shape[0] != 1 or product_mask.shape[0] != 1:
            raise ValueError('The first version accepts one product, not a batch')
        rgb = Image.fromarray((product[0].cpu().numpy().clip(0, 1)*255).astype(np.uint8)).convert('RGBA')
        alpha = Image.fromarray(((1-product_mask[0].cpu().numpy()).clip(0, 1)*255).astype(np.uint8))
        if alpha.size != rgb.size:
            raise ValueError('Connect the MASK output of the same transparent LoadImage')
        rgb.putalpha(alpha)
        from server import PromptServer
        base = 'http://127.0.0.1:'+str(PromptServer.instance.port)
        job_id = director_jobs().start(rgb, brief, base)
        return {'ui': {'perfume_job': [job_id]}, 'result': (job_id,)}


class ProductDirectorLoop(PerfumeDirectorLoop):
    @classmethod
    def INPUT_TYPES(cls):
        fields=super().INPUT_TYPES()
        fields['required']['category']=(['skincare','watches','footwear','beverage','perfume','menswear','womenswear'],)
        fields['required']['brief']=('STRING', {'multiline':True,'default':'为这款商品探索四个明显不同的商业海报方向。保留商品原图、真实品牌和名称，不添加价格或未经提供的功效声明。'})
        return fields

    CATEGORY='Product Art Director'
    DESCRIPTION='Choose a product category and run four fresh Director/Renderer/Critic concepts, with visible drafts and guarded review.'

    def execute(self, product, product_mask, brief, category, garment_type='auto', display_mode='auto'):
        if product.shape[0]!=1 or product_mask.shape[0]!=1:raise ValueError('One product per task')
        rgb=Image.fromarray((product[0].cpu().numpy().clip(0,1)*255).astype(np.uint8)).convert('RGBA')
        alpha=Image.fromarray(((1-product_mask[0].cpu().numpy()).clip(0,1)*255).astype(np.uint8))
        if alpha.size!=rgb.size:raise ValueError('Connect IMAGE and MASK of the same transparent PNG')
        rgb.putalpha(alpha)
        from server import PromptServer
        job_id=director_jobs().start(rgb,brief,'http://127.0.0.1:'+str(PromptServer.instance.port),category=category,garment_type=garment_type,display_mode=display_mode)
        return {'ui':{'perfume_job':[job_id]},'result':(job_id,)}


class ClothingDirectorLoop(ProductDirectorLoop):
    @classmethod
    def INPUT_TYPES(cls):
        from .categories import GARMENT_TYPES,DISPLAY_MODES
        fields=super().INPUT_TYPES()
        fields['required']['category']=(['menswear','womenswear'],)
        fields['required']['garment_type']=(list(GARMENT_TYPES),)
        fields['required']['display_mode']=(list(DISPLAY_MODES),)
        fields['required']['brief']=('STRING',{'multiline':True,'default':'为这款服装探索四个明显不同的品牌海报方向。保留原图版型、面料纹理、颜色和全部细节，保持原展示方式；只使用可确认的品牌与名称，不虚构材质成分、价格或功能，不生成模特或改变穿着。'})
        return fields

    DESCRIPTION='Menswear/womenswear and garment subtypes; preserve source presentation, fabric and silhouette, with four fresh reviewed directions.'


class PerfumePosterSpecRender:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'product': ('IMAGE',), 'product_mask': ('MASK',), 'background': ('IMAGE',),
            'spec_json': ('STRING', {'multiline': True}), 'font_path': ('STRING', {'default': 'C:/Windows/Fonts/msyh.ttc'})}}

    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'execute'
    CATEGORY = 'Perfume Director'

    def execute(self, product, product_mask, background, spec_json, font_path):
        rgb = Image.fromarray((product[0].cpu().numpy().clip(0, 1)*255).astype(np.uint8)).convert('RGBA')
        # Comfy LoadImage MASK is inverted alpha: 0 opaque, 1 transparent.
        alpha = Image.fromarray(((1-product_mask[0].cpu().numpy()).clip(0, 1)*255).astype(np.uint8))
        if alpha.size != rgb.size:
            raise ValueError('Product mask must match image; provide transparent PNG')
        rgb.putalpha(alpha)
        bg = Image.fromarray((background[0].cpu().numpy().clip(0, 1)*255).astype(np.uint8))
        result = render(json.loads(spec_json), rgb, font_path, bg)
        return (torch.from_numpy(np.array(result).astype(np.float32)/255)[None, ...],)


NODE_CLASS_MAPPINGS = {'ClothingDirectorLoop':ClothingDirectorLoop,'ProductDirectorLoop':ProductDirectorLoop, 'PerfumePosterSpecRender': PerfumePosterSpecRender, 'PerfumeDirectorLoop': PerfumeDirectorLoop}
NODE_DISPLAY_NAME_MAPPINGS = {'ClothingDirectorLoop':'AI Art Director · 男装女装细分闭环','ProductDirectorLoop':'AI Art Director · 多类别四方向闭环', 'PerfumePosterSpecRender': 'Perfume PosterSpec Render', 'PerfumeDirectorLoop': 'AI Art Director Loop · 四风格香水闭环'}


def require_finite(value, stage):
    if isinstance(value, torch.Tensor):
        if not torch.isfinite(value).all().item():
            raise ValueError(f'{stage}: non-finite tensor; check precision/model configuration')
    elif isinstance(value, dict):
        for child in value.values():
            require_finite(child, stage)
    elif isinstance(value, (tuple, list)):
        for child in value:
            require_finite(child, stage)


class PerfumeFiniteConditioning:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'conditioning': ('CONDITIONING',)}}
    RETURN_TYPES = ('CONDITIONING',)
    FUNCTION = 'execute'
    CATEGORY = 'Perfume Director/Validation'
    def execute(self, conditioning):
        require_finite(conditioning, 'text_encoder')
        return (conditioning,)


class PerfumeFiniteLatent:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'samples': ('LATENT',)}}
    RETURN_TYPES = ('LATENT',)
    FUNCTION = 'execute'
    CATEGORY = 'Perfume Director/Validation'
    def execute(self, samples):
        require_finite(samples, 'sampler')
        return (samples,)


class PerfumeFiniteImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'images': ('IMAGE',)}}
    RETURN_TYPES = ('IMAGE',)
    FUNCTION = 'execute'
    CATEGORY = 'Perfume Director/Validation'
    def execute(self, images):
        require_finite(images, 'vae_decode')
        return (images,)


NODE_CLASS_MAPPINGS.update({
    'PerfumeFiniteConditioning': PerfumeFiniteConditioning,
    'PerfumeFiniteLatent': PerfumeFiniteLatent,
    'PerfumeFiniteImage': PerfumeFiniteImage,
})


from aiohttp import web
from server import PromptServer


@PromptServer.instance.routes.get('/perfume-director/jobs/{job_id}')
async def director_status(request):
    try:
        return web.json_response(director_jobs().status(request.match_info['job_id']))
    except (ValueError, FileNotFoundError):
        raise web.HTTPNotFound()


@PromptServer.instance.routes.get('/perfume-director/jobs/{job_id}/preview')
async def director_preview(request):
    try:
        return web.FileResponse(director_jobs().preview(request.match_info['job_id'], request.query.get('direction'),draft=request.query.get('draft')=='1'))
    except (ValueError, FileNotFoundError):
        raise web.HTTPNotFound()
