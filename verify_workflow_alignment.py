"""Check every saved workflow against the running ComfyUI interface registry."""
import argparse
from pathlib import Path
import poster
from run_category_matrix import request


def verify(base):
    registry=request(base,'/object_info');catalog=poster.read(poster.ROOT/'workflows/QUALITY_ALIGNMENT.json')
    rows=[]
    for entry in catalog['workflows']:
        graph=poster.read(poster.ROOT/entry['path']);issues=[]
        ui='nodes' in graph
        nodes=graph['nodes'] if ui else [{'type':n['class_type'],'api_inputs':n['inputs']} for n in graph.values()]
        for node in nodes:
            name=node['type']
            if name not in registry:
                issues.append('Unregistered node: '+name);continue
            if name in ('ProductDirectorLoop','ClothingDirectorLoop'):
                values=node['widgets_values'];required=registry[name]['input']['required']
                if values[1] not in required['category'][0]:issues.append('Unsupported category')
                if name=='ClothingDirectorLoop':
                    for field,index in [('garment_type',2),('display_mode',3)]:
                        if values[index] not in required[field][0]:issues.append('Unsupported '+field)
        requires_upload=ui and any(n['type']=='LoadImage' and not n.get('widgets_values',[''])[0] for n in nodes)
        rows.append({**entry,'registered_interfaces_ok':not issues,'issues':issues,
            'requires_product_upload':requires_upload,'full_visual_run_verified':False})
    return {'scope':'registered node interfaces and saved presets; not commercial visual certification',
        'quality_profile':catalog['quality_profile'],'workflows':rows,
        'all_registered_interfaces_ok':all(r['registered_interfaces_ok'] for r in rows)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--comfy-url',default='http://127.0.0.1:8191')
    parser.add_argument('--output',default='samples/categories/commercial-alignment-fixed-20261003/interfaces.json')
    args=parser.parse_args();path=(poster.ROOT/args.output).resolve()
    if not path.is_relative_to(poster.ROOT/'samples'):parser.error('Output must be inside project samples')
    result=verify(args.comfy_url);poster.write(path,result)
    print('Interfaces:',len(result['workflows']),'workflows; all available:',result['all_registered_interfaces_ok'])
    if not result['all_registered_interfaces_ok']:raise SystemExit(1)
