"""Approved baseline acceptance checks, exercising the actual application engine."""
import copy
import json
import unittest
from pathlib import Path
from starweaver.engine import AXES, RESOURCES, Model, compile_graph

HERE = Path(__file__).resolve().parent
BASE = json.loads((HERE.parent / 'data' / 'star-weaver.fixture.json').read_text(encoding='utf-8'))


def node(data, key):
    return next(item for item in data['nodes'] if item['id'] == key)


def learned_model(data=None):
    model = Model(data or BASE)
    for key in ('M0', 'T0', 'A1', 'T1', 'H1'):
        assert model.learn(key, 'learn-' + key) == 'LEARNED'
    return model


def composition_variant(first, second):
    data = copy.deepcopy(BASE)
    comp = node(data, 'H1')
    inputs = [node(data, first), node(data, second)]
    comp['mapping']['axis_requires'] = sorted({axis for item in inputs for axis in item['mapping']['axis_requires']})
    rank = comp['ranks'][0]
    rank['requires'] = [{'node': item['id'], 'rank': 1} for item in inputs]
    rank['activation']['cost'] = {r: sum(item['ranks'][0]['activation']['cost'][r] for item in inputs) for r in RESOURCES}
    rank['activation']['equipment'] = sorted({e for item in inputs for e in item['ranks'][0]['activation']['equipment']})
    for port, item in zip(comp['recipe']['inputs'], inputs):
        port['node'] = item['id']
        port['capability'] = item['ranks'][0]['activation']['output']
    return data


class Acceptance(unittest.TestCase):
    def test_01_ordinary_magic_and_technology_need_neither_axis(self):
        model = Model(BASE)
        for axis in AXES:
            model.set_axis(axis, 'unavailable')
        for key in ('M0', 'T0'):
            self.assertEqual(model.learn(key, 'learn-' + key), 'LEARNED')
            self.assertEqual(model.activate(key, 'use-' + key), 'ACTIVE')
            model.advance(2)
        self.assertEqual(len(model.state['outputs']), 2)
        self.assertEqual(model.state['ranks']['A1'], 0)
        self.assertEqual(model.state['ranks']['T1'], 0)
        self.assertEqual(set(model.state['axis_access'].values()), {'unavailable'})

    def test_02_independent_axis_progression_both_directions(self):
        for available, blocked, root, expression, other_root, other_expression in [
                ('Affinity', 'Techfinity', 'M0', 'A1', 'T0', 'T1'),
                ('Techfinity', 'Affinity', 'T0', 'T1', 'M0', 'A1')]:
            model = Model(BASE)
            model.set_axis(blocked, 'unavailable')
            self.assertEqual(model.learn(root, 'root'), 'LEARNED')
            self.assertEqual(model.learn(expression, 'expression'), 'LEARNED')
            self.assertEqual(model.learn(other_root, 'other-root'), 'LEARNED')
            self.assertEqual(model.learn(other_expression, 'other'), 'AXIS_UNAVAILABLE')
            self.assertEqual(model.state['ranks'][other_expression], 0)
            self.assertEqual(model.state['axis_access'][available], 'available')

    def test_03_hybrid_requires_both_inputs_no_automatic_unlock(self):
        model = Model(BASE)
        for key in ('M0', 'A1', 'T0'):
            model.learn(key, 'learn-' + key)
        before = model.save()
        self.assertEqual(model.learn('H1', 'early'), 'PREREQUISITE')
        self.assertEqual(model.save(), before)
        model.learn('T1', 'learn-T1')
        self.assertEqual(model.state['ranks']['H1'], 0)
        self.assertEqual(model.learn('H1', 'learn-H1'), 'LEARNED')
        self.assertIsNone(model.state['active'])
        self.assertEqual(model.state['outputs'], [])

    def test_04_learning_budget_and_retries_are_atomic(self):
        model = learned_model()
        self.assertEqual(model.state['growth_points'], 0)
        before = model.save()
        self.assertEqual(model.learn('H1', 'learn-H1'), 'DUPLICATE')
        self.assertEqual(model.save(), before)
        data = copy.deepcopy(BASE)
        data['scenario']['growth_points'] = 0
        model = Model(data)
        before = model.save()
        self.assertEqual(model.learn('M0', 'learn'), 'POINTS')
        self.assertEqual(model.save(), before)

    def test_05_success_charges_once_emits_one_output_then_recovers(self):
        model = learned_model()
        self.assertEqual(model.activate('H1', 'beacon'), 'ACTIVE')
        self.assertEqual(model.state['resources'], {'focus': 2, 'charge': 2})
        model.advance()
        self.assertEqual(model.state['outputs'], [])
        model.advance()
        self.assertEqual([out['output'] for out in model.state['outputs']], ['encoded_light_beacon'])
        self.assertEqual(model.availability('H1'), 'RECOVERING')
        model.advance(2)
        self.assertEqual(model.availability('H1'), 'READY')

    def test_06_insufficient_one_resource_spends_neither(self):
        model = learned_model()
        model.state['resources']['charge'] = 0
        before = model.save()
        self.assertEqual(model.activate('H1', 'dry'), 'DEPLETED')
        self.assertEqual(model.save(), before)

    def test_07_input_loss_aborts_no_output_or_resource_refund(self):
        model = learned_model()
        model.activate('H1', 'beacon')
        model.advance()
        ranks = copy.deepcopy(model.state['ranks'])
        model.set_axis('Techfinity', 'unavailable')
        self.assertIsNone(model.state['active'])
        self.assertEqual(model.state['outputs'], [])
        self.assertEqual(model.state['resources'], {'focus': 2, 'charge': 2})
        self.assertEqual(model.state['ranks'], ranks)
        self.assertEqual(model.availability('H1'), 'SUSPENDED')
        model.set_axis('Techfinity', 'available')
        self.assertEqual(model.availability('H1'), 'RECOVERING')
        model.advance(2)
        self.assertEqual(model.availability('H1'), 'READY')
        self.assertIsNone(model.state['active'])

    def test_08_hardware_loss_blocks_recipe_but_leaves_magic_usable(self):
        model = learned_model()
        model.set_equipment([])
        self.assertEqual(model.availability('H1'), 'SUSPENDED')
        self.assertEqual(model.availability('T1'), 'SUSPENDED')
        self.assertEqual(model.availability('A1'), 'READY')
        self.assertEqual(model.state['ranks']['T1'], 1)
        model.set_equipment(['lamp'])
        self.assertEqual(model.availability('H1'), 'READY')
        model.activate('H1', 'beacon')
        model.set_equipment([])
        self.assertEqual(model.state['events'][-1]['event'], 'ABORTED')

    def test_09_unknown_access_is_not_known_absence_or_permission(self):
        model = Model(BASE)
        model.set_axis('Affinity', 'unknown')
        self.assertEqual(model.learn('M0', 'root'), 'LEARNED')
        self.assertEqual(model.learn('A1', 'expression'), 'AXIS_UNKNOWN')
        self.assertEqual(model.state['ranks']['A1'], 0)

    def test_10_unresolved_mapping_remains_null_and_nonexecutable(self):
        data = copy.deepcopy(BASE)
        for key in ('A1', 'H1'):
            node(data, key)['mapping'] = {'status': 'UNRESOLVED', 'axis_requires': None,
                                          'question': 'Which system, if any, does this action require?'}
        model = Model(data)
        model.learn('M0', 'root')
        self.assertEqual(model.learn('A1', 'expression'), 'UNRESOLVED')
        self.assertEqual(model.learn('H1', 'hybrid'), 'UNRESOLVED')
        self.assertEqual(model.activate('M0', 'ordinary'), 'ACTIVE')

    def test_11_ordinary_hybrid_has_no_system_requirements(self):
        data = composition_variant('M0', 'T0')
        data['scenario']['axis_access'] = {axis: 'unavailable' for axis in AXES}
        model = Model(data)
        for key in ('M0', 'T0', 'H1'):
            self.assertEqual(model.learn(key, 'learn-' + key), 'LEARNED')
        self.assertEqual(model.activate('H1', 'ordinary-hybrid'), 'ACTIVE')
        self.assertEqual(node(data, 'H1')['mapping']['axis_requires'], [])

    def test_12_single_axis_hybrids_require_only_the_explicit_axis(self):
        for first, second, required, absent in [('A1', 'T0', 'Affinity', 'Techfinity'),
                                                ('M0', 'T1', 'Techfinity', 'Affinity')]:
            data = composition_variant(first, second)
            data['scenario']['axis_access'][absent] = 'unavailable'
            model = Model(data)
            for key in ('M0', 'T0', first, second, 'H1'):
                if model.state['ranks'][key] == 0:
                    self.assertEqual(model.learn(key, 'learn-' + key), 'LEARNED')
            self.assertEqual(node(data, 'H1')['mapping']['axis_requires'], [required])
            self.assertEqual(model.activate('H1', 'mixed'), 'ACTIVE')

    def test_13_provisional_family_labels_change_no_runtime_behavior(self):
        data = copy.deepcopy(BASE)
        data['family_labels'] = [{'id': 'candidate_signal', 'label': 'Candidate signal family',
                                 'status': 'PROVISIONAL', 'members': ['M0', 'H1']}]
        left, right = learned_model(), learned_model(data)
        left.activate('H1', 'beacon')
        right.activate('H1', 'beacon')
        left.advance(4)
        right.advance(4)
        self.assertEqual(left.save(), right.save())

    def test_14_rejects_finity_as_system_or_progression_root(self):
        data = copy.deepcopy(BASE)
        node(data, 'H1')['mapping']['axis_requires'].append('Finity')
        with self.assertRaises(ValueError):
            compile_graph(data)
        data = copy.deepcopy(BASE)
        node(data, 'M0')['label'] = 'Finity'
        with self.assertRaises(ValueError):
            compile_graph(data)

    def test_15_rejects_cycles_and_missing_prerequisites(self):
        for target in ('A1', 'missing'):
            data = copy.deepcopy(BASE)
            node(data, 'M0')['ranks'][0]['requires'] = [{'node': target, 'rank': 1}]
            with self.assertRaises(ValueError):
                compile_graph(data)

    def test_16_rejects_mismatched_capability_port(self):
        data = copy.deepcopy(BASE)
        node(data, 'H1')['recipe']['inputs'][0]['capability'] = 'unearned_capability'
        with self.assertRaises(ValueError):
            compile_graph(data)

    def test_17_rejects_hidden_axis_inheritance_and_free_conversion(self):
        for field in ('axis', 'cost'):
            data = copy.deepcopy(BASE)
            if field == 'axis':
                node(data, 'H1')['mapping']['axis_requires'] = ['Affinity']
            else:
                node(data, 'H1')['ranks'][0]['activation']['cost']['charge'] = 0
            with self.assertRaises(ValueError):
                compile_graph(data)

    def test_18_shared_input_recovery_cannot_be_bypassed(self):
        model = learned_model()
        model.activate('A1', 'light')
        model.advance()
        before = model.save()
        self.assertEqual(model.activate('H1', 'early-beacon'), 'RECOVERING')
        self.assertEqual(model.save(), before)
        model.advance()
        self.assertEqual(model.activate('H1', 'beacon'), 'ACTIVE')
        model.advance(2)
        self.assertEqual(model.availability('A1'), 'RECOVERING')
        self.assertEqual(model.availability('T1'), 'RECOVERING')

    def test_19_respec_requires_cascade_and_refunds_exact_spend(self):
        model = learned_model()
        before = model.save()
        self.assertEqual(model.respec('M0', 'respec'), 'DEPENDENTS')
        self.assertEqual(model.save(), before)
        self.assertEqual(model.respec('M0', 'respec', cascade=True), 'REFUNDED')
        self.assertEqual(model.state['growth_points'], 4)
        self.assertEqual(model.state['ranks'], {'M0': 0, 'T0': 1, 'A1': 0, 'T1': 1, 'H1': 0})
        self.assertEqual(model.state['resources'], {'focus': 3, 'charge': 3})
        self.assertEqual(model.respec('M0', 'respec', cascade=True), 'DUPLICATE')

    def test_20_save_resume_mid_action_and_replay_charge_once(self):
        model = learned_model()
        model.activate('H1', 'beacon')
        model.advance()
        resumed = Model.restore(BASE, model.save())
        before = resumed.save()
        self.assertEqual(resumed.activate('H1', 'beacon'), 'DUPLICATE')
        self.assertEqual(resumed.save(), before)
        model.advance(3)
        resumed.advance(3)
        self.assertEqual(model.save(), resumed.save())
        self.assertEqual(len(resumed.state['outputs']), 1)

    def test_21_incompatible_save_is_rejected_without_mutation(self):
        model = learned_model()
        saved = model.save()
        data = copy.deepcopy(BASE)
        node(data, 'H1')['ranks'][0]['activation']['duration_ticks'] = 3
        with self.assertRaises(ValueError):
            Model.restore(data, saved)
        bad_save = json.loads(saved)
        bad_save['schema_version'] = 'future'
        with self.assertRaises(ValueError):
            Model.restore(BASE, json.dumps(bad_save))
        self.assertEqual(model.save(), saved)

    def test_22_higher_rank_replaces_action_parameters_and_pins_recipe_inputs(self):
        data = copy.deepcopy(BASE)
        data['scenario']['growth_points'] = 8
        rank = copy.deepcopy(node(data, 'A1')['ranks'][0])
        rank.update(rank=2, growth_cost=2)
        rank['activation']['cost']['focus'] = 2
        rank['activation']['output'] = 'guided_light_rank_2'
        node(data, 'A1')['ranks'].append(rank)
        model = learned_model(data)
        self.assertEqual(model.learn('A1', 'rank-2'), 'LEARNED')
        self.assertEqual(model.rank_spec('A1')['activation']['cost']['focus'], 2)
        self.assertEqual(model.activate('H1', 'beacon'), 'ACTIVE')
        self.assertEqual(model.state['resources']['focus'], 2)
        self.assertEqual(model.state['growth_points'], 0)

    def test_23_proposal_permission_is_explicit_and_never_promotes(self):
        data = copy.deepcopy(BASE)
        data['scenario']['allowed_proposal'] = 'some-other-proposal'
        with self.assertRaises(ValueError):
            Model(data)
        model = learned_model()
        model.activate('H1', 'beacon')
        model.advance(4)
        self.assertEqual(model.data['adoption'], 'PROPOSED')
        self.assertTrue(all(n['adoption'] == 'PROPOSED' for n in model.data['nodes']))
        self.assertEqual(model.data['context_doubt']['Finity']['runtime_role'], 'none')

    def test_24_respec_cannot_reset_recovery_or_refund_activation_resources(self):
        model = learned_model()
        model.activate('H1', 'beacon')
        self.assertEqual(model.respec('H1', 'during-action'), 'BUSY')
        model.advance(2)
        self.assertEqual(model.respec('H1', 'respec'), 'REFUNDED')
        self.assertEqual(model.learn('H1', 'relearn'), 'LEARNED')
        self.assertEqual(model.availability('H1'), 'RECOVERING')
        self.assertEqual(model.state['resources'], {'focus': 2, 'charge': 2})

    def test_25_unearned_rank_requirements_do_not_trigger_respec(self):
        data = copy.deepcopy(BASE)
        rank = copy.deepcopy(node(data, 'A1')['ranks'][0])
        rank.update(rank=2, growth_cost=2)
        rank['requires'].append({'node': 'T0', 'rank': 1})
        node(data, 'A1')['ranks'].append(rank)
        model = Model(data)
        for key in ('M0', 'T0', 'A1'):
            self.assertEqual(model.learn(key, 'learn-' + key), 'LEARNED')
        self.assertEqual(model.respec('T0', 'respec'), 'REFUNDED')
        self.assertEqual(model.state['ranks']['A1'], 1)
        self.assertEqual(model.state['growth_points'], 4)
