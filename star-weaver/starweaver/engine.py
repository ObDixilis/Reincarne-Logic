"""Deterministic skill progression engine for the approved SW-SKILL-001 baseline."""
import copy
import hashlib
import json

AXES = {'Affinity', 'Techfinity'}
RESOURCES = ('focus', 'charge')


def compile_graph(data):
    """Check graph semantics alongside the packaged JSON Schema contract."""
    if data['schema_version'] != '0.1.0' or data['adoption'] != 'PROPOSED':
        raise ValueError('Unsupported schema or adoption state')
    if set(data['canonical_systems']) != AXES:
        raise ValueError('Only the two independent system references are admitted')
    if data['context_doubt']['Finity']['runtime_role'] != 'none':
        raise ValueError('Finity has no runtime role')
    if (data['scenario']['mode'] != 'proposal_playtest'
            or data['scenario']['allowed_proposal'] != data['proposal_id']):
        raise ValueError('Proposal playtest must explicitly select this proposal')
    nodes = {node['id']: node for node in data['nodes']}
    if len(nodes) != len(data['nodes']):
        raise ValueError('Duplicate node ID')
    dependencies = {key: set() for key in nodes}
    for key, node in nodes.items():
        if key.casefold() == 'finity' or node['label'].strip().casefold() == 'finity':
            raise ValueError('Finity cannot be a gameplay node')
        if node['adoption'] != 'PROPOSED':
            raise ValueError('This fixture never promotes nodes to canon')
        mapping = node['mapping']
        if mapping['status'] == 'UNRESOLVED':
            if mapping['axis_requires'] is not None or not mapping['question']:
                raise ValueError('Unknown mapping must remain null with a question')
        elif mapping['status'] == 'PROPOSED':
            if (not isinstance(mapping['axis_requires'], list)
                    or not set(mapping['axis_requires']) <= AXES
                    or len(set(mapping['axis_requires'])) != len(mapping['axis_requires'])):
                raise ValueError('Invalid system requirements')
        else:
            raise ValueError('Invalid mapping state')
        if node['kind'] == 'practice':
            if mapping['status'] != 'PROPOSED' or mapping['axis_requires'] != []:
                raise ValueError('Practice is explicitly axis-independent in this proposal')
        elif node['kind'] == 'expression':
            if mapping['status'] == 'PROPOSED' and len(mapping['axis_requires']) != 1:
                raise ValueError('An expression explicitly requires one system')
        elif node['kind'] != 'composition':
            raise ValueError('Unsupported node kind')
        if node['kind'] != 'composition' and node['recipe'] is not None:
            raise ValueError('Only a composition has input ports')
        if [rank['rank'] for rank in node['ranks']] != list(range(1, len(node['ranks']) + 1)):
            raise ValueError('Ranks must be contiguous from one')
        for rank in node['ranks']:
            if rank['growth_cost'] <= 0:
                raise ValueError('Learning must cost a positive integer')
            seen = set()
            for req in rank['requires']:
                target, level = req['node'], req['rank']
                if target not in nodes or not 1 <= level <= len(nodes[target]['ranks']):
                    raise ValueError('Missing prerequisite or invalid rank')
                if target in seen:
                    raise ValueError('Duplicate prerequisite')
                seen.add(target)
                dependencies[key].add(target)
            act = rank['activation']
            if any(act['cost'][r] < 0 for r in RESOURCES) or act['duration_ticks'] < 1 or act['recovery_ticks'] < 0:
                raise ValueError('Invalid action cost or timing')
    for key, node in nodes.items():
        if node['kind'] != 'composition':
            continue
        recipe = node['recipe']
        if (not recipe or recipe['mode'] != 'coupled' or recipe['fallback'] is not None
                or recipe['on_input_loss'] != 'abort_no_refund' or len(recipe['inputs']) < 2):
            raise ValueError('Unsupported recipe contract')
        roles, input_ids, methods, axes, unknown = set(), set(), set(), set(), False
        cost = {r: 0 for r in RESOURCES}
        equipment, duration, recovery = set(), 0, 0
        for port in recipe['inputs']:
            target, level = port['node'], port['rank']
            if target not in nodes or not 1 <= level <= len(nodes[target]['ranks']):
                raise ValueError('Unknown input node or rank')
            if port['role'] in roles or target in input_ids:
                raise ValueError('Input roles and node instances must be unique')
            roles.add(port['role'])
            input_ids.add(target)
            source = nodes[target]
            if source['kind'] == 'composition':
                raise ValueError('Version 0.1 uses flat recipes')
            action = source['ranks'][level - 1]['activation']
            if port['capability'] != action['output']:
                raise ValueError('Input capability does not match its selected rank')
            methods.update(source['methods'])
            if source['mapping']['status'] == 'UNRESOLVED':
                unknown = True
            else:
                axes.update(source['mapping']['axis_requires'])
            for resource in RESOURCES:
                cost[resource] += action['cost'][resource]
            equipment.update(action['equipment'])
            duration = max(duration, action['duration_ticks'])
            recovery = max(recovery, action['recovery_ticks'])
            dependencies[key].add(target)
        if set(node['methods']) != methods:
            raise ValueError('Composition methods must match the input union')
        if unknown:
            if node['mapping']['status'] != 'UNRESOLVED':
                raise ValueError('Unknown input mapping cannot become a known composition')
        elif node['mapping']['status'] == 'PROPOSED' and set(node['mapping']['axis_requires']) != axes:
            raise ValueError('Composition requires exactly the input system union')
        for rank in node['ranks']:
            requirements = {req['node']: req['rank'] for req in rank['requires']}
            if any(requirements.get(port['node'], 0) < port['rank'] for port in recipe['inputs']):
                raise ValueError('Every input rank must be a learning prerequisite')
            act = rank['activation']
            if act['cost'] != cost or set(act['equipment']) != equipment:
                raise ValueError('Composition cost and equipment must equal the input totals')
            if act['duration_ticks'] < duration or act['recovery_ticks'] < recovery:
                raise ValueError('Composition cannot bypass input timing')
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            raise ValueError('Cyclic progression or composition')
        if key in visited:
            return
        visiting.add(key)
        for parent in dependencies[key]:
            visit(parent)
        visiting.remove(key)
        visited.add(key)

    for key in nodes:
        visit(key)
    family_ids = set()
    for family in data['family_labels']:
        if (family['id'] in family_ids or family['id'] in nodes
                or family['id'].casefold() == 'finity'
                or family['label'].strip().casefold() == 'finity'
                or family['status'] != 'PROVISIONAL' or not set(family['members']) <= nodes.keys()):
            raise ValueError('Invalid display-only family label')
        family_ids.add(family['id'])
    return nodes, dependencies


def mechanics_digest(data):
    projection = {'schema_version': data['schema_version'], 'proposal_id': data['proposal_id'],
                  'nodes': [{key: value for key, value in node.items() if key not in ('label', 'adoption')}
                            for node in data['nodes']]}
    return hashlib.sha256(json.dumps(projection, sort_keys=True).encode()).hexdigest()


class Model:
    def __init__(self, data):
        self.data = copy.deepcopy(data)
        self.nodes, self.dependencies = compile_graph(self.data)
        scenario = self.data['scenario']
        self.state = {
            'schema_version': data['schema_version'], 'mechanics_digest': mechanics_digest(data),
            'tick': 0, 'growth_points': scenario['growth_points'],
            'resources': copy.deepcopy(scenario['resources']),
            'axis_access': copy.deepcopy(scenario['axis_access']), 'equipment': list(scenario['equipment']),
            'ranks': {key: 0 for key in self.nodes}, 'spent': {key: [] for key in self.nodes},
            'ready_at': {key: 0 for key in self.nodes}, 'active': None,
            'receipts': {}, 'outputs': [], 'events': []}

    def rank_spec(self, node, rank=None):
        level = self.state['ranks'][node] if rank is None else rank
        return self.nodes[node]['ranks'][level - 1]

    def mapping_gate(self, node):
        mapping = self.nodes[node]['mapping']
        if mapping['status'] == 'UNRESOLVED':
            return 'UNRESOLVED'
        for axis in mapping['axis_requires']:
            if self.state['axis_access'][axis] != 'available':
                return 'AXIS_' + self.state['axis_access'][axis].upper()
        return None

    def gate(self, node, rank=None):
        if self.state['ranks'][node] < (rank or 1):
            return 'NOT_LEARNED'
        reason = self.mapping_gate(node)
        if reason:
            return reason
        spec = self.rank_spec(node, rank)
        if any(self.state['ranks'][r['node']] < r['rank'] for r in spec['requires']):
            return 'PREREQUISITE'
        if not set(spec['activation']['equipment']) <= set(self.state['equipment']):
            return 'EQUIPMENT'
        if self.nodes[node]['recipe']:
            for port in self.nodes[node]['recipe']['inputs']:
                reason = self.gate(port['node'], port['rank'])
                if reason:
                    return reason
        return None

    def participants(self, node):
        recipe = self.nodes[node]['recipe']
        return [node] + ([port['node'] for port in recipe['inputs']] if recipe else [])

    def availability(self, node):
        if self.state['ranks'][node] == 0:
            return 'LOCKED'
        reason = self.gate(node)
        if reason:
            return 'UNRESOLVED' if reason == 'UNRESOLVED' else 'SUSPENDED'
        if self.state['active'] and self.state['active']['node'] == node:
            return 'ACTIVE'
        if any(self.state['ready_at'][part] > self.state['tick'] for part in self.participants(node)):
            return 'RECOVERING'
        cost = self.rank_spec(node)['activation']['cost']
        if any(self.state['resources'][r] < cost[r] for r in RESOURCES):
            return 'DEPLETED'
        return 'READY'

    def learn(self, node, request_id):
        if request_id in self.state['receipts']:
            return 'DUPLICATE'
        if self.state['active']:
            return 'BUSY'
        level = self.state['ranks'][node] + 1
        if level > len(self.nodes[node]['ranks']):
            return 'MAX_RANK'
        reason = self.mapping_gate(node)
        if reason:
            return reason
        rank = self.rank_spec(node, level)
        if any(self.state['ranks'][r['node']] < r['rank'] for r in rank['requires']):
            return 'PREREQUISITE'
        if self.state['growth_points'] < rank['growth_cost']:
            return 'POINTS'
        self.state['growth_points'] -= rank['growth_cost']
        self.state['ranks'][node] = level
        self.state['spent'][node].append(rank['growth_cost'])
        self.state['receipts'][request_id] = {'op': 'learn', 'node': node, 'rank': level}
        return 'LEARNED'

    def activate(self, node, request_id):
        if request_id in self.state['receipts']:
            return 'DUPLICATE'
        if self.state['active']:
            return 'BUSY'
        state = self.availability(node)
        if state != 'READY':
            return state
        rank = self.state['ranks'][node]
        act = self.rank_spec(node, rank)['activation']
        for resource in RESOURCES:
            self.state['resources'][resource] -= act['cost'][resource]
        self.state['active'] = {'node': node, 'rank': rank,
                                'ends_at': self.state['tick'] + act['duration_ticks'],
                                'request_id': request_id}
        self.state['receipts'][request_id] = {'op': 'activate', 'node': node, 'rank': rank}
        self.state['events'].append({'tick': self.state['tick'], 'node': node, 'event': 'ACTIVE'})
        return 'ACTIVE'

    def finish(self, event):
        active = self.state['active']
        act = self.rank_spec(active['node'], active['rank'])['activation']
        for participant in self.participants(active['node']):
            self.state['ready_at'][participant] = self.state['tick'] + act['recovery_ticks']
        if event == 'COMPLETE':
            self.state['outputs'].append({'tick': self.state['tick'], 'node': active['node'],
                                          'output': act['output'], 'request_id': active['request_id']})
        self.state['events'].append({'tick': self.state['tick'], 'node': active['node'], 'event': event})
        self.state['active'] = None

    def enforce_active_gates(self):
        active = self.state['active']
        if active and self.gate(active['node'], active['rank']):
            self.finish('ABORTED')

    def set_axis(self, axis, access):
        if axis not in AXES or access not in ('available', 'unavailable', 'unknown'):
            raise ValueError('Invalid scenario access state')
        self.state['axis_access'][axis] = access
        self.enforce_active_gates()

    def set_equipment(self, equipment):
        self.state['equipment'] = sorted(set(equipment))
        self.enforce_active_gates()

    def advance(self, ticks=1):
        if type(ticks) is not int or ticks < 0:
            raise ValueError('Ticks must be a nonnegative integer')
        for _ in range(ticks):
            self.state['tick'] += 1
            self.enforce_active_gates()
            active = self.state['active']
            if active and self.state['tick'] >= active['ends_at']:
                self.finish('COMPLETE')

    def respec(self, node, request_id, cascade=False):
        if request_id in self.state['receipts']:
            return 'DUPLICATE'
        if self.state['active']:
            return 'BUSY'
        if self.state['ranks'][node] == 0:
            return 'NOT_LEARNED'
        removal = {node}
        learned_dependencies = {
            key: {req['node'] for rank in self.nodes[key]['ranks'][:self.state['ranks'][key]]
                  for req in rank['requires']}
            for key in self.nodes}
        while True:
            added = {key for key, parents in learned_dependencies.items()
                     if self.state['ranks'][key] > 0 and parents & removal} - removal
            if not added:
                break
            removal.update(added)
        if len(removal) > 1 and not cascade:
            return 'DEPENDENTS'
        refund = sum(sum(self.state['spent'][key]) for key in removal)
        for key in removal:
            self.state['ranks'][key] = 0
            self.state['spent'][key] = []
        self.state['growth_points'] += refund
        self.state['receipts'][request_id] = {'op': 'respec', 'nodes': sorted(removal), 'refund': refund}
        return 'REFUNDED'

    def save(self):
        return json.dumps(self.state, sort_keys=True)

    @classmethod
    def restore(cls, data, saved):
        result = cls(data)
        state = json.loads(saved)
        if (state['schema_version'] != data['schema_version']
                or state['mechanics_digest'] != mechanics_digest(data)):
            raise ValueError('Save needs an explicit migration; no changes were applied')
        if set(state) != set(result.state) or set(state['ranks']) != set(result.nodes):
            raise ValueError('Incompatible save fields')
        if (type(state['growth_points']) is not int or state['growth_points'] < 0
                or any(type(state['resources'][r]) is not int or state['resources'][r] < 0 for r in RESOURCES)):
            raise ValueError('Invalid saved resource ledger')
        for key, rank in state['ranks'].items():
            if type(rank) is not int or not 0 <= rank <= len(result.nodes[key]['ranks']):
                raise ValueError('Invalid saved rank')
            if state['spent'][key] != [r['growth_cost'] for r in result.nodes[key]['ranks'][:rank]]:
                raise ValueError('Invalid saved spending ledger')
        validate_saved_state(result, state)
        result.state = state
        result.enforce_active_gates()
        return result


def validate_saved_state(model, state):
    """Validate untrusted browser saves before installing any state."""
    def integer(value, maximum=1_000_000_000):
        return type(value) is int and 0 <= value <= maximum

    keys = set(model.nodes)
    if not integer(state['tick']) or set(state['spent']) != keys or set(state['ready_at']) != keys:
        raise ValueError('Invalid saved clock or node maps')
    if set(state['axis_access']) != AXES or any(v not in ('available', 'unavailable', 'unknown') for v in state['axis_access'].values()):
        raise ValueError('Invalid system access facts')
    if (not isinstance(state['equipment'], list) or len(state['equipment']) != len(set(state['equipment']))
            or not set(state['equipment']) <= {'lamp'}):
        raise ValueError('Invalid saved equipment')
    maxima = model.data['scenario']['resources']
    if set(state['resources']) != set(RESOURCES) or any(not integer(state['resources'][r], maxima[r]) for r in RESOURCES):
        raise ValueError('Saved resource pool is outside the scenario capacity')
    spent = sum(sum(value) for value in state['spent'].values())
    if state['growth_points'] + spent != model.data['scenario']['growth_points']:
        raise ValueError('Saved growth budget does not match recorded learning')
    max_recovery = max(r['activation']['recovery_ticks'] for n in model.nodes.values() for r in n['ranks'])
    if any(not integer(v, state['tick'] + max_recovery) for v in state['ready_at'].values()):
        raise ValueError('Invalid recovery clock')
    for key in keys:
        for rank in model.nodes[key]['ranks'][:state['ranks'][key]]:
            if any(state['ranks'][r['node']] < r['rank'] for r in rank['requires']):
                raise ValueError('A saved learned rank has missing prerequisites')
    if not isinstance(state['receipts'], dict) or len(state['receipts']) > 5000:
        raise ValueError('Invalid request ledger')
    for request_id, receipt in state['receipts'].items():
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 100 or not isinstance(receipt, dict):
            raise ValueError('Invalid request receipt')
        if receipt.get('op') in ('learn', 'activate'):
            if set(receipt) != {'op', 'node', 'rank'} or receipt['node'] not in keys or not integer(receipt['rank'], len(model.nodes[receipt['node']]['ranks'])) or receipt['rank'] == 0:
                raise ValueError('Invalid node receipt')
        elif receipt.get('op') == 'respec':
            if set(receipt) != {'op', 'nodes', 'refund'} or not isinstance(receipt['nodes'], list) or not set(receipt['nodes']) <= keys or not integer(receipt['refund'], model.data['scenario']['growth_points']):
                raise ValueError('Invalid refund receipt')
        else:
            raise ValueError('Unknown saved operation')
    if not isinstance(state['events'], list) or not isinstance(state['outputs'], list) or max(len(state['events']), len(state['outputs'])) > 5000:
        raise ValueError('Saved history is too large')
    for event in state['events']:
        if (not isinstance(event, dict) or set(event) != {'tick', 'node', 'event'}
                or not integer(event['tick'], state['tick']) or event['node'] not in keys
                or event['event'] not in ('ACTIVE', 'ABORTED', 'COMPLETE')):
            raise ValueError('Invalid execution history')
    output_ids = set()
    for output in state['outputs']:
        if (not isinstance(output, dict) or set(output) != {'tick', 'node', 'output', 'request_id'}
                or not integer(output['tick'], state['tick']) or output['node'] not in keys):
            raise ValueError('Invalid output history')
        expected_outputs = {r['activation']['output'] for r in model.nodes[output['node']]['ranks']}
        receipt = state['receipts'].get(output['request_id'], {})
        if output['output'] not in expected_outputs or output['request_id'] in output_ids or receipt.get('op') != 'activate' or receipt.get('node') != output['node']:
            raise ValueError('Output does not match an activation receipt')
        output_ids.add(output['request_id'])
    active = state['active']
    if active is not None:
        if (not isinstance(active, dict) or set(active) != {'node', 'rank', 'ends_at', 'request_id'}
                or active['node'] not in keys or not integer(active['rank'], state['ranks'][active['node']]) or active['rank'] == 0):
            raise ValueError('Invalid active action')
        duration = model.nodes[active['node']]['ranks'][active['rank'] - 1]['activation']['duration_ticks']
        if not integer(active['ends_at']) or not state['tick'] < active['ends_at'] <= state['tick'] + duration:
            raise ValueError('Invalid active-action timing')
        if state['receipts'].get(active['request_id']) != {'op': 'activate', 'node': active['node'], 'rank': active['rank']} or active['request_id'] in output_ids:
            raise ValueError('Invalid active-action receipt')
