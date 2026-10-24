"""Three-axis skill engine (EXPERIMENTAL v0.3).

Deterministic, tick-based. Learning spends growth points; activation spends
focus / charge / resonance which regenerate every ``regen_interval`` ticks up
to a cap. Passive nodes raise caps or regen. Compositions are coupled: losing
any input axis, input skill or equipment aborts them with no refund.
Inherited potential can only shift learning cost; it never grants ranks,
equipment or axis access.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from . import AXES, DATA_DIR, RESOURCES

KINDS = {"practice", "expression", "passive", "composition", "capstone"}
ACCESS = ("available", "unavailable", "unknown")
SCHEMA = "0.3.0"


def load_tree(path: Path | None = None) -> dict:
    tree = json.loads(Path(path or DATA_DIR / "tree.json").read_text(encoding="utf-8"))
    validate_tree(tree)
    return tree


def tree_digest(tree: dict) -> str:
    mech = {"scenario": tree["scenario"], "potential_modifiers": tree["potential_modifiers"],
            "nodes": [{k: v for k, v in n.items() if k != "label"} for n in tree["nodes"]]}
    return hashlib.sha256(json.dumps(mech, sort_keys=True).encode()).hexdigest()


def validate_tree(tree: dict) -> dict:
    if tree.get("schema_version") != SCHEMA or tree.get("status") != "EXPERIMENTAL":
        raise ValueError("v0.3 tree must be schema 0.3.0 and EXPERIMENTAL")
    if tuple(tree["axes"]) != AXES or tuple(tree["resources"]) != RESOURCES:
        raise ValueError("Axes/resources must be exactly the three-axis set")
    sc = tree["scenario"]
    for key in ("resources", "caps", "regen"):
        if set(sc[key]) != set(RESOURCES) or any(type(v) is not int or v < 0 for v in sc[key].values()):
            raise ValueError(f"scenario.{key} must cover every resource with integers >= 0")
    if set(sc["axis_access"]) != set(AXES) or any(v not in ACCESS for v in sc["axis_access"].values()):
        raise ValueError("scenario.axis_access must cover all three axes")
    nodes = {n["id"]: n for n in tree["nodes"]}
    if len(nodes) != len(tree["nodes"]):
        raise ValueError("Duplicate node id")
    for nid, n in nodes.items():
        if n["kind"] not in KINDS:
            raise ValueError(f"{nid}: unknown kind")
        if not set(n["axes"]) <= set(AXES) or len(set(n["axes"])) != len(n["axes"]):
            raise ValueError(f"{nid}: invalid axes")
        if n["kind"] == "practice" and n["axes"]:
            raise ValueError(f"{nid}: practice is axis-independent")
        if n["kind"] in ("expression", "passive") and len(n["axes"]) != 1:
            raise ValueError(f"{nid}: expressions/passives use exactly one axis")
        if n["kind"] in ("composition", "capstone"):
            if len(n["inputs"]) < 2 or not set(n["inputs"]) <= set(n["requires"]):
                raise ValueError(f"{nid}: composition inputs must be >=2 and be prerequisites")
            union = set()
            for i in n["inputs"]:
                union |= set(nodes[i]["axes"]) if i in nodes else set()
            if union != set(n["axes"]):
                raise ValueError(f"{nid}: composition axes must equal the input axis union")
        elif n["inputs"]:
            raise ValueError(f"{nid}: only compositions have inputs")
        if type(n["growth_cost"]) is not int or n["growth_cost"] < 1:
            raise ValueError(f"{nid}: growth cost must be a positive integer")
        for ref in n["requires"] + n["requires_any"] + n["excludes"] + n["inputs"]:
            if ref not in nodes or ref == nid:
                raise ValueError(f"{nid}: bad reference {ref}")
        for ex in n["excludes"]:
            if nid not in nodes[ex]["excludes"]:
                raise ValueError(f"{nid}: exclusion with {ex} must be mutual")
        if (n["activation"] is None) == (n["passive"] is None):
            raise ValueError(f"{nid}: exactly one of activation/passive")
        if n["passive"] is not None and n["kind"] != "passive":
            raise ValueError(f"{nid}: only passive nodes carry passive effects")
        act = n["activation"]
        if act:
            if set(act["cost"]) != set(RESOURCES) or any(type(v) is not int or v < 0 for v in act["cost"].values()):
                raise ValueError(f"{nid}: invalid cost")
            if act["duration"] < 1 or act["recovery"] < 0 or act["power"] < 0:
                raise ValueError(f"{nid}: invalid timing/power")
        if n["passive"]:
            for part in ("regen", "cap"):
                if not set(n["passive"].get(part, {})) <= set(RESOURCES):
                    raise ValueError(f"{nid}: passive targets unknown resource")
    state: dict[str, int] = {}

    def visit(k):
        if state.get(k) == 1:
            raise ValueError("Cyclic prerequisites")
        if state.get(k) == 2:
            return
        state[k] = 1
        for p in nodes[k]["requires"] + nodes[k]["requires_any"]:
            visit(p)
        state[k] = 2

    for k in nodes:
        visit(k)
    return nodes


class TriModel:
    def __init__(self, tree: dict, potential: dict | None = None):
        self.tree = copy.deepcopy(tree)
        self.nodes = validate_tree(self.tree)
        if potential is not None and (set(potential) != set(AXES)
                                      or any(not 0 <= potential[a] <= 100 for a in AXES)):
            raise ValueError("Potential must give 0-100 for all three axes")
        sc = self.tree["scenario"]
        self.state = {
            "schema_version": SCHEMA, "digest": tree_digest(self.tree), "tick": 0,
            "growth_points": sc["growth_points"], "resources": dict(sc["resources"]),
            "axis_access": dict(sc["axis_access"]), "equipment": sorted(sc["equipment"]),
            "potential": None if potential is None else dict(potential),
            "learned": [], "spent": {}, "ready_at": {}, "active": None,
            "outputs": [], "events": [], "receipts": {},
        }

    # ---------------------------------------------------------------- derived
    def learn_cost(self, nid: str) -> int:
        node, pot = self.nodes[nid], self.state["potential"]
        cost = node["growth_cost"]
        if pot is None or not node["axes"]:
            return cost
        level = min(pot[a] for a in node["axes"])
        mods = self.tree["potential_modifiers"]
        if level >= mods["discount_at"]:
            cost -= 1
        elif level < mods["surcharge_below"]:
            cost += 1
        return max(1, cost)

    def _passive_total(self, part: str) -> dict:
        total = {r: 0 for r in RESOURCES}
        for nid in self.state["learned"]:
            p = self.nodes[nid]["passive"]
            if p and not self._axis_block(nid):
                for r, v in p.get(part, {}).items():
                    total[r] += v
        return total

    def caps(self) -> dict:
        extra = self._passive_total("cap")
        return {r: self.tree["scenario"]["caps"][r] + extra[r] for r in RESOURCES}

    def regen(self) -> dict:
        extra = self._passive_total("regen")
        return {r: self.tree["scenario"]["regen"][r] + extra[r] for r in RESOURCES}

    def _axis_block(self, nid: str) -> str | None:
        for axis in self.nodes[nid]["axes"]:
            if self.state["axis_access"][axis] != "available":
                return "AXIS_" + axis.upper() + "_" + self.state["axis_access"][axis].upper()
        return None

    # ---------------------------------------------------------------- learning
    def learn_block(self, nid: str) -> str | None:
        if nid not in self.nodes:
            return "UNKNOWN_NODE"
        n, learned = self.nodes[nid], set(self.state["learned"])
        if nid in learned:
            return "LEARNED_ALREADY"
        if learned & set(n["excludes"]):
            return "EXCLUDED"
        if not set(n["requires"]) <= learned or (n["requires_any"] and not learned & set(n["requires_any"])):
            return "PREREQUISITE"
        if self.state["growth_points"] < self.learn_cost(nid):
            return "POINTS"
        return None

    def learn(self, nid: str, request_id: str) -> str:
        if request_id in self.state["receipts"]:
            return "DUPLICATE"
        if self.state["active"]:
            return "BUSY"
        reason = self.learn_block(nid)
        if reason:
            return reason
        cost = self.learn_cost(nid)
        self.state["growth_points"] -= cost
        self.state["learned"].append(nid)
        self.state["spent"][nid] = cost
        self.state["receipts"][request_id] = {"op": "learn", "node": nid}
        return "LEARNED"

    def respec(self, nid: str, request_id: str) -> str:
        """Refund a learned node if nothing learned depends on it."""
        if request_id in self.state["receipts"]:
            return "DUPLICATE"
        if self.state["active"]:
            return "BUSY"
        if nid not in self.state["learned"]:
            return "NOT_LEARNED"
        rest = [k for k in self.state["learned"] if k != nid]
        for k in rest:
            n = self.nodes[k]
            if nid in n["requires"] or (n["requires_any"] and not set(rest) & set(n["requires_any"])):
                return "DEPENDENT"
        self.state["learned"] = rest
        self.state["growth_points"] += self.state["spent"].pop(nid)
        self.state["receipts"][request_id] = {"op": "respec", "node": nid}
        return "REFUNDED"

    # ---------------------------------------------------------------- activation
    def gate(self, nid: str) -> str | None:
        if nid not in self.state["learned"]:
            return "NOT_LEARNED"
        reason = self._axis_block(nid)
        if reason:
            return reason
        act = self.nodes[nid]["activation"]
        if act and not set(act["equipment"]) <= set(self.state["equipment"]):
            return "EQUIPMENT"
        for i in self.nodes[nid]["inputs"]:
            reason = self.gate(i)
            if reason:
                return reason
        return None

    def participants(self, nid: str) -> list[str]:
        seen, stack = [], [nid]
        while stack:
            k = stack.pop()
            if k not in seen:
                seen.append(k)
                stack.extend(self.nodes[k]["inputs"])
        return seen

    def availability(self, nid: str) -> str:
        if nid not in self.state["learned"]:
            return "LOCKED"
        if self.nodes[nid]["activation"] is None:
            return "PASSIVE" if not self._axis_block(nid) else "SUSPENDED"
        if self.gate(nid):
            return "SUSPENDED"
        if self.state["active"] and self.state["active"]["node"] == nid:
            return "ACTIVE"
        if any(self.state["ready_at"].get(p, 0) > self.state["tick"] for p in self.participants(nid)):
            return "RECOVERING"
        cost = self.nodes[nid]["activation"]["cost"]
        if any(self.state["resources"][r] < cost[r] for r in RESOURCES):
            return "DEPLETED"
        return "READY"

    def activate(self, nid: str, request_id: str) -> str:
        if request_id in self.state["receipts"]:
            return "DUPLICATE"
        if self.state["active"]:
            return "BUSY"
        status = self.availability(nid)
        if status != "READY":
            return status
        act = self.nodes[nid]["activation"]
        for r in RESOURCES:
            self.state["resources"][r] -= act["cost"][r]
        self.state["active"] = {"node": nid, "ends_at": self.state["tick"] + act["duration"],
                                "request_id": request_id}
        self.state["receipts"][request_id] = {"op": "activate", "node": nid}
        self.state["events"].append({"tick": self.state["tick"], "node": nid, "event": "STARTED"})
        return "STARTED"

    def _finish(self, event: str) -> None:
        active = self.state["active"]
        act = self.nodes[active["node"]]["activation"]
        for p in self.participants(active["node"]):
            self.state["ready_at"][p] = self.state["tick"] + act["recovery"]
        if event == "COMPLETE":
            self.state["outputs"].append({"tick": self.state["tick"], "node": active["node"],
                                          "output": act["output"], "power": act["power"]})
        self.state["events"].append({"tick": self.state["tick"], "node": active["node"], "event": event})
        self.state["active"] = None

    def _enforce(self) -> None:
        if self.state["active"] and self.gate(self.state["active"]["node"]):
            self._finish("ABORTED")
        caps = self.caps()
        for r in RESOURCES:
            self.state["resources"][r] = min(self.state["resources"][r], caps[r])

    def set_axis(self, axis: str, access: str) -> None:
        if axis not in AXES or access not in ACCESS:
            raise ValueError("Invalid axis access")
        self.state["axis_access"][axis] = access
        self._enforce()

    def set_equipment(self, equipment) -> None:
        self.state["equipment"] = sorted(set(equipment))
        self._enforce()

    def advance(self, ticks: int = 1) -> None:
        if type(ticks) is not int or ticks < 0:
            raise ValueError("Ticks must be a nonnegative integer")
        interval = self.tree["scenario"]["regen_interval"]
        for _ in range(ticks):
            self.state["tick"] += 1
            self._enforce()
            if interval and self.state["tick"] % interval == 0:
                caps, regen = self.caps(), self.regen()
                for r in RESOURCES:
                    self.state["resources"][r] = min(caps[r], self.state["resources"][r] + regen[r])
            active = self.state["active"]
            if active and self.state["tick"] >= active["ends_at"]:
                self._finish("COMPLETE")

    def score(self) -> int:
        return sum(o["power"] for o in self.state["outputs"])

    # ---------------------------------------------------------------- persistence
    def save(self) -> str:
        return json.dumps(self.state, sort_keys=True)

    @classmethod
    def restore(cls, tree: dict, saved: str) -> "TriModel":
        state = json.loads(saved)
        model = cls(tree, state.get("potential"))
        if state.get("schema_version") != SCHEMA or state.get("digest") != model.state["digest"]:
            raise ValueError("Save belongs to another ruleset; migrate explicitly")
        if set(state) != set(model.state):
            raise ValueError("Incompatible save fields")
        # Replay learning to prove the ledger is legal under this tree.
        for i, nid in enumerate(state["learned"]):
            if model.learn(nid, f"replay-{i}") != "LEARNED" or model.state["spent"][nid] != state["spent"].get(nid):
                raise ValueError("Saved learning ledger is not reproducible")
        if model.state["growth_points"] != state["growth_points"] or set(state["spent"]) != set(state["learned"]):
            raise ValueError("Saved growth points do not match the ledger")
        caps = model.caps()
        if any(type(state["resources"][r]) is not int or not 0 <= state["resources"][r] <= caps[r] for r in RESOURCES):
            raise ValueError("Saved resources out of range")
        if state["active"] is not None and state["active"]["node"] not in state["learned"]:
            raise ValueError("Active action references an unlearned node")
        model.state = state
        model._enforce()
        return model


def migrate_v02(v02_saved: str, tree: dict | None = None) -> TriModel:
    """Convert a v0.2 workbench save into a v0.3 model.

    Learned v0.2 nodes (M0, T0, A1, T1, H1 keep their ids) are re-learned at
    v0.3 costs; tick, outputs and focus/charge carry over (clamped to caps);
    Finity access starts available; resonance starts at the scenario value;
    an in-flight v0.2 action is aborted without refund, as in v0.2.
    """
    tree = tree or load_tree()
    old = json.loads(v02_saved)
    model = TriModel(tree)
    learned = [k for k, r in old.get("ranks", {}).items() if r > 0]
    order = [n["id"] for n in tree["nodes"] if n["id"] in learned]
    for i, nid in enumerate(order):
        result = model.learn(nid, f"migrate-{i}")
        if result != "LEARNED":
            raise ValueError(f"Cannot migrate {nid}: {result}")
    caps = model.caps()
    for r in ("focus", "charge"):
        model.state["resources"][r] = min(caps[r], int(old["resources"][r]))
    for axis in ("Affinity", "Techfinity"):
        model.state["axis_access"][axis] = old["axis_access"][axis]
    model.state["equipment"] = sorted(old.get("equipment", []))
    model.state["tick"] = int(old.get("tick", 0))
    for o in old.get("outputs", []):
        node = model.nodes.get(o["node"])
        power = node["activation"]["power"] if node and node["activation"] else 0
        model.state["outputs"].append({"tick": o["tick"], "node": o["node"], "output": o["output"], "power": power})
    if old.get("active"):
        model.state["events"].append({"tick": model.state["tick"], "node": old["active"]["node"],
                                      "event": "ABORTED_BY_MIGRATION"})
    model.state["events"].append({"tick": model.state["tick"], "node": None, "event": "MIGRATED_FROM_0.2"})
    return model
