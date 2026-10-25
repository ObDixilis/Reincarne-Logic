"""Manifestation Compiler for Star Weaver v0.3.1 (EXPERIMENTAL).

Compiles engine activation events into grounded Neoluminescent manifestations:
- 7-Anchor Color Gamut with skin-safe luminance clamping (preserving Black skin tone detail)
- Geometric Line Grammar (wave = flow carrier, particle = impulse, zigzag = control logic)
- Material Interfaces (Aetherwear wearable conduit vs Assorcery magech tooling vs Inherent somatic flow)
- Rigorous separation of physical World-State Effect from Sensory Expression & Choreography
- Breakdown & failure responses upon axis loss or hardware interruption
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import DATA_DIR

SCHEMA_VERSION = "0.3.1"
PROPOSAL_ID = "SW-MANIFEST-001"


def load_manifestation_catalog(path: Path | None = None) -> dict[str, Any]:
    file_path = Path(path or DATA_DIR / "manifestations.json")
    if not file_path.is_file():
        raise FileNotFoundError(f"Manifestation catalog not found at {file_path}")
    data = json.loads(file_path.read_text(encoding="utf-8"))
    validate_manifestation_catalog(data)
    return data


def validate_manifestation_catalog(data: dict[str, Any]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Expected schema_version {SCHEMA_VERSION}, got {data.get('schema_version')}")
    if data.get("status") != "EXPERIMENTAL":
        raise ValueError("Manifestation contract must remain explicitly EXPERIMENTAL")
    for key in ("color_gamut", "line_grammar_rules", "material_channels", "manifestations"):
        if key not in data:
            raise ValueError(f"Missing required top-level key: {key}")

    gamut = data["color_gamut"]
    for color_key, entry in gamut.items():
        if "hex" not in entry or not entry["hex"].startswith("#"):
            raise ValueError(f"Color {color_key} missing valid hex string")
        if "skin_safe_max_luminance_nits" not in entry or entry["skin_safe_max_luminance_nits"] <= 0:
            raise ValueError(f"Color {color_key} must specify positive skin_safe_max_luminance_nits")

    grammar = data["line_grammar_rules"]
    for mode in ("wave", "particle", "zigzag"):
        if mode not in grammar:
            raise ValueError(f"Missing line grammar definition for '{mode}'")

    channels = data["material_channels"]
    for ch in ("Aetherwear", "Assorcery", "Ordinary", "Inherent"):
        if ch not in channels:
            raise ValueError(f"Missing material channel definition for '{ch}'")

    for skill_id, man in data["manifestations"].items():
        for req in ("skill_id", "material_channel", "line_grammar", "color_signature",
                    "choreography", "world_effect", "sensory_expression", "failure"):
            if req not in man:
                raise ValueError(f"Manifestation for {skill_id} missing required field '{req}'")
        for g in man["line_grammar"]:
            if g not in grammar:
                raise ValueError(f"Skill {skill_id} references unknown line grammar '{g}'")
        for c in man["color_signature"]:
            if c not in gamut:
                raise ValueError(f"Skill {skill_id} references unknown color '{c}'")


@dataclass(frozen=True)
class ColorAnchor:
    key: str
    name: str
    hex: str
    semantic_role: str
    max_luminance_nits: float


@dataclass(frozen=True)
class LineGrammarElement:
    kind: str  # wave, particle, zigzag
    mode: str
    physics_behavior: str
    carrier_role: str


@dataclass
class ManifestationFrame:
    skill_id: str
    label: str
    status: str  # ACTIVE, COMPLETED, INTERRUPTED
    tick: int
    material_channel: str
    channel_definition: str
    apparatus_required: list[str]
    apparatus_present: list[str]
    line_grammar: list[LineGrammarElement]
    visual_palette: list[ColorAnchor]
    skin_tone_protection_rule: str
    choreography: dict[str, str]
    world_effect: dict[str, Any]
    sensory_expression: dict[str, str]
    failure_report: dict[str, str] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "label": self.label,
            "status": self.status,
            "tick": self.tick,
            "material_channel": self.material_channel,
            "channel_definition": self.channel_definition,
            "apparatus_required": list(self.apparatus_required),
            "apparatus_present": list(self.apparatus_present),
            "line_grammar": [asdict(g) for g in self.line_grammar],
            "visual_palette": [asdict(c) for c in self.visual_palette],
            "skin_tone_protection_rule": self.skin_tone_protection_rule,
            "choreography": dict(self.choreography),
            "world_effect": dict(self.world_effect),
            "sensory_expression": dict(self.sensory_expression),
            "failure_report": dict(self.failure_report) if self.failure_report else None,
        }

    def render_ascii_diagram(self) -> str:
        """Procedural ASCII visualizer of the luminous geometry and physical presence."""
        lines = [
            f"=== Manifestation Frame: {self.label} ({self.skill_id}) [Status: {self.status}] ===",
            f"Material Interface : {self.material_channel} (Apparatus: {', '.join(self.apparatus_present) or 'None'})",
            f"Line Grammar       : {' + '.join(g.kind.upper() for g in self.line_grammar)}",
            f"Color Gamut        : {' + '.join(f'{c.name} ({c.hex})' for c in self.visual_palette)}",
            f"Luminance Bound    : Capped at {min(c.max_luminance_nits for c in self.visual_palette)} nits (Skin-safe)",
            f"Choreography       : {self.choreography.get('flow_style', 'Standard')} [{self.choreography.get('rhythm', '')}]",
            "--- Spatial Geometry ---",
        ]

        grammars = [g.kind for g in self.line_grammar]
        if "wave" in grammars and "zigzag" in grammars:
            # Dual-braid helix visualization (e.g. Woven Beacon H1)
            lines.extend([
                "  (MAGENTA WAVE)      ~\\         /~\\         /~\\         /~",
                "                       \\  +=====+  /  +=====+  /  +=====+  ",
                "  (CYAN ZIGZAG)        +[ZIGZAG]+-[ZIGZAG]+-[ZIGZAG]+- > [ENCODED BEACON]",
                "                       /  +=====+  \\  +=====+  \\  +=====+  ",
                "  (MAGENTA WAVE)      ~/         \\_/~         \\_/~         \\_",
                "  [Coherence Nodes]    *            *            *            * (Interference Flashes)",
            ])
        elif "wave" in grammars and "particle" in grammars:
            # Concentric / particle ring (e.g. Threshold Sense F1)
            lines.extend([
                "          . : * (PARTICLE PULSE) * : .",
                "       .'     ~~~~~~~~~~~~~~~~~~~     '.",
                "      :    (CONCENTRIC LIMINAL IRIS)    :",
                "       '.     ~~~~~~~~~~~~~~~~~~~     .'",
                "          ' : * (PARTICLE PULSE) * : '",
            ])
        elif "wave" in grammars:
            # Pure wave (e.g. Guided Light A1, Learned Light M0)
            lines.extend([
                "  (CONTINUOUS FLOW)   ~~/~~\\~~/~~\\~~/~~\\~~/~~\\~~> [RESONANT ARC]",
                "                      ~~~~~~~~~~~~~~~~~~~~~~~~~",
            ])
        elif "zigzag" in grammars:
            # Pure routed logic (e.g. Signal Control T1, Lamp Handling T0)
            lines.extend([
                "  (ROUTED LOGIC)      |--+   +--+   +--+   +----> [CLOCK RASTER]",
                "                         |---|  |---|  |---|",
            ])
        else:
            lines.append("  [Omni-directional ambient radiance]")

        lines.extend([
            "--- Reality Consequence ---",
            f"World Effect       : {self.world_effect.get('kind', 'None')}",
            f"Signal Protocol    : {self.world_effect.get('signal_protocol') or 'None (Unencoded)'}",
            f"Collision Profile  : {self.world_effect.get('collision_profile') or 'None (Non-solid)'}",
            f"Physical Range     : {self.world_effect.get('range_meters') or 'Unbounded/Unquantified (Pending World Laws)'}",
            f"Persistence        : {self.world_effect.get('persistence_ticks', 0)} ticks",
            f"Skin-Safe Rule     : {self.skin_tone_protection_rule}",
        ])

        if self.failure_report:
            lines.extend([
                "--- Interruption & Failure Breakdown ---",
                f"Breakdown Visual   : {self.failure_report.get('breakdown_visual')}",
                f"Somatic Recoil     : {self.failure_report.get('somatic_recoil')}",
            ])

        return "\n".join(lines)


class ManifestationCompiler:
    """Reality compiler service that computes complete manifestation frames from engine state."""

    def __init__(self, catalog: dict[str, Any] | None = None):
        self.catalog = catalog or load_manifestation_catalog()

    def compile(
        self,
        skill_id: str,
        tick: int = 0,
        status: str = "ACTIVE",
        performer_profile: dict[str, Any] | None = None,
        equipment_present: list[str] | None = None,
        interrupted: bool = False,
        interruption_reason: str | None = None,
    ) -> ManifestationFrame:
        if skill_id not in self.catalog["manifestations"]:
            raise KeyError(f"No manifestation contract registered for skill '{skill_id}'")

        man = copy.deepcopy(self.catalog["manifestations"][skill_id])
        gamut_db = self.catalog["color_gamut"]
        grammar_db = self.catalog["line_grammar_rules"]
        channel_db = self.catalog["material_channels"]

        # 1. Resolve Color Palette
        palette: list[ColorAnchor] = []
        for c_key in man["color_signature"]:
            c_info = gamut_db[c_key]
            palette.append(ColorAnchor(
                key=c_key,
                name=c_info["name"],
                hex=c_info["hex"],
                semantic_role=c_info["semantic_role"],
                max_luminance_nits=float(c_info["skin_safe_max_luminance_nits"]),
            ))

        # 2. Resolve Line Grammar
        grammar_list: list[LineGrammarElement] = []
        for g_key in man["line_grammar"]:
            g_info = grammar_db[g_key]
            grammar_list.append(LineGrammarElement(
                kind=g_key,
                mode=g_info["mode"],
                physics_behavior=g_info["physics_behavior"],
                carrier_role=g_info["carrier_role"],
            ))

        # 3. Material Channel & Hardware
        channel_name = man["material_channel"]
        channel_def = channel_db[channel_name]["definition"]
        req_equipment = list(man.get("apparatus_required", []))
        present_equipment = list(equipment_present) if equipment_present is not None else req_equipment

        # 4. Choreography customisation based on mentorship lineage
        choreography = dict(man["choreography"])
        if performer_profile and "mentorship_tradition" in performer_profile:
            trad = performer_profile["mentorship_tradition"]
            choreography["flow_style"] = f"{trad} Variation: {choreography['flow_style']}"

        # 5. Interruption / Failure breakdown
        failure_report = None
        current_status = "INTERRUPTED" if interrupted else status

        if interrupted:
            fail_spec = man["failure"]
            failure_report = {
                "reason": interruption_reason or "UNKNOWN_INTERRUPTION",
                "breakdown_visual": fail_spec["breakdown_visual"],
                "somatic_recoil": fail_spec["somatic_recoil"],
            }
            # Interrupted world effect ceases persistence
            man["world_effect"]["persistence_ticks"] = 0

        return ManifestationFrame(
            skill_id=skill_id,
            label=man["label"],
            status=current_status,
            tick=tick,
            material_channel=channel_name,
            channel_definition=channel_def,
            apparatus_required=req_equipment,
            apparatus_present=present_equipment,
            line_grammar=grammar_list,
            visual_palette=palette,
            skin_tone_protection_rule=man["sensory_expression"]["skin_tone_protection_rule"],
            choreography=choreography,
            world_effect=man["world_effect"],
            sensory_expression=man["sensory_expression"],
            failure_report=failure_report,
        )


def compile_woven_beacon_vertical_slice(equipment: list[str] | None = None, drop_lamp: bool = False) -> dict[str, Any]:
    """Generates the full vertical slice manifestation comparison for H1 Woven Beacon."""
    compiler = ManifestationCompiler()
    equip = equipment if equipment is not None else ["lamp"]

    # 1. Normal successful execution frame
    normal_frame = compiler.compile(
        skill_id="H1",
        tick=2,
        status="ACTIVE",
        equipment_present=equip,
        interrupted=False,
    )

    # 2. Interrupted execution frame (hardware loss: lamp removed)
    interrupted_frame = compiler.compile(
        skill_id="H1",
        tick=3,
        status="INTERRUPTED",
        equipment_present=[] if drop_lamp else equip,
        interrupted=True,
        interruption_reason="HARDWARE_LOSS: lamp missing during active composition",
    )

    return {
        "skill_id": "H1",
        "label": "Woven Beacon",
        "normal_execution": normal_frame.to_dict(),
        "normal_ascii": normal_frame.render_ascii_diagram(),
        "interrupted_execution": interrupted_frame.to_dict(),
        "interrupted_ascii": interrupted_frame.render_ascii_diagram(),
    }
