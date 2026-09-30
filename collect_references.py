"""Download explicitly curated reference URLs; preserve original files and provenance."""
import concurrent.futures
import hashlib
import io
import json
from pathlib import Path
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent


def download(item):
    folder = ROOT/'references/candidates'
    folder.mkdir(exist_ok=True)
    try:
        request = urllib.request.Request(item['image_url'], headers={'User-Agent': 'Mozilla/5.0', 'Referer': item['source_url']})
        with urllib.request.urlopen(request, timeout=25) as response:
            content = response.read(20_000_001)
        if len(content) > 20_000_000:
            raise ValueError('Image exceeds 20 MB')
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            width, height, fmt = image.width, image.height, image.format
        if min(width, height) < 400:
            raise ValueError(f'Too small: {width}x{height}')
        suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}.get(fmt)
        if not suffix:
            raise ValueError(f'Unsupported image format: {fmt}')
        path = folder/(item['id']+suffix)
        path.write_bytes(content)
        return {**item, 'path': str(path.relative_to(ROOT)).replace('\\', '/'), 'width': width, 'height': height,
                'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'status': 'downloaded'}
    except Exception as error:
        return {**item, 'status': 'failed', 'error': str(error)}


def sheets(items):
    successful = [item for item in items if item['status'] == 'downloaded']
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    for start in range(0, len(successful), 8):
        page = Image.new('RGB', (1440, 1040), '#eeeeee')
        draw = ImageDraw.Draw(page)
        for i, item in enumerate(successful[start:start+8]):
            x, y = i % 4 * 360, i // 4 * 520
            with Image.open(ROOT/item['path']) as source:
                thumb = ImageOps.contain(source.convert('RGB'), (340, 455))
            page.paste(thumb, (x+(360-thumb.width)//2, y+(465-thumb.height)//2))
            draw.text((x+8, y+468), item['id'], fill='black', font=font)
            draw.text((x+8, y+493), f"{item['width']} x {item['height']}", fill='black', font=font)
        page.save(ROOT/f'references/contact-sheet-{start//8+1}.jpg', quality=92)


if __name__ == '__main__':
    candidates = json.loads((ROOT/'references/candidates.json').read_text(encoding='utf-8'))
    previous_path = ROOT/'references/downloads.json'
    previous = {row['id']: row for row in json.loads(previous_path.read_text(encoding='utf-8'))} if previous_path.exists() else {}
    pending = [row for row in candidates if row['id'] not in previous]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        new_results = {row['id']: row for row in pool.map(download, pending)}
    results = [previous[row['id']] if row['id'] in previous else new_results[row['id']] for row in candidates]
    (ROOT/'references/downloads.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    sheets(results)
    for item in results:
        print(item['id'], item['status'], item.get('error', f"{item['width']}x{item['height']}" if item['status'] == 'downloaded' else ''))
