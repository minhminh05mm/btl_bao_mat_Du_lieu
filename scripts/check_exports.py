"""Read-only check that generated public evidence contains no local secrets."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
secret_dir = ROOT / 'runtime' / 'secrets'
config = json.loads((secret_dir / 'config.json').read_text())
material = json.loads((secret_dir / 'bao-init.json').read_text())

def values(item):
    if isinstance(item, dict):
        for value in item.values():
            yield from values(value)
    elif isinstance(item, list):
        for value in item:
            yield from values(value)
    elif isinstance(item, str) and len(item) >= 16:
        yield item.encode()

needles = set(values(config)) | set(values(material))
for directory in [secret_dir, ROOT / 'runtime' / 'pki', ROOT / 'runtime' / 'api-secrets']:
    for file in directory.iterdir():
        if file.is_file() and (file.suffix == '.key' or file.name in {'bao-app-token', 'proxy-secret', 'restic-password'}):
            needles.add(file.read_bytes().strip())
needles.discard(b'')
violations = []
files = 0
for directory in ['results', 'docs', 'app', 'lab', 'tests', 'policies', 'scripts']:
    for file in (ROOT / directory).rglob('*'):
        if not file.is_file() or '__pycache__' in file.parts or file.suffix in {'.png', '.jpg', '.pyc'}:
            continue
        files += 1
        content = file.read_bytes()
        if any(secret in content for secret in needles):
            violations.append(str(file.relative_to(ROOT)))
report = {'files_scanned': files, 'secret_values_checked': len(needles),
          'violations': violations, 'passed': not violations,
          'scope': 'Exact local credentials/key values in source, documentation and exported evidence; generated private runtime/infra excluded.'}
print(json.dumps(report))
(ROOT / 'results' / 'export-secret-check.json').write_text(json.dumps(report, indent=2))
raise SystemExit(1 if violations else 0)
