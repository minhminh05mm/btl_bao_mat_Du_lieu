"""CLI for sanitized, run-linked provenance; writes no application state."""
import json
from environment_manifest import main
if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'status':'collection_failed','error_type':type(error).__name__}))
        raise SystemExit(1)
