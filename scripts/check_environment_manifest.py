"""Validate saved sanitized provenance without touching services or dataset."""
import argparse,json
from pathlib import Path
from environment_manifest import validate_manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args=parser.parse_args()
    data=json.loads(Path(args.manifest).read_text(encoding='utf-8-sig'))
    result=validate_manifest(data)
    print(json.dumps({'run_id':data.get('run_id'),'phase':data.get('phase'),'validation':result}))
    raise SystemExit(0 if result['complete'] else 1)
