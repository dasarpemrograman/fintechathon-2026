"""Container-executed developer setup and read-only readiness helpers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import time
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def fail(message):
    raise SystemExit(message)


def project_name(value):
    import re
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", value):
        fail("Use a lowercase Compose project name containing letters, digits, '-' or '_'.")
    return value


def canonical(value):
    value = value.replace('\\', '/').rstrip('/')
    return value.casefold() if len(value) > 1 and value[1] == ':' else value


def inventory(rows, expected_root, requested_mode=None):
    modes = set()
    active_modes = set()
    running = 0
    for row in rows:
        labels = row.get('Config', {}).get('Labels') or {}
        if canonical(labels.get('com.docker.compose.project.working_dir', '')) != canonical(expected_root):
            fail('A same-named Compose project belongs to another checkout. Choose COMPOSE_PROJECT_NAME or stop it from its own checkout.')
        running += bool(row.get('State', {}).get('Running'))
        if labels.get('com.docker.compose.service') in {'api', 'worker'}:
            mode = next((v.split('=', 1)[1] for v in row['Config'].get('Env', []) if v.startswith('APP_MODE=')), None)
            if mode:
                modes.add(mode)
                if row.get('State', {}).get('Running'):
                    active_modes.add(mode)
    if len(active_modes) > 1:
        fail('Project services have mixed modes. Run dev stop before starting again.')
    modes = active_modes or modes
    mode = next(iter(modes), 'unknown')
    if active_modes and requested_mode and mode not in {requested_mode, 'unknown'}:
        fail('Project is running in '+mode+' mode. Run dev stop, then explicitly start the requested mode.')
    return mode, running, len(rows)


def private_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)


def prepare(root, existing_db, existing_runtime, project):
    password = root/'.local/db-password'
    if existing_db and (not password.is_file() or not password.read_bytes().strip()):
        fail('Existing database is missing .local/db-password. Restore the original secret; do not reset the volume.')
    try:
        initialized = json.loads(state_path(root, project).read_text()).get('initialized', False)
    except (OSError, ValueError):
        initialized = False
    if existing_db and not existing_runtime and initialized:
        fail('Existing database is missing its runtime volume. Restore the matching runtime/encryption key before startup.')
    (root/'.local').mkdir(exist_ok=True, mode=0o700)
    if not password.exists():
        private_write(password, secrets.token_urlsafe(32).encode())
    if not (root/'.env').exists():
        private_write(root/'.env', (root/'.env.example').read_bytes())
    directory = root/'.local/dev'/project
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    print('Local configuration prepared; existing values preserved. Provider keys are optional.')


def fingerprint(root):
    excluded = {'.git', '.local', '.venv', 'node_modules', '.next', '__pycache__', '.pytest_cache', '.playwright', 'test-results', 'playwright-report'}
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in excluded and not (Path(directory)/d).is_symlink())
        for name in sorted(files):
            path = Path(directory)/name
            if path.is_symlink() or name.endswith(('.pyc', '.tsbuildinfo')):
                continue
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def state_path(root, project):
    return root/'.local/dev'/project/'state.json'


def reusable(root, project, mode):
    try:
        state = json.loads(state_path(root, project).read_text())
        return state['ready'] and state['mode'] == mode and state['fingerprint'] == fingerprint(root)
    except (OSError, ValueError, KeyError):
        return False


def set_state(root, project, mode, ready):
    path = state_path(root, project)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps({'project': project, 'mode': mode, 'initialized': True, 'ready': ready, 'fingerprint': fingerprint(root)}))
    temp.chmod(0o600)
    temp.replace(path)


def check_ports(ports):
    probes = []
    try:
        for port in ports:
            if not 1 <= port <= 65535:
                fail('Explicit ports must be between 1 and 65535.')
            probe = socket.socket()
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probes.append(probe)
            try:
                probe.bind(('127.0.0.1', port))
            except OSError:
                fail('Loopback port '+str(port)+' is occupied. Stop its owner explicitly or configure an explicit ALLEXPORT_WEB_PORT / ALLEXPORT_API_PORT; no process was stopped.')
    finally:
        for probe in probes:
            probe.close()


def readiness(mode, timeout):
    deadline = time.monotonic()+timeout
    stage = 'API/database/worker'
    while True:
        try:
            stage = 'API/database/worker'
            with urlopen('http://api:8000/health', timeout=3) as response:
                value = json.load(response)
                if value.get('status') != 'ready' or value.get('mode') != mode:
                    raise ValueError('matching worker not ready')
            stage = 'web'
            with urlopen('http://web:3000/', timeout=3) as response:
                if response.status != 200:
                    raise ValueError('web unavailable')
            if mode == 'demo':
                stage = 'seeded demo identities'
                with urlopen('http://api:8000/v2/auth/demo-identities', timeout=3) as response:
                    if not json.load(response)['result']['users']:
                        raise ValueError('demo seed absent')
            print('Web, API, database and matching worker ready'+('; seeded synthetic identities available.' if mode == 'demo' else '.'))
            return
        except (OSError, ValueError, KeyError):
            if time.monotonic() >= deadline:
                fail('Readiness failed at '+stage+'. Run dev doctor and inspect the private stage logs.')
            time.sleep(1)


def check_data_key():
    # Import settings/storage, never cipher(): a missing key must not regenerate.
    import sqlalchemy as sa
    from services.api import store
    from services.api.settings import settings
    with store.engine.connect() as conn:
        tables = sa.inspect(conn).get_table_names()
        encrypted = sum(conn.scalar(sa.text('SELECT count(*) FROM '+name)) for name in ['auth_commands', 'connector_credentials'] if name in tables)
    if encrypted and not (settings.storage.parent/'encryption-key').is_file():
        fail('Encrypted application records exist but the installation key is missing. Restore the matching runtime volume/key; startup was stopped.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inventory', 'prepare', 'ports', 'ready', 'key', 'reusable', 'state'])
    parser.add_argument('--root', type=Path, default=Path('/checkout'))
    parser.add_argument('--root-label')
    parser.add_argument('--project', type=project_name, default='allexport')
    parser.add_argument('--mode', choices=['demo', 'normal'])
    parser.add_argument('--existing-db', type=int, choices=[0, 1], default=0)
    parser.add_argument('--existing-runtime', type=int, choices=[0, 1], default=0)
    parser.add_argument('--port', type=int, action='append', default=[])
    parser.add_argument('--timeout', type=int, default=90)
    parser.add_argument('--ready', choices=['yes', 'no'], default='yes')
    args = parser.parse_args()
    if args.command == 'inventory':
        print(*inventory(json.load(sys.stdin), args.root_label, args.mode))
    elif args.command == 'prepare':
        prepare(args.root, args.existing_db, args.existing_runtime, args.project)
    elif args.command == 'ports':
        check_ports(args.port)
    elif args.command == 'ready':
        readiness(args.mode, args.timeout)
    elif args.command == 'key':
        check_data_key()
    elif args.command == 'reusable':
        raise SystemExit(0 if reusable(args.root, args.project, args.mode) else 1)
    elif args.command == 'state':
        set_state(args.root, args.project, args.mode, args.ready == 'yes')


if __name__ == '__main__':
    main()
