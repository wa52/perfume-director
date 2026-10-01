"""Build a side-by-side review artifact from actual saved posters and critiques."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import poster


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir')
    args = parser.parse_args()
    folder = Path(args.run_dir)
    # Rendering a preview must never rewrite the original evaluation provenance.
    result = poster.read(folder/'result.json')
    rows = result['versions']
    if not 1 <= len(rows) <= 3:
        raise ValueError('Expected one to three saved versions')
    canvas = Image.new('RGB', (1560, 800), '#20211f')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
    reviewer = '模型审阅' if result.get('standalone_vision_api_used') else '对话审阅'
    for i, row in enumerate(rows):
        x = i*520
        with Image.open(folder/row['poster'].replace('\\', '/')) as source:
            thumb = ImageOps.contain(source, (486, 650))
        canvas.paste(thumb, (x+(520-thumb.width)//2, 26))
        draw.text((x+24, 700), f"V{row['version']} · {reviewer}", font=font, fill='#efe9db')
        draw.text((x+24, 744), f"评分 {row['score']} / 100 · "+('本轮通过' if row['pass'] else '未通过'), font=small, fill='#c3b68f')
    canvas.save(folder/'comparison.png')
    print(folder/'comparison.png')


if __name__ == '__main__':
    main()
