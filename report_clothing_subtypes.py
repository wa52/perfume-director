"""Publish honest subtype qualification progress from exported evidence only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

ROOT=Path(__file__).resolve().parent


def report(folder,manifest):
    path=folder/'summary.json'
    summary=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    observed={r['case_id']:r for r in summary}
    rows=[]
    for fixture in manifest:
        key=fixture['case_id'];state=observed.get(key,{'status':'QUEUED','selected_directions':0,'model_pass_directions':0})
        row={k:state.get(k) for k in ('status','stage','selected_directions','model_pass_directions')}
        row.update(case_id=key,input_sha256=fixture['sha256'],input_limitations=fixture.get('input_limitations',[]))
        for evidence in (folder/key).glob('concept-*/evidence.json'):
            value=json.loads(evidence.read_text(encoding='utf-8'))
            assert value['input_sha256']==fixture['sha256'],'Exported evidence belongs to a different input'
            assert hashlib.sha256(evidence.with_name('poster.png').read_bytes()).hexdigest()==value['poster_sha256'],'Exported PNG differs from evidence'
        rows.append(row)
    terminal=all(r['status'] in ('COMPLETED','PARTIAL','ERROR') for r in rows)
    payload={'updated_at':datetime.now(timezone.utc).isoformat(),'execution_finished':terminal,
        'commercial_quality_certified':False,'scope':'One real product per explicit subtype; auto presets are aliases. Not repeated-run stability or fit certification.',
        'planned_cases':len(rows),'planned_directions':4*len(rows),'cases':rows}
    text=json.dumps(payload,ensure_ascii=False,indent=2)
    (folder/'coverage.tmp').write_text(text,encoding='utf-8');(folder/'coverage.tmp').replace(folder/'coverage.json')
    lines=['# Clothing subtype qualification','',
        'Actual ComfyUI ClothingDirectorLoop with Qwen planning, copy review, rendering and image critique. Each case requests four directions under the existing iteration budget. Creative/copy rejection can stop a case before rendering. Such failures remain visible and are not counted as successful posters.','',
        'Execution finished: '+str(terminal)+'. Commercial quality certified: **false**.','',
        '| Case | State | Selected posters | Model passes |','|---|---|---:|---:|']
    lines += [f"| {r['case_id']} | {r['status']} | {r.get('selected_directions') or 0} | {r.get('model_pass_directions') or 0} |" for r in rows]
    lines += ['', '[Actual selected images](gallery.html). [Input contact sheet](../../../assets/products/clothing/subtypes/inputs-contact.jpg).', '',
        'This is one-fixture coverage, not multi-product stability. The merchandising audience is supplied by the test brief; it does not infer personal gender or certify manufacturer sizing. Garment-specific references fall back explicitly to same-audience references when fewer than three brands match. Reference scarcity can constrain creative quality.','',
        'Original RGB, labels, clothing construction and existing wearer photographs are preserved; no wearer is generated. The official Rifo women blazer uses a deterministic matte with unchanged original RGB. Source provenance and preprocessing are in the manifest. PNGimg/StickPNG examples are non-commercial testing fixtures; this run does not grant commercial source rights.','', '## Input limitations','']
    lines += [r['case_id']+': '+'; '.join(r['input_limitations']) for r in rows if r['input_limitations']]
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return terminal


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag',default='clothing-subtypes-20261004')
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    if not args.tag.replace('-','').isalnum():parser.error('Invalid tag')
    folder=ROOT/'samples/categories'/args.tag;folder.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((ROOT/'assets/products/clothing/subtypes/manifest.json').read_text(encoding='utf-8'))
    transient_failures=0
    while True:
        try:
            finished=report(folder,manifest)
            transient_failures=0
        except (json.JSONDecodeError,FileNotFoundError,AssertionError):
            # Export may be replacing an image before its matching evidence.
            # Never publish a partially read snapshot; retry, then fail visibly.
            transient_failures+=1
            if transient_failures>=5:raise
            time.sleep(1)
            continue
        if finished or not args.watch:break
        time.sleep(30)
    print('Clothing report updated; execution_finished:',finished)
