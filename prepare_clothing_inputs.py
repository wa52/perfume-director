"""Download two attributed, non-commercial clothing fixtures and generate UI graphs."""
import copy
import hashlib
import io
import requests
from bs4 import BeautifulSoup
from PIL import Image
import poster
from categories import GARMENT_TYPES, PROFILES

ROOT=poster.ROOT
BRIEF='为这件服装探索四个明显不同的商业海报方向。保留完整版型、面料纹理和图案；保留原图展示方式。只使用可确认的品牌和名称，不编造面料成分、功效、价格或季节信息。'
FIXTURES=[('menswear','tshirt','https://pngimg.com/image/5447'),('womenswear','dress','https://pngimg.com/image/56146')]


def workflows():
    base=poster.read(ROOT/'workflows/categories/footwear.ui.json')
    folder=ROOT/'workflows/clothing';folder.mkdir(parents=True,exist_ok=True)
    for category in ('menswear','womenswear'):
        types=['auto','shirt','tshirt','knitwear','tailoring','outerwear','trousers','activewear']
        if category=='womenswear':types+=['dress','skirt']
        for kind in types:
            graph=copy.deepcopy(base);load,node=graph['nodes']
            # Specific presets require the user's matching product, not the pilot fixture.
            load['widgets_values']=[category+'.png','image']
            load['title']='上传对应服装透明 PNG（示例图片需替换）'
            node.update(type='ClothingDirectorLoop',title=PROFILES[category]['label']+' · '+GARMENT_TYPES[kind]+' · 四方向闭环')
            node['properties']['Node name for S&R']='ClothingDirectorLoop'
            node['widgets_values']=[BRIEF,category,kind,'auto']
            poster.write(folder/(category+('-'+kind if kind!='auto' else '')+'.ui.json'),graph)


def main():
    workflows();folder=ROOT/'assets/products/clothing';folder.mkdir(parents=True,exist_ok=True);rows=[]
    for category,kind,page in FIXTURES:
        response=requests.get(page,timeout=30);response.raise_for_status()
        soup=BeautifulSoup(response.text,'html.parser')
        links=[tag.get('href','') for tag in soup.select('a[href]')]
        links+=[tag.get('src','') for tag in soup.select('img[src]')]
        url=next(url for url in links if '/uploads/' in url and url.lower().endswith('.png'))
        response=requests.get(url,timeout=40);response.raise_for_status();content=response.content
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            if image.format!='PNG' or min(image.size)<500 or 'A' not in image.getbands() or image.getchannel('A').getextrema()!=(0,255):
                raise ValueError('Expected a large transparent clothing PNG')
            width,height=image.size
        path=folder/(category+'.png');path.write_bytes(content)
        (ROOT/'runtime/input'/(category+'.png')).write_bytes(content)
        rows.append({'id':category+'-pilot','product_category':category,'garment_type':kind,'display_mode':'auto',
            'local_path':path.relative_to(ROOT).as_posix(),'source_url':page,'image_url':url,
            'sha256':hashlib.sha256(content).hexdigest(),'width':width,'height':height,'brief':BRIEF,
            'audience_basis':'test merchandising category; not inferred from a person',
            'rights_status':'CC BY-NC 4.0; PNGimg attribution; non-commercial test fixture only'})
    poster.write(folder/'products.json',rows)
    print('Prepared',len(rows),'transparent clothing fixtures and 18 UI workflows')


if __name__=='__main__':main()
