import copy
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from server import Conflict, SessionStore, WorkbenchServer
from starweaver.engine import Model


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='star-weaver-test-')
        self.directory = Path(self.temporary.name)
        self.store = SessionStore(self.directory)

    def tearDown(self):
        self.temporary.cleanup()

    def action(self, action, **kwargs):
        return self.store.action({'revision': self.store.record['revision'], 'request_id': f'req-{self.store.record["revision"]}',
                                  'action': action, **kwargs})

    def lineage(self):
        a, b = [p['id'] for p in self.store.catalog['profiles'][:2]]
        return self.store.preview_lineage({'parent_a': a, 'parent_b': b, 'seed': 'test-seed'})['lineage']

    def test_learning_persists_across_service_restart(self):
        self.action('learn', node='M0')
        restored = SessionStore(self.directory)
        self.assertEqual(restored.record['state']['ranks']['M0'], 1)
        self.assertEqual(restored.record['revision'], 1)

    def test_stale_action_and_invalid_action_preserve_state(self):
        self.action('learn', node='M0')
        before = self.store.export()
        with self.assertRaises(Conflict):
            self.store.action({'revision': 0, 'request_id': 'stale', 'action': 'learn', 'node': 'T0'})
        with self.assertRaises(ValueError):
            self.action('advance', ticks=True)
        self.assertEqual(self.store.export(), before)

    def test_duplicate_request_has_no_second_mutation(self):
        self.action('learn', node='M0')
        before = self.store.export()
        response = self.store.action({'revision': 1, 'request_id': 'req-0', 'action': 'learn', 'node': 'T0'})
        self.assertEqual(response['result'], 'DUPLICATE')
        self.assertEqual(self.store.export(), before)

    def test_disk_failure_does_not_install_candidate_state(self):
        before = self.store.export()
        with patch.object(self.store, 'write_record', side_effect=OSError('synthetic write failure')):
            with self.assertRaises(OSError):
                self.action('learn', node='M0')
        self.assertEqual(self.store.export(), before)

    def test_invalid_save_rejected_before_replacement(self):
        self.action('learn', node='M0')
        for tamper in ('budget', 'digest', 'clock', 'access', 'dangling', 'active'):
            saved = copy.deepcopy(self.store.export())
            state = saved['session']['state']
            if tamper == 'budget':
                state['growth_points'] = 9999
            elif tamper == 'digest':
                state['mechanics_digest'] = 'old'
            elif tamper == 'clock':
                state['tick'] = -1
            elif tamper == 'access':
                state['axis_access']['Finity'] = 'available'
            elif tamper == 'dangling':
                state['ranks']['H1'] = 1
                state['spent']['H1'] = [2]
                state['growth_points'] -= 2
            else:
                state['active'] = {'node': 'M0', 'rank': 1, 'ends_at': 9999, 'request_id': 'fake'}
            before = self.store.export()
            with self.subTest(tamper=tamper), self.assertRaises((ValueError, KeyError, TypeError)):
                self.store.import_save({'revision': self.store.record['revision'], 'request_id': 'invalid', 'save': saved})
            self.assertEqual(self.store.export(), before)

    def test_valid_save_roundtrip_resumes_active_action_once(self):
        self.action('learn', node='M0')
        self.action('activate', node='M0')
        saved = self.store.export()
        self.action('advance')
        self.store.import_save({'revision': self.store.record['revision'], 'request_id': 'restore', 'save': saved})
        self.action('advance')
        self.assertEqual(len(self.store.record['state']['outputs']), 1)
        self.assertEqual(self.store.record['state']['resources']['focus'], 2)

    def test_lineage_preview_does_not_mutate_incarnation(self):
        before = self.store.export()
        lineage = self.lineage()
        self.assertEqual(lineage['learned_skills'], [])
        self.assertEqual(self.store.export(), before)

    def test_lineage_application_starts_untrained_unequipped_without_active_access(self):
        lineage = self.lineage()
        self.store.install_lineage({'revision': 0, 'request_id': 'apply', 'lineage': lineage})
        state = self.store.record['state']
        self.assertEqual(set(state['ranks'].values()), {0})
        self.assertEqual(set(state['axis_access'].values()), {'unavailable'})
        self.assertEqual(state['equipment'], [])
        self.assertEqual(self.store.record['last_lineage']['id'], lineage['id'])
        self.action('learn', node='M0')
        with self.assertRaises(ValueError):
            self.action('learn', node='A1')

    def test_tampered_lineage_is_not_trusted(self):
        lineage = self.lineage()
        lineage['axis_potential']['Affinity'] = not lineage['axis_potential']['Affinity']
        before = self.store.export()
        with self.assertRaises(ValueError):
            self.store.install_lineage({'revision': 0, 'request_id': 'apply', 'lineage': lineage})
        self.assertEqual(self.store.export(), before)

    def test_multigeneration_parent_registry_survives_export_and_restart(self):
        first = self.lineage()
        self.store.install_lineage({'revision': 0, 'request_id': 'register', 'lineage': first}, register=True)
        second = self.store.preview_lineage({'parent_a': first['id'], 'parent_b': self.store.catalog['profiles'][2]['id'], 'seed': 'second'})['lineage']
        self.assertGreater(second['generation'], first['generation'])
        self.store.install_lineage({'revision': 1, 'request_id': 'register-2', 'lineage': second}, register=True)
        restored = SessionStore(self.directory)
        self.assertIn(second['id'], {p['id'] for p in restored.current_catalog()['profiles']})
        self.assertEqual(restored.export(), self.store.export())

    def test_damaged_save_is_preserved_and_last_good_backup_recovers(self):
        self.action('learn', node='M0')
        self.action('learn', node='T0')
        self.store.path.write_text('damaged save', encoding='utf-8')
        recovered = SessionStore(self.directory)
        self.assertEqual(recovered.record['state']['ranks']['M0'], 1)
        self.assertEqual(recovered.record['state']['ranks']['T0'], 0)
        self.assertTrue(recovered.path.with_suffix('.corrupt.json').exists())
        self.assertIn('Recovered', recovered.notice)

    def test_recovered_save_remains_the_backup_after_next_write(self):
        self.action('learn', node='M0')
        self.action('learn', node='T0')
        self.store.path.write_text('damaged primary', encoding='utf-8')
        self.store = SessionStore(self.directory)
        self.action('learn', node='T0')
        self.store.path.write_text('damaged again', encoding='utf-8')
        recovered_again = SessionStore(self.directory)
        self.assertEqual(recovered_again.record['state']['ranks']['M0'], 1)
        self.assertEqual(recovered_again.record['state']['ranks']['T0'], 0)

    def test_reset_recovers_from_full_request_history(self):
        self.store.record['request_ids'] = [f'old-{i}' for i in range(5000)]
        result = self.action('reset')
        self.assertEqual(result['result'], 'RESET')
        self.assertEqual(self.store.record['revision'], 1)
        self.assertEqual(self.store.record['request_ids'], ['req-0'])

    def test_full_history_export_remains_importable_after_reset(self):
        self.store.record['request_ids'] = [f'old-{i}' for i in range(5000)]
        saved = self.store.export()
        self.action('reset')
        result = self.store.import_save({'revision': 1, 'request_id': 'import-full', 'save': saved})
        self.assertEqual(result['result'], 'IMPORTED')
        self.assertEqual(self.store.record['revision'], 2)
        self.assertEqual(self.store.record['request_ids'], ['import-full'])

    def test_reset_clears_registered_parents_and_returns_base_catalog(self):
        first = self.lineage()
        self.store.install_lineage({'revision': 0, 'request_id': 'register', 'lineage': first}, register=True)
        result = self.action('reset')
        self.assertEqual(self.store.record['lineage_registry'], [])
        self.assertNotIn(first['id'], {p['id'] for p in result['lineage_catalog']['profiles']})


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='star-weaver-http-test-')
        self.store = SessionStore(Path(self.temporary.name))
        self.server = WorkbenchServer(('127.0.0.1', 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temporary.cleanup()

    def request(self, method, path, value=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        body = None if value is None else json.dumps(value)
        connection.request(method, path, body=body, headers={'Content-Type': 'application/json', **(headers or {})})
        response = connection.getresponse()
        raw = response.read()
        result = response.status, dict(response.getheaders()), raw
        connection.close()
        return result

    def test_bootstrap_and_real_action_stale_revision_flow(self):
        status, headers, raw = self.request('GET', '/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn('lineage_catalog', json.loads(raw))
        payload = {'revision': 0, 'request_id': 'http-learn', 'action': 'learn', 'node': 'M0'}
        status, _, raw = self.request('POST', '/api/action', payload)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['session']['state']['ranks']['M0'], 1)
        status, _, raw = self.request('POST', '/api/action', {**payload, 'node': 'T0', 'request_id': 'stale'})
        self.assertEqual(status, 409)
        self.assertEqual(json.loads(raw)['session']['revision'], 1)

    def test_origin_host_and_path_boundaries(self):
        payload = {'revision': 0, 'request_id': 'cross-origin', 'action': 'reset'}
        self.assertEqual(self.request('POST', '/api/action', payload, {'Origin': 'https://example.invalid'})[0], 403)
        self.assertEqual(self.request('GET', '/api/bootstrap', headers={'Host': 'remote.invalid'})[0], 403)
        self.assertEqual(self.request('GET', '/%2e%2e/server.py')[0], 404)
        self.assertEqual(self.store.record['revision'], 0)

    def test_invalid_body_returns_actionable_error_and_keeps_state(self):
        status, _, raw = self.request('POST', '/api/action', {'revision': 0, 'request_id': 'invalid', 'action': 'learn', 'node': 'missing'})
        self.assertEqual(status, 400)
        self.assertIn('known skill', json.loads(raw)['error'])
        self.assertEqual(self.store.record['revision'], 0)

    def test_manifestation_endpoints(self):
        status, _, raw = self.request('GET', '/api/manifestation')
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertEqual(data['schema_version'], '0.3.1')
        self.assertIn('H1', data['manifestations'])

        compile_payload = {'skill_id': 'H1', 'equipment': ['lamp'], 'mentorship_tradition': 'Gorgon Flow Arts Lineage'}
        status, _, raw = self.request('POST', '/api/compile-manifestation', compile_payload)
        self.assertEqual(status, 200)
        frame = json.loads(raw)
        self.assertEqual(frame['skill_id'], 'H1')
        self.assertEqual(frame['status'], 'ACTIVE')
        self.assertEqual(frame['material_channel'], 'Assorcery')
        self.assertIn('Gorgon Flow Arts Lineage', frame['choreography']['flow_style'])


if __name__ == '__main__':
    unittest.main()
