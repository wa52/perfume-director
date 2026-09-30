"""Build a side-by-side review artifact from actual saved posters and critiques."""
import argparse
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import poster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir')
    args = parser.parse_args()
    folder = Path(args.run_dir)
    rows = []
    for version in range(1, 4):
        path = folder/f'v{version}'
        if not path.exists():
            continue
        critique = poster.validate_critique(poster.read(path/'Critic.json'))
        rows.append({'version': version, 'score': critique['score'], 'pass': critique['pass'],
            'poster': f'v{version}/poster.png', 'spec': f'v{version}/PosterSpec.json', 'critic': f'v{version}/Critic.json',
            'sha256': hashlib.sha256((path/'poster.png').read_bytes()).hexdigest()})
    best = max(rows, key=lambda row: (row['pass'], row['score']))
    poster.write(folder/'result.json', {'mode': 'codex_guided_visual_review',
        'status': 'GUIDED_PASS' if best['pass'] else 'NEEDS_REVIEW', 'selected': best, 'versions': rows,
        'standalone_vision_api_used': False, 'renderer': 'real_local_comfyui',
        'background_model': 'z_image_turbo_bf16.safetensors loaded as fp8_e4m3fn',
        'text_encoder': 'Qwen3-4B-UD-Q6_K_XL.gguf', 'background_seed': 20260930,
        'score_interpretation': 'Subjective Codex assessment after inspecting each rendered image.'})
    canvas = Image.new('RGB', (1560, 800), '#20211f')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
    captions = ['V1 · 商品落在台面边缘以下', 'V2 · 修正位置与接触阴影', 'V3 · 收敛排版与阴影']
    for i, row in enumerate(rows):
        x = i*520
        with Image.open(folder/row['poster']) as source:
            thumb = ImageOps.contain(source, (486, 650))
        canvas.paste(thumb, (x+(520-thumb.width)//2, 26))
        draw.text((x+24, 700), captions[i], font=font, fill='#efe9db')
        draw.text((x+24, 744), f"看图自评 {row['score']} / 100 · "+('本轮通过' if row['pass'] else '继续调整'), font=small, fill='#c3b68f')
    canvas.save(folder/'comparison.png')
    print(folder/'comparison.png')


if __name__ == '__main__':
    main()
