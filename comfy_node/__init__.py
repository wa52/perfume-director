"""Copy this directory and poster.py to ComfyUI/custom_nodes/perfume_director/."""
import json
import numpy as np
import torch
from PIL import Image
from .poster import render


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


NODE_CLASS_MAPPINGS = {'PerfumePosterSpecRender': PerfumePosterSpecRender}
NODE_DISPLAY_NAME_MAPPINGS = {'PerfumePosterSpecRender': 'Perfume PosterSpec Render'}


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
