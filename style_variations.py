"""Four art directions for the same real perfume, executed by local ComfyUI."""
import argparse
import copy
import hashlib
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageOps
import poster

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT/'runs/styles/jadore-four-directions'
BASE = ROOT/'runs/guided/jadore-20260930/v3/PosterSpec.json'
DIRECTIONS = [('01-black-gold', '黑金奢华'), ('02-cream-minimal', '奶油极简'),
              ('03-burgundy-editorial', '酒红编辑风'), ('04-botanical', '清新植物风')]


def center_text(spec, layer):
    text = spec[layer]
    font = ImageFont.truetype(text['font'], text['size'])
    text['x'] = round((spec['canvas']['width']-font.getlength(text['text']))/2)


def prepare():
    base = poster.read(BASE)
    specs = [copy.deepcopy(base) for _ in DIRECTIONS]
    minimal = specs[1]
    minimal['background'].update(color='#EEE9DF', prompt='A photograph of a completely empty seamless ivory studio cyclorama. Only a continuous pale warm off-white paper floor gently curving into an off-white background wall. Clear uninterrupted space across the whole frame, a blank studio set waiting for a photoshoot, soft diffuse daylight from upper left, extremely quiet tonal shading, zero props, zero objects. Vertical portrait view, immaculate warm white, museum-like simplicity. The frame shows only a blank empty studio background.')
    minimal['palette'] = ['#EEE9DF', '#5B5141', '#9C8E73']
    minimal['product'].update(x=512, y=690, width=390, height=770)
    minimal['title'].update(text='J’adore', y=1132, size=76, color='#514839', font='C:/Windows/Fonts/georgiai.ttf')
    minimal['subtitle'].update(y=1232, size=18, color='#8B7F6A', font='C:/Windows/Fonts/arial.ttf')
    minimal['logo'].update(y=90, size=38, color='#514839')
    minimal['shadow'].update(opacity=.22, blur=12, offset_y=2)
    minimal['decoration']['enabled'] = False
    for layer in ('title', 'subtitle', 'logo'):
        center_text(minimal, layer)

    editorial = specs[2]
    editorial['background'].update(color='#5D1023', prompt='Empty background plate for a bold contemporary fashion fragrance magazine campaign. Vertical photograph, saturated dark wine red burgundy studio backdrop. Matte deep red tabletop covers the bottom 22 percent and blends into the backdrop with a subtle soft horizon, no visible slab edge. A restrained diagonally falling pink-red light gradient across the right side, rich velvet-like chromatic depth, high fashion studio lighting, refined editorial mood. Upper 30 percent is empty even burgundy, center right empty for a tall product added later. No objects, no fabric folds, no bottles, no perfume, no product, no people, no flowers, no text, no letters, no logo, no signage.')
    editorial['palette'] = ['#5D1023', '#F4DBD3', '#DA947E']
    editorial['product'].update(x=685, y=818, width=390, height=770)
    editorial['title'].update(text='J’ADORE', x=68, y=148, size=126, color='#F4DBD3', font='C:/Windows/Fonts/arialbd.ttf')
    editorial['subtitle'].update(x=76, y=306, size=19, color='#F4DBD3', font='C:/Windows/Fonts/arial.ttf')
    editorial['logo'].update(x=76, y=74, size=24, color='#F4DBD3', font='C:/Windows/Fonts/arial.ttf')
    editorial['decoration'].update(x=76, y=360, width=112, color='#DA947E')
    editorial['shadow'].update(opacity=.42, blur=8, offset_y=0)

    botanical = specs[3]
    botanical['background'].update(color='#E4E7D8', prompt='A completely empty botanical studio set. Pale desaturated sage green plaster wall with delicate blurred leaf shadows at far left. An unoccupied smooth pale limestone table spanning the lower twenty percent, continuous flat top surface. Only a tiny jasmine branch with white petals and green leaves in the extreme lower left corner. The entire center and right tabletop are bare and empty. Clean blank wall in the upper left. Soft diffuse daylight, tranquil spring palette, sage green and ivory, vertical architectural photograph. Empty room, no other props.')
    botanical['palette'] = ['#E4E7D8', '#334C38', '#7A8B66']
    botanical['product'].update(x=686, y=643, width=390, height=770)
    botanical['title'].update(text='J’adore', x=82, y=252, size=88, color='#334C38', font='C:/Windows/Fonts/georgiai.ttf')
    botanical['subtitle'].update(x=86, y=369, size=20, color='#657659', font='C:/Windows/Fonts/arial.ttf')
    botanical['logo'].update(x=84, y=84, size=32, color='#334C38')
    botanical['decoration'].update(x=86, y=418, width=82, color='#7A8B66')
    botanical['shadow'].update(opacity=.25, blur=10, offset_y=0)

    for (name, label), spec in zip(DIRECTIONS, specs):
        spec['design_direction'] = name
        spec['design_direction_label'] = label
        poster.validate(spec)
        poster.write(OUTPUT/name/'PosterSpec.json', spec)
    luxury_dir = OUTPUT/DIRECTIONS[0][0]
    shutil.copyfile(BASE.parent/'poster.png', luxury_dir/'poster.png')
    shutil.copyfile(ROOT/'runs/guided/jadore-20260930/v1/background.png', luxury_dir/'background.png')
    poster.write(OUTPUT/'request.json', {'mode': 'codex_guided_style_exploration', 'product': 'assets/products/dior-jadore-retailer.png',
        'directions': dict(DIRECTIONS), 'seed': base['seed'], 'purpose': 'Compare actual different backgrounds, palette, placement and type; same unchanged product photograph.',
        'existing_black_gold_reused': True, 'status': 'IN_PROGRESS'})


def render():
    config = poster.read(ROOT/'config.local.json')
    # Ensure relative model workflow paths work regardless of caller directory.
    config['background_workflow'] = str(ROOT/config['background_workflow'])
    for name, label in DIRECTIONS[1:]:
        print('Rendering:', label, flush=True)
        folder = OUTPUT/name
        poster.comfy_render(config, poster.read(folder/'PosterSpec.json'),
            ROOT/'assets/products/dior-jadore-retailer.png', folder/'poster.png', None)
        print('Saved:', folder/'poster.png', flush=True)


def comparison():
    canvas = Image.new('RGB', (1800, 720), '#22231F')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 24)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 16)
    descriptions = ['暗色石台 / 金色灯光 / 衬线字', '浅色留白 / 居中商品 / 斜体字', '酒红色块 / 粗体大字 / 编辑感', '鼠尾草绿 / 花卉叶影 / 柔光']
    result = []
    for i, (name, label) in enumerate(DIRECTIONS):
        path = OUTPUT/name/'poster.png'
        with Image.open(path) as source:
            thumb = ImageOps.contain(source.convert('RGB'), (418, 556))
        x = i*450
        canvas.paste(thumb, (x+(450-thumb.width)//2, 24))
        draw.text((x+20, 610), f'{i+1:02d}  {label}', font=font, fill='#EFEADA')
        draw.text((x+20, 656), descriptions[i], font=small, fill='#BDBAAE')
        result.append({'id': name, 'label': label, 'poster': f'{name}/poster.png',
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    canvas.save(OUTPUT/'comparison.png')
    poster.write(OUTPUT/'result.json', {'status': 'READY_FOR_STYLE_SELECTION', 'variants': result,
        'renderer': 'real_local_comfyui', 'background_model': 'z_image_turbo', 'product_regenerated': False})
    print(OUTPUT/'comparison.png', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'render', 'comparison'))
    args = parser.parse_args()
    {'prepare': prepare, 'render': render, 'comparison': comparison}[args.command]()
