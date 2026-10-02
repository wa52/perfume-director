"""Export portable visual evidence from a live matrix without private configuration."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont
import poster

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tag',required=True)
    args=parser.parse_args();source=ROOT/'runs/matrix'/args.tag;out=ROOT/'samples/matrix'/args.tag
    out.mkdir(parents=True,exist_ok=True)
    endpoint=poster.read(ROOT/'config.local.json')['vision_base_url']
    products=poster.read(ROOT/'assets/products/test-products-15.json')['products']
    execution=poster.read(source/'execution.json') if (source/'execution.json').exists() else {}
    if execution.get('requested_products'):
        products=[r for r in products if r['id'] in execution['requested_products']]
    requested=len(products)
    records=[];cards=[]
    def safe_copy(path,target):
        target.parent.mkdir(parents=True,exist_ok=True)
        if path.suffix=='.json':
            text=path.read_text(encoding='utf-8').replace(endpoint,'https://YOUR_WORKSPACE_ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')
            target.write_text(text,encoding='utf-8')
        else:shutil.copy2(path,target)
    for item in products:
        trial=source/item['id'];result=trial/'result.json';state=trial/'state.json'
        record=poster.read(result if result.exists() else state) if state.exists() else {'status':'PENDING'}
        record={**record,'product_id':item['id'],'brand':item['brand'],'name':item['name']}
        display=[];safe_dir=out/item['id'];safe_dir.mkdir(exist_ok=True)
        directions=record.get('directions',[])
        # For a live child, include its completed versions even before final selection.
        if record.get('status')=='RUNNING' and record.get('direction_index'):
            live=Path(record.get('run_dir','.'))
            if (live/'result.json').exists():
                d=poster.read(live/'result.json')
                if all(Path(x.get('run_dir','.'))!=live for x in directions):
                    directions=[*directions,{'id':'concept-'+str(record['direction_index']),'name':record.get('direction_name',''),
                        'run_dir':str(live),**d}]
        summary=[]
        for index,direction in enumerate(directions,1):
            original=Path(direction.get('run_dir','.'));target=safe_dir/direction.get('id',f'concept-{index}')
            versions=[]
            for version in direction.get('versions',[]):
                image_path=original/version['poster']
                if not image_path.is_file():continue
                preview=target/f'v{version["version"]}.jpg';preview.parent.mkdir(parents=True,exist_ok=True)
                if not preview.exists():
                    with Image.open(image_path) as im:im.convert('RGB').save(preview,quality=94)
                versions.append({**version,'preview':preview.relative_to(out).as_posix(),
                    'original_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),
                    'preview_sha256':hashlib.sha256(preview.read_bytes()).hexdigest()})
            for path in original.glob('*.json'):safe_copy(path,target/path.name)
            for path in original.glob('v*/*.json'):safe_copy(path,target/path.relative_to(original))
            selected=direction.get('selected',{}).get('version')
            shown=next((v for v in versions if v['version']==selected),None)
            summary.append({'id':direction.get('id'),'name':direction.get('name'), 'status':direction['status'],
                'selected_version':selected,'versions':versions,'error':direction.get('error')})
            if shown:
                display.append((shown['preview'],direction.get('name','')))
                first=versions[0]['preview'];last=shown['preview']
                cards.append('<article><h3>'+html.escape(item['brand']+' '+item['name']+' · '+direction.get('name',''))+'</h3>'
                    '<p>'+html.escape(direction['status'])+' · 首版 '+str(versions[0]['score'])+' → 选中 V'+str(selected)+' '+str(shown['score'])+'</p>'
                    '<div class="pair"><figure><img loading="lazy" src="'+first+'"><figcaption>首次</figcaption></figure>'
                    '<figure><img loading="lazy" src="'+last+'"><figcaption>选中版本（可能仍是首版）</figcaption></figure></div></article>')
        if display:
            sheet=Image.new('RGB',(1200,1680),'#1b1c1e');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23)
            for i,(relative,name) in enumerate(display[:4]):
                im=Image.open(out/relative);im.thumbnail((580,780));x=(i%2)*600+10;y=(i//2)*840+40
                sheet.paste(im,(x,y));draw.text((x,y-33),name[:23],font=font,fill='white')
            sheet.save(safe_dir/'four.jpg',quality=92)
        record['directions']=summary;records.append(record)
        if result.exists():safe_copy(result,safe_dir/'execution-result.json')
        batch_path=record.get('batch_dir')
        if not batch_path:
            candidate=Path(record.get('run_dir','.'))
            if candidate.is_dir() and candidate.parent==ROOT/'runs/batches':batch_path=str(candidate)
        if batch_path:
            for path in (ROOT/batch_path).glob('*.json'):safe_copy(path,safe_dir/'planning'/path.name)
    if (source/'engine-source').exists():shutil.copytree(source/'engine-source',out/'engine-source',dirs_exist_ok=True)
    finished=sum(r['status'] not in ('PENDING','RUNNING') for r in records)
    selected=sum(bool(d.get('selected_version')) for r in records for d in r['directions'])
    summary={'tag':args.tag,'products_finished':finished,'products_requested':requested,'directions_with_selection':selected,
        'reference_count':100,'preview_encoding':'JPEG94 derivative; original and preview SHA recorded separately','products':records}
    serialized=json.dumps(summary,ensure_ascii=False,indent=2).replace(endpoint,'https://YOUR_WORKSPACE_ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1')
    (out/'summary.json').write_text(serialized,encoding='utf-8')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>15款香水自动测试</title>
<style>body{margin:0;background:#151719;color:#eee;font:16px/1.6 system-ui;padding:32px}header{max-width:920px;margin-bottom:36px}h1{font-size:36px}p{color:#b9bfc5}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:30px}article{background:#232629;padding:16px}h3{margin:0;font-size:18px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}figure{margin:0}img{width:100%;height:auto}figcaption{font-size:13px;color:#aeb4b9}@media(max-width:600px){body{padding:16px}.grid{grid-template-columns:1fr}}</style>'''
    page+='<header><h1>'+str(requested)+'款香水 · 自动生成测试</h1><p>'+str(finished)+'/'+str(requested)+' 款流程结束，'+str(selected)+'/'+str(requested*4)+' 个方向已有选中版本。100张参考，真实千问与 ComfyUI。首轮每方向最多两版，用于发现跨商品问题；后续修复另记。</p><p>流程结束不等于审美通过。评分来自模型；保留 NEEDS_REVIEW 与失败，不把分数变化当作人工质量结论。预览为JPEG，原始文件哈希单独保存。</p></header><main class="grid">'+''.join(cards)+'</main></html>'
    (out/'gallery.html').write_text(page,encoding='utf-8');print(f'Exported {finished}/{requested} products, {selected}/{requested*4} selected directions',flush=True)

if __name__=='__main__':main()
