"""Check tracked/unignored submission files without printing any secret value."""
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                                cwd=root).decode().split('\0')
files = [name for name in files if name]
for name in files:
    parts = Path(name).parts
    assert not any(part in {'.local-test', 'node_modules', '.next', '.venv', 'venv', '__pycache__'} for part in parts), name
    assert not (Path(name).name.startswith('.env') and Path(name).name != '.env.example'), name

local_env = root / '.local-test' / '.env'
if local_env.exists():
    values = [line.split('=', 1)[1] for line in local_env.read_text(encoding='utf-8-sig').splitlines()
              if '=' in line and len(line.split('=', 1)[1]) >= 24]
    for name in files:
        data = (root / name).read_bytes()
        assert not any(value.encode() in data for value in values), f'Local test secret included: {name}'

for prefix in ['app', 'components', 'api']:
    for file in (root / 'monitor' / 'next-frontend' / prefix).rglob('*.js'):
        text = file.read_text(encoding='utf-8')
        assert not any(secret in text for secret in ['DB_PASSWORD', 'SECRET_KEY', 'EVENT_TOKEN', 'NEXT_PUBLIC_']), file.name

required = ['general/.env.example', 'monitor/backend/.env.example',
            'monitor/next-frontend/.env.example', 'general/sql/deploy.sql',
            'monitor/backend/sql/deploy.sql']
for name in required:
    assert name in files, f'Missing or ignored: {name}'
for prefix in ['general', 'monitor/backend']:
    text = (root / prefix / '.env.example').read_text(encoding='utf-8')
    assert 'SENTRY_DSN=\n' in text and 'ENABLE_SENTRY_TEST=false' in text
    sql = (root / prefix / 'sql' / 'deploy.sql').read_text(encoding='utf-8').upper()
    assert 'DROP ' not in sql and 'TRUNCATE ' not in sql and 'DELETE ' not in sql
print(f'PASS {len(files)} candidate files: environment/generated file exclusions, local secret exclusion, browser secret exclusion, required examples and non-destructive SQL')
