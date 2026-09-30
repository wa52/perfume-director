"""Fetch an existing perfume packshot and verify real alpha, without regenerating it."""
import hashlib
import io
import json
from pathlib import Path
import urllib.request
from PIL import Image

ROOT = Path(__file__).resolve().parent
CANDIDATES = [
    {'id': 'dior-jadore-retailer', 'source_url': 'https://mondo-parfum.de/Dior-J-adore-Eau-de-Parfum-100-ml/SW10238.2',
     'image_url': 'https://mondo-parfum.de/media/9d/05/00/1759494959/Dior%20Jadore%20Eau%20de%20Parfum.png?ts=1759494959'},
    {'id': 'dior-jadore-cutout', 'source_url': 'https://www.pikpng.com/transpng/hxRbxwb/',
     'image_url': 'https://www.pikpng.com/pngl/b/564-5643337_perfume-png-transparent-images-j-adore-dior-png.png'}
]


def main():
    output = ROOT/'assets/products'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for item in CANDIDATES:
        try:
            req = urllib.request.Request(item['image_url'], headers={'User-Agent': 'Mozilla/5.0', 'Referer': item['source_url']})
            with urllib.request.urlopen(req, timeout=25) as response:
                content = response.read(15_000_001)
            if len(content) > 15_000_000:
                raise ValueError('File exceeds 15 MB')
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                alpha = image.getchannel('A') if 'A' in image.getbands() else None
                record = {**item, 'width': image.width, 'height': image.height, 'mode': image.mode,
                          'format': image.format, 'alpha_extrema': alpha.getextrema() if alpha else None,
                          'alpha_bbox': alpha.getbbox() if alpha else None,
                          'usable': alpha is not None and alpha.getextrema()[0] == 0 and alpha.getextrema()[1] > 0}
            path = output/(item['id']+'.png')
            path.write_bytes(content)
            record.update(local_path=str(path.relative_to(ROOT)).replace('\\', '/'), sha256=hashlib.sha256(content).hexdigest(),
                          rights_status='original_rights_retained; commercial_reuse_unverified', status='downloaded')
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
            if record['usable']:
                break
        except Exception as error:
            records.append({**item, 'status': 'failed', 'error': str(error)})
            print(item['id'], str(error), flush=True)
    (output/'sources.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
