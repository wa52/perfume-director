"""Combine public batch reports without hiding earlier failures or re-running AI."""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tags', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    for name in [args.output, *args.tags]:
        if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            raise ValueError('Invalid report name')
    reports = ROOT/'samples/matrix'
    products = json.loads((ROOT/'assets/products/test-products-15.json').read_text(encoding='utf-8'))['products']
    attempts = {item['id']: [] for item in products}
    for tag in args.tags:
        source = reports/tag/'summary.json'
        if not source.exists():
            continue
        for record in json.loads(source.read_text(encoding='utf-8'))['products']:
            if record['product_id'] in attempts:
                attempts[record['product_id']].append({'tag': tag, **record})
    records, cards = [], []
    complete = selected_count = 0
    for item in products:
        history = attempts[item['id']]
        chosen = next((r for r in reversed(history) if r['status'] == 'COMPLETED'), history[-1] if history else None)
        directions = chosen.get('directions', []) if chosen else []
        selected = [(d, next((v for v in d.get('versions', []) if v['version'] == d.get('selected_version')), None)) for d in directions]
        selected = [(d, v) for d, v in selected if v and v.get('preview')]
        complete += bool(chosen and chosen['status'] == 'COMPLETED' and len(selected) == 4)
        selected_count += len(selected)
        record = {'product_id': item['id'], 'status': chosen['status'] if chosen else 'PENDING',
                  'selected_tag': chosen['tag'] if chosen else None, 'selected_directions': len(selected),
                  'attempts': [{'tag': r['tag'], 'status': r['status'], 'error_type': r.get('error_type'),
                                'error': r.get('error')} for r in history], 'directions': directions}
        records.append(record)
        title = html.escape(item['brand']+' '+item['name'])
        card = '<article><h2>'+title+'</h2><p>'+html.escape(record['status'])+' · '+str(len(selected))+'/4 个方向</p><div class="images">'
        for direction, version in selected:
            relative = '../'+chosen['tag']+'/'+version['preview']
            if not (reports/chosen['tag']/version['preview']).is_file():
                raise FileNotFoundError(relative)
            card += '<figure><img loading="lazy" src="'+html.escape(relative, quote=True)+'"><figcaption>'+html.escape(direction['name'])+' · V'+str(version['version'])+' · '+html.escape(direction['status'])+'</figcaption></figure>'
        card += '</div><details><summary>尝试记录与完整证据</summary><ul>'
        for attempt in history:
            card += '<li><a href="../'+attempt['tag']+'/gallery.html">'+html.escape(attempt['tag'])+'</a> · '+html.escape(attempt['status'])+'</li>'
        cards.append(card+'</ul></details></article>')
    out = reports/args.output
    out.mkdir(parents=True, exist_ok=True)
    summary = {'products_requested': len(products), 'products_with_four_directions': complete,
               'selected_directions': selected_count, 'source_tags': args.tags, 'products': records}
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>香水跨商品测试总览</title>
<style>body{margin:0;padding:32px;background:#151719;color:#eee;font:16px/1.6 system-ui}header{max-width:1000px}h1{font-size:34px}h2{font-size:22px;margin:0}p,figcaption{color:#bbc0c6}article{margin:32px 0;padding:24px;background:#232629}.images{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}figure{margin:0}img{width:100%;height:auto}figcaption{font-size:13px}a{color:#a5caff}details{margin-top:16px}@media(max-width:900px){.images{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){body{padding:12px}article{padding:12px}.images{grid-template-columns:1fr}}</style>'''
    page += '<header><h1>100 张参考 · 15 款香水自动测试</h1><p>'+str(complete)+'/'+str(len(products))+' 款已有完整四方向；'+str(selected_count)+'/60 个方向已有选中海报。优先展示最新完整批次，保留此前失败；各批次采用的引擎快照与两轮评审在证据页。</p><p>完成生成不等于审美通过。参考是广告与商业静物混合库；预览为 JPEG。图中评分、PASS 或 NEEDS_REVIEW 来自模型评审，不能代替人工判断。</p></header>'+''.join(cards)+'</html>'
    (out/'gallery.html').write_text(page, encoding='utf-8')
    print(f'Overview: {complete}/{len(products)} complete products, {selected_count}/60 selected directions')


if __name__ == '__main__':
    main()
