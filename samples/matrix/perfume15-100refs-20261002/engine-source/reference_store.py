"""SQLite Design KB: original image bytes, provenance, and explicit annotation origin."""
from contextlib import closing
import hashlib
import html
import json
from pathlib import Path
import shutil
import sqlite3
import random
from urllib.parse import urlsplit
from datetime import datetime, timezone


def connect(root):
    path = Path(root)/'kb/design_kb.sqlite3'
    path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('''CREATE TABLE IF NOT EXISTS reference_images (
        id TEXT PRIMARY KEY, brand TEXT NOT NULL, style TEXT NOT NULL,
        reference_kind TEXT NOT NULL, source_url TEXT NOT NULL, image_url TEXT NOT NULL,
        local_path TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
        sha256 TEXT NOT NULL UNIQUE, image_bytes BLOB NOT NULL,
        selection_reason TEXT NOT NULL, analysis_json TEXT NOT NULL,
        analysis_origin TEXT NOT NULL, rights_status TEXT NOT NULL, acquired_at TEXT NOT NULL
    )''')
    return conn


def import_curated(root):
    root = Path(root)
    downloads = {row['id']: row for row in json.loads((root/'references/downloads.json').read_text(encoding='utf-8'))}
    selections = json.loads((root/'references/curated.json').read_text(encoding='utf-8'))
    accepted = [row for row in selections if row['accepted']]
    # Validate all image data before mutating the database.
    prepared = []
    for selection in accepted:
        row = downloads[selection['id']]
        if row['status'] != 'downloaded':
            raise ValueError(f"Reference not downloaded: {row['id']}")
        content = (root/row['path']).read_bytes()
        if hashlib.sha256(content).hexdigest() != row['sha256']:
            raise ValueError('Image checksum mismatch')
        style = selection.get('style','luxury')
        if style not in ('luxury','editorial','minimal','experimental','tech','fashion'):
            raise ValueError('Invalid reference style')
        target = root/'references'/style/Path(row['path']).name
        prepared.append((selection, row, content, target))
    if len({row['sha256'] for _, row, _, _ in prepared}) != len(prepared):
        raise ValueError('Duplicate reference image content')
    with closing(connect(root)) as conn, conn:
        for selection, row, content, target in prepared:
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(root/row['path'], target)
            conn.execute('''INSERT INTO reference_images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET selection_reason=excluded.selection_reason,
                analysis_json=CASE WHEN reference_images.analysis_origin='vision_api' THEN reference_images.analysis_json ELSE excluded.analysis_json END,
                analysis_origin=CASE WHEN reference_images.analysis_origin='vision_api' THEN reference_images.analysis_origin ELSE excluded.analysis_origin END''',
                (row['id'], selection.get('brand',row.get('brand','Unknown')), selection.get('style','luxury'), selection['reference_kind'], row['source_url'], row['image_url'],
                 str(target.relative_to(root)).replace('\\', '/'), row['width'], row['height'], row['sha256'], content,
                 selection['reason'], json.dumps(selection['analysis'], ensure_ascii=False), selection.get('analysis_origin','codex_visual_review'),
                 'copyright_retained_by_original_owner; reuse_license_unverified', datetime.now(timezone.utc).isoformat()))
    export(root)


def entries(root):
    with closing(connect(root)) as conn:
        rows = conn.execute('SELECT id,brand,style,reference_kind,source_url,local_path,selection_reason,analysis_json,analysis_origin FROM reference_images ORDER BY id').fetchall()
    return [{'id': row['id'], 'brand': row['brand'], 'style': row['style'], 'reference_kind': row['reference_kind'],
             'source_url': row['source_url'], 'image': row['local_path'], 'selection_reason': row['selection_reason'],
             'analysis': json.loads(row['analysis_json']), 'analysis_origin': row['analysis_origin']} for row in rows]


def select(root, limit=3, direction=None):
    colors = {'black-gold':('black','gold','silver'), 'cream-minimal':('beige','warm_white','peach'),
              'burgundy-editorial':('burgundy','red','purple'), 'botanical':('green','mint_green','warm_white','pink')}
    def relevance(row):
        observed = row['analysis'].get('color', [])
        matches = sum(color in observed for color in colors.get(direction,()))
        penalty = 20 if direction == 'cream-minimal' and 'black' in observed and 'beige' not in observed else 0
        return row['analysis']['perfume_suitability']+matches*25-penalty
    ranked = sorted(entries(root), key=relevance, reverse=True)
    selected, brands = [], set()
    # Avoid choosing three variants from the same brand/campaign.
    for row in ranked:
        if row['brand'] not in brands:
            selected.append(row)
            brands.add(row['brand'])
        if len(selected) == limit:
            return selected
    return (selected+[row for row in ranked if row not in selected])[:limit]


def planning_pool(root, limit=8):
    """Quality-weighted diverse examples; never confuse label text with poster type."""
    pool=entries(root)
    random.SystemRandom().shuffle(pool)
    selected=[];brands=set();features=set();sources={}
    def tags(row):
        a=row['analysis']
        return {(k,str(a.get(k,''))) for k in ('composition','lighting','typography','negative_space')}|{('style',row['style'])}
    while pool and len(selected)<limit:
        eligible=[r for r in pool if r['brand'] not in brands and r['brand'].lower()!='unknown']
        if not eligible:break
        def score(row):
            a=row['analysis'];domain=urlsplit(row['source_url']).netloc
            compatibility=a.get('renderer_compatibility',35 if a.get('subject_ratio',.2)<.08 else 75)
            type_bonus=12 if a.get('has_campaign_typography') and not any(r['analysis'].get('has_campaign_typography') for r in selected) else 0
            return a.get('perfume_suitability',70)*.5+compatibility*.25+len(tags(row)-features)*7+type_bonus-sources.get(domain,0)*12
        row=max(eligible,key=score);selected.append(row);pool.remove(row)
        brands.add(row['brand']);features.update(tags(row))
        domain=urlsplit(row['source_url']).netloc;sources[domain]=sources.get(domain,0)+1
    return selected


def update_analysis(root, local_path, analysis):
    with closing(connect(root)) as conn, conn:
        conn.execute('UPDATE reference_images SET analysis_json=?, analysis_origin=? WHERE local_path=?',
                     (json.dumps(analysis, ensure_ascii=False), 'vision_api', local_path.replace('\\', '/')))


def export(root):
    root = Path(root)
    rows = entries(root)
    (root/'kb/luxury.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    source_lines = ['# 香水参考来源', '', f'共 {len(rows)} 张。图像原文件及来源、审美标注保存在 kb/design_kb.sqlite3；入选图按风格存放。',
        '每项 analysis_origin 记录实际标注来源；新增记录为千问视觉 API 分析，原20张保留原标注。subject_ratio 为粗略估计，评分为选图偏好，不是成品质量分。商业静物与含排版广告分别标注，不将无文字摄影称为完整海报。',
        '版权属于原权利人，未核实商业复用授权。部分图片为媒体或零售渠道转载，未据此声称为品牌官网原始发布。', '',
        '| 作品 | 来源 | 类型 | 入选理由 |', '| --- | --- | --- | --- |']
    cards = []
    for row in rows:
        source_lines.append(f"| {row['id']} | [来源]({row['source_url']}) | {row['reference_kind']} | {row['selection_reason']} |")
        esc = html.escape
        cards.append(f'''<article><a href="../{esc(row['image'])}"><img loading="lazy" src="../{esc(row['image'])}" alt="{esc(row['id'])}"></a>
        <h2>{esc(row['brand'])}</h2><p>{esc(row['id'])} · {esc(row['reference_kind'])}</p><p>{esc(row['selection_reason'])}</p>
        <a href="{esc(row['source_url'], quote=True)}" target="_blank" rel="noopener noreferrer">来源网页 ↗</a></article>''')
    (root/'references/sources.md').write_text('\n'.join(source_lines)+'\n', encoding='utf-8')
    gallery = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>香水审美参考库</title><style>body{background:#171918;color:#eeeae0;font:16px/1.7 system-ui;margin:0;padding:40px}
    header{max-width:800px;margin-bottom:36px}h1{font-size:40px;margin:0}header p{color:#bbb9af}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}
    article{background:#242824;padding:18px}img{width:100%;height:340px;object-fit:contain;background:#131613}h2{font-size:21px;margin:16px 0 0}
    article p{font-size:14px;color:#c2c6bc}a{color:#d5c292}article>a:first-child{display:block}</style>
    <header><h1>香水审美参考库</h1><p>'''+str(len(rows))+''' 张广告与商业静物参考 · 按商品视觉、留白、色彩和信息层级挑选。
    每张保存实际标注来源，面积比例为估计值。原作品版权保留，未核实复用授权。</p></header><main class="grid">'''+''.join(cards)+'</main></html>'
    (root/'references/gallery.html').write_text(gallery, encoding='utf-8')


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    import_curated(root)
    print(f'Imported {len(entries(root))} references into kb/design_kb.sqlite3')
