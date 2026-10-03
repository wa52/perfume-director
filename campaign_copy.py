"""Automatic, concept-specific copy with immutable identity and independent review."""
import copy


def validate(value,concepts,identity):
    rows=value.get('directions') if isinstance(value,dict) else None
    ids={c['id'] for c in concepts}
    if not isinstance(rows,list) or len(rows)!=4:raise ValueError('Four campaign copy directions required')
    found={};titles=set()
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'creative_id','title','subtitle','rationale'}:raise ValueError('Copy may only author headline and subhead')
        id=row['creative_id']
        if not isinstance(id,str) or id not in ids or id in found:raise ValueError('Copy IDs must match concepts exactly once')
        for field,limit in [('title',64),('subtitle',96),('rationale',1000)]:
            if not isinstance(row[field],str) or not row[field].strip() or len(row[field])>limit or any(c in row[field] for c in '\n\r\x00'):raise ValueError('Invalid copy '+field)
        title=' '.join(row['title'].casefold().split())
        if title in titles:raise ValueError('Headlines repeat across creative propositions')
        titles.add(title);words=copy.deepcopy(identity);words.update(title=row['title'],subtitle=row['subtitle'])
        found[id]=words
    if set(found)!=ids:raise ValueError('Missing concept copy')
    return found


def stage(engine,config,product,brief,folder,concepts,identity):
    prompt=('Act as campaign copywriter. Write a specific short headline and subhead for EACH of these four approved advertising propositions. '
        'Return {directions:[{creative_id,title,subtitle,rationale}]}. IDs must exactly match, headlines distinct, single-line strings. '
        'A slogan must express its actual visual event and audience situation, not generic GOOD TIMES or a product category. '
        'Do not repeat the same brand/product name as every headline. User exact requested wording and prohibitions override creative freedom. '
        'Never invent price, promotion, launch, provenance, health, ingredient, performance or historical claims. '
        'Brand/logo and supplied price are immutable and handled separately by the program. Only author title/subtitle. '
        'Brief: '+brief+' Identity: '+engine.json.dumps(identity,ensure_ascii=False)+' Concepts: '+engine.json.dumps(concepts,ensure_ascii=False))
    error=''
    for attempt in range(3):
        value=engine.vision(config,prompt+error,[product],folder/f'CampaignCopy-{attempt+1}-call.json')
        engine.write(folder/f'CampaignCopy-{attempt+1}.json',value)
        try:
            words=validate(value,concepts,identity)
            assessment=engine.vision(config,'Independently review the four campaign copies against their visual propositions and the user brief. '
                'Return {directions:[{creative_id,concept_fit:boolean,brand_fit:boolean,claim_safe:boolean,memory_clear:boolean,evidence:string}]}. '
                'Every ID exactly once; reject generic interchangeable slogans, unsupported factual claims, user wording/prohibition violations, '
                'and a memorable phrase unrelated to the visible creative event. Brief: '+brief+' Identity: '+engine.json.dumps(identity,ensure_ascii=False)+
                ' Concepts: '+engine.json.dumps(concepts,ensure_ascii=False)+' Proposed copy: '+engine.json.dumps(value,ensure_ascii=False),
                [product],folder/f'CampaignCopyReview-{attempt+1}-call.json')
            engine.write(folder/f'CampaignCopyReview-{attempt+1}.json',assessment)
            rows=assessment.get('directions',[]) if isinstance(assessment,dict) else []
            if len(rows)!=4 or any(not isinstance(r,dict) for r in rows) or {r.get('creative_id') for r in rows}!=set(words):raise ValueError('Incomplete copy review')
            for row in rows:
                if not isinstance(row.get('evidence'),str) or not row['evidence'].strip():raise ValueError('Missing copy review evidence')
                if any(row.get(k) is not True for k in ('concept_fit','brand_fit','claim_safe','memory_clear')):raise ValueError('Copy rejected: '+engine.json.dumps(row,ensure_ascii=False))
            engine.write(folder/'CampaignCopy.json',{'copy_by_creative_id':words,'review':assessment,'identity_locked':True})
            return words
        except ValueError as exc:
            if attempt==2:raise
            error=' Repair the entire set using these actual validation/review failures: '+str(exc)+' Previous proposal: '+engine.json.dumps(value,ensure_ascii=False)
    raise ValueError('Campaign copy did not pass')
