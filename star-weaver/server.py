"""Star Weaver local workbench. Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import copy
import json
import mimetypes
import os
import shutil
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from starweaver import __version__
from starweaver.engine import AXES, Model
from starweaver.heredity import extend_catalog, generate_lineage, load_catalog

ROOT = Path(__file__).resolve().parent
MAX_BODY = 512 * 1024
SUCCESS = {'LEARNED', 'ACTIVE', 'REFUNDED'}


class Conflict(ValueError):
    pass


def bounded_string(value, name, limit=100):
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise ValueError(f'{name} must be a nonempty string of at most {limit} characters')
    return value


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


class SessionStore:
    def __init__(self, state_dir: Path):
        self.lock = threading.RLock()
        self.graph = read_json(ROOT / 'data' / 'star-weaver.fixture.json')
        self.catalog = load_catalog(ROOT / 'data')
        self.decisions = read_json(ROOT / 'data' / 'decisions.json')
        self.path = Path(state_dir) / 'session.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.notice = None
        self.record = self.fresh()
        if self.path.exists():
            try:
                self.record = self.validate_record(read_json(self.path))
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                preserved = self.path.with_suffix('.corrupt.json')
                # Never overwrite a previously preserved damaged save.
                counter = 1
                while preserved.exists():
                    preserved = self.path.with_suffix(f'.corrupt-{counter}.json')
                    counter += 1
                shutil.copyfile(self.path, preserved)
                backup = self.path.with_suffix('.bak.json')
                if backup.exists():
                    try:
                        self.record = self.validate_record(read_json(backup))
                        self.notice = 'Recovered the previous local save. The damaged file was preserved.'
                    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
                        self.notice = 'The damaged save was preserved. A fresh incarnation is open; import a valid backup to recover.'
                else:
                    self.notice = 'The damaged save was preserved. A fresh incarnation is open; import a valid backup to recover.'

    def fresh(self):
        return {'revision': 0, 'state': Model(self.graph).state, 'last_lineage': None,
                'lineage_registry': [], 'request_ids': []}

    def current_catalog(self, registry=None):
        result = copy.deepcopy(self.catalog)
        for lineage in self.record['lineage_registry'] if registry is None else registry:
            result = extend_catalog(result, lineage)
        return result

    def recompute_lineage(self, value, catalog=None):
        if not isinstance(value, dict) or not isinstance(value.get('parent_ids'), list) or len(value['parent_ids']) != 2:
            raise ValueError('Lineage must include two known parent IDs and a seed')
        expected = generate_lineage(catalog or self.current_catalog(), *value['parent_ids'], value.get('seed'))
        if value != expected:
            raise ValueError('Lineage differs from its reproducible parents, seed, or rule set')
        return expected

    def validate_record(self, value):
        if not isinstance(value, dict) or set(value) != {'revision', 'state', 'last_lineage', 'lineage_registry', 'request_ids'}:
            raise ValueError('Save has incompatible session fields')
        if type(value['revision']) is not int or not 0 <= value['revision'] < 1_000_000_000:
            raise ValueError('Invalid revision')
        if not isinstance(value['lineage_registry'], list) or len(value['lineage_registry']) > 30:
            raise ValueError('At most 30 generated parents can be kept')
        catalog = self.current_catalog(value['lineage_registry'])
        if value['last_lineage'] is not None:
            self.recompute_lineage(value['last_lineage'], catalog)
        ids = value['request_ids']
        if not isinstance(ids, list) or len(ids) > 5000 or any(not isinstance(i, str) or not 1 <= len(i) <= 100 for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('Invalid session request ledger')
        Model.restore(self.graph, json.dumps(value['state']))
        return copy.deepcopy(value)

    def snapshot(self):
        with self.lock:
            result = copy.deepcopy(self.record)
            model = Model.restore(self.graph, json.dumps(result['state']))
            result['state'] = model.state
            details = {}
            for key, node in model.nodes.items():
                level = model.state['ranks'][key] + 1
                reason = None
                cost = None
                if level > len(node['ranks']):
                    reason = 'MAX_RANK'
                elif model.state['active']:
                    reason = 'BUSY'
                else:
                    rank = model.rank_spec(key, level)
                    cost = rank['growth_cost']
                    reason = model.mapping_gate(key)
                    if not reason and any(model.state['ranks'][r['node']] < r['rank'] for r in rank['requires']):
                        reason = 'PREREQUISITE'
                    if not reason and model.state['growth_points'] < cost:
                        reason = 'POINTS'
                details[key] = {'availability': model.availability(key), 'reason': model.gate(key),
                                'learnable': reason is None, 'learn_reason': reason,
                                'next_growth_cost': cost}
            result['nodes'] = details
            result['notice'] = self.notice
            return result

    def bootstrap(self):
        with self.lock:
            return {'graph': self.graph, 'session': self.snapshot(),
                    'lineage_catalog': self.current_catalog(), 'lineage_rules': self.catalog['rules'],
                    'decisions': self.decisions, 'version': __version__}

    def write_record(self, candidate):
        raw = json.dumps(candidate, ensure_ascii=False, indent=2)
        if len(raw.encode('utf-8')) > MAX_BODY - 4096:
            raise ValueError('Local history is full. Export the save, then begin a fresh incarnation.')
        temporary = self.path.with_suffix('.tmp.json')
        with temporary.open('w', encoding='utf-8') as handle:
            handle.write(raw + '\n')
            handle.flush()
            os.fsync(handle.fileno())
        if self.path.exists():
            # Startup may have recovered from a damaged primary. Rotate the
            # validated record, never the untrusted bytes still at that path.
            backup = self.path.with_suffix('.bak.json')
            backup_temporary = self.path.with_suffix('.bak.tmp.json')
            with backup_temporary.open('w', encoding='utf-8') as handle:
                handle.write(json.dumps(self.record, ensure_ascii=False, indent=2) + '\n')
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(backup_temporary, backup)
        os.replace(temporary, self.path)

    def commit(self, payload, operation):
        with self.lock:
            if type(payload.get('revision')) is not int or payload['revision'] != self.record['revision']:
                raise Conflict('This incarnation changed. Review the refreshed state and try the intended action again.')
            request = bounded_string(payload.get('request_id'), 'request_id')
            if request in self.record['request_ids']:
                return {'session': self.snapshot(), 'result': 'DUPLICATE'}
            candidate = copy.deepcopy(self.record)
            model = Model.restore(self.graph, json.dumps(candidate['state']))
            result, candidate, catalog = operation(model, candidate)
            candidate['revision'] = self.record['revision'] + 1
            candidate['request_ids'].append(request)
            if len(candidate['request_ids']) > 5000:
                raise ValueError('Request history is full. Export this save before starting another incarnation.')
            self.validate_record(candidate)
            self.write_record(candidate)
            self.record = candidate
            response = {'session': self.snapshot(), 'result': result}
            if catalog is not None:
                response['lineage_catalog'] = catalog
            return response

    def action(self, payload):
        action = bounded_string(payload.get('action'), 'action', 30)

        def operation(model, candidate):
            request = payload['request_id']
            catalog = None
            if action in ('learn', 'activate', 'respec'):
                key = payload.get('node')
                if key not in model.nodes:
                    raise ValueError('Choose a known skill node')
                if action == 'respec':
                    cascade = payload.get('cascade', False)
                    if type(cascade) is not bool:
                        raise ValueError('cascade must be true or false')
                    result = model.respec(key, request, cascade)
                else:
                    result = getattr(model, action)(key, request)
                if result not in SUCCESS:
                    raise ValueError(result)
            elif action == 'advance':
                ticks = payload.get('ticks', 1)
                if type(ticks) is not int or not 1 <= ticks <= 100:
                    raise ValueError('Advance between 1 and 100 ticks at a time')
                model.advance(ticks)
                result = 'ADVANCED'
            elif action == 'set_axis':
                model.set_axis(payload.get('axis'), payload.get('access'))
                result = 'UPDATED'
            elif action == 'set_lamp':
                if type(payload.get('equipped')) is not bool:
                    raise ValueError('equipped must be true or false')
                model.set_equipment(['lamp'] if payload['equipped'] else [])
                result = 'UPDATED'
            elif action == 'restore_resources':
                model.state['resources'] = copy.deepcopy(self.graph['scenario']['resources'])
                result = 'RESOURCES_RESTORED'
            elif action == 'reset':
                model = Model(self.graph)
                candidate['last_lineage'] = None
                candidate['lineage_registry'] = []
                catalog = copy.deepcopy(self.catalog)
                # A new incarnation begins a new idempotency epoch; the outer
                # revision continues increasing to reject stale browser actions.
                candidate['request_ids'] = []
                result = 'RESET'
            else:
                raise ValueError('Unknown action')
            candidate['state'] = model.state
            return result, candidate, catalog

        return self.commit(payload, operation)

    def preview_lineage(self, payload):
        with self.lock:
            return {'lineage': generate_lineage(self.current_catalog(), payload.get('parent_a'), payload.get('parent_b'), payload.get('seed'))}

    def install_lineage(self, payload, register=False):
        def operation(model, candidate):
            lineage = self.recompute_lineage(payload.get('lineage'))
            if register:
                if lineage['id'] in {p['id'] for p in self.current_catalog()['profiles']}:
                    raise ValueError('This offspring is already available as a parent')
                catalog = extend_catalog(self.current_catalog(), lineage)
                candidate['lineage_registry'].append(lineage)
                return 'PARENT_REGISTERED', candidate, catalog
            if model.state['active']:
                raise ValueError('Finish or interrupt the active action before changing incarnation')
            model = Model(self.graph)
            model.state['axis_access'] = {axis: 'unavailable' for axis in AXES}
            model.state['equipment'] = []
            candidate['state'] = model.state
            candidate['last_lineage'] = lineage
            return 'LINEAGE_APPLIED', candidate, None

        return self.commit(payload, operation)

    def export(self):
        with self.lock:
            return {'format': 'star-weaver-save', 'version': 1, 'session': copy.deepcopy(self.record)}

    def import_save(self, payload):
        saved = payload.get('save')
        if not isinstance(saved, dict) or set(saved) != {'format', 'version', 'session'} or saved['format'] != 'star-weaver-save' or type(saved['version']) is not int or saved['version'] != 1:
            raise ValueError('Choose a Star Weaver version-1 save file')
        imported = self.validate_record(saved['session'])
        # Import restores model receipts but begins a bounded session-request
        # epoch. Monotonic revisions still reject old browser requests.
        def operation(model, candidate):
            imported['request_ids'] = []
            return 'IMPORTED', imported, self.current_catalog(imported['lineage_registry'])
        return self.commit(payload, operation)


class WorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store):
        super().__init__(address, Handler)
        self.store = store


class Handler(BaseHTTPRequestHandler):
    server_version = 'StarWeaver/' + __version__

    def log_message(self, fmt, *args):
        # Deliberately exclude request bodies and save data from logs.
        print(f'{self.address_string()} {fmt % args}', flush=True)

    def send_bytes(self, status, data, content_type, attachment=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if attachment:
            self.send_header('Content-Disposition', f'attachment; filename="{attachment}"')
        self.end_headers()
        self.wfile.write(data)

    def json(self, status, value, attachment=None):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8', attachment)

    def trusted_request(self):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            self.json(403, {'error': 'Use the local workbench address'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{host}' for host in hosts}:
            self.json(403, {'error': 'Only the local workbench can change this session'})
            return False
        return True

    def do_GET(self):
        if not self.trusted_request():
            return
        path = unquote(urlsplit(self.path).path)
        if path == '/api/health':
            self.json(200, {'status': 'ok', 'version': __version__})
        elif path == '/api/bootstrap':
            self.json(200, self.server.store.bootstrap())
        elif path == '/api/export':
            self.json(200, self.server.store.export(), 'star-weaver-save.json')
        elif path.startswith('/api/'):
            self.json(404, {'error': 'Unknown endpoint'})
        else:
            target = (ROOT / 'web' / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
            if not target.is_relative_to((ROOT / 'web').resolve()) or not target.is_file():
                self.json(404, {'error': 'File not found'})
                return
            mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            if target.suffix in ('.js', '.css', '.html', '.svg'):
                mime = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.svg': 'image/svg+xml'}[target.suffix]
            self.send_bytes(200, target.read_bytes(), mime + '; charset=utf-8')

    def do_POST(self):
        if not self.trusted_request():
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                self.json(413, {'error': 'JSON request must be between 1 byte and 512 KiB'})
                return
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                self.json(415, {'error': 'Send application/json'})
                return
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(payload, dict):
                raise ValueError('Send a JSON object')
            store = self.server.store
            path = urlsplit(self.path).path
            if path == '/api/action':
                result = store.action(payload)
            elif path == '/api/lineage':
                result = store.preview_lineage(payload)
            elif path == '/api/register-lineage':
                result = store.install_lineage(payload, register=True)
            elif path == '/api/apply-lineage':
                result = store.install_lineage(payload)
            elif path == '/api/import':
                result = store.import_save(payload)
            else:
                self.json(404, {'error': 'Unknown endpoint'})
                return
            self.json(200, result)
        except Conflict as error:
            self.json(409, {'error': str(error), 'session': self.server.store.snapshot()})
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
            self.json(400, {'error': 'Invalid input: ' + str(error)})
        except OSError:
            self.json(500, {'error': 'The local save could not be written. The previous state is preserved.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--state-dir', type=Path, default=ROOT / 'runtime')
    parser.add_argument('--open', action='store_true', help='Open the local workbench in the default browser')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    store = SessionStore(args.state_dir)
    server = WorkbenchServer(('127.0.0.1', args.port), store)
    print(f'Star Weaver {__version__} — http://127.0.0.1:{server.server_port}', flush=True)
    if args.open:
        webbrowser.open(f'http://127.0.0.1:{server.server_port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
