"""Re-render an existing direction with the current engine, preserving its original evidence."""
import argparse
import hashlib
from pathlib import Path
import shutil
import poster


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-run',required=True)
    parser.add_argument('--version',type=int,default=1)
    parser.add_argument('--rounds',type=int,default=2)
    parser.add_argument('--spec',help='Optional reviewed replacement PosterSpec; original evidence remains untouched')
    args=parser.parse_args()
    source=Path(args.source_run).resolve()
    request=poster.read(source/'request.json')
    plan=poster.read(source/'Director-plan.json')
    spec=poster.read(Path(args.spec)) if args.spec else poster.read(source/f'v{args.version}/PosterSpec.json')
    config=poster.read(poster.ROOT/'config.local.json')
    config.update(initial_spec=spec, references=request['references'], max_rounds=args.rounds,
                  direction_id='concept-retest', creative_direction=plan['creative_direction'],
                  planning_trace=plan['planning_trace'], direction_seed_offset=0,
                  approved_copy={n:spec[n]['text'] for n in poster.TEXT_LAYERS})
    batch=Path(plan['planning_trace']).parent
    if (batch/'Product-copy.json').exists():
        config['product_profile']=poster.read(batch/'Product-copy.json').get('product_profile',{})
    evidence=poster.ROOT/'runs/retests'/source.name
    evidence.mkdir(parents=True,exist_ok=True)
    hashes={}
    for name in ('poster.py','concepts.py','quality.py','typography.py','reference_store.py','graphic_shapes.py'):
        data=(poster.ROOT/name).read_bytes()
        hashes[name]=hashlib.sha256(data).hexdigest()
        target=evidence/'engine-source'/hashes[name]/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(poster.ROOT/name,target)
    def progress(values):
        if values.get('run_dir'):
            poster.write(evidence/'latest.json',{'source_run':str(source),'source_version':args.version,
                         'run_dir':values['run_dir'],'engine_sha256':hashes})
    poster.run(config,poster.ROOT/request['product'],request['brief'],progress=progress)


if __name__=='__main__':main()
