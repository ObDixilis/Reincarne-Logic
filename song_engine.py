"""Modular songwriting engine prototype.

This module implements a symbolic, engine-based meaning pipeline:

parse -> select -> route -> symbolize -> structure -> generate -> audit
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import re


@dataclass
class SongInput:
    raw_prompt: str
    persona: str
    genre: str
    desired_effect: str = ""
    constraints: Dict[str, str] | None = None


@dataclass
class Signal:
    reality: str
    emotion: str
    pressure: str
    motion: str


@dataclass
class SongSection:
    name: str
    function: str
    engines: List[str]
    intensity: float


@dataclass
class SongDraft:
    primary_engine: str
    support_engines: List[str]
    motif_bank: List[str]
    section_map: List[SongSection]
    lyrics: Dict[str, List[str]]
    solved_statement: str
    engine_trace: Dict[str, object]


def _contains_any(text: str, words: List[str]) -> bool:
    lowered = text.lower()
    return any(w in lowered for w in words)


def parse_prompt(raw_prompt: str) -> Signal:
    """Extract symbolic core variables from a raw prompt."""
    prompt = raw_prompt.lower()

    # Emotional core
    emotion = "reflective tension"
    if _contains_any(prompt, ["longing", "love", "tender", "regret", "miss"]):
        emotion = "longing tenderness"
    elif _contains_any(prompt, ["dominant", "control", "pressure", "threat", "smoke"]):
        emotion = "dominant heat"
    elif _contains_any(prompt, ["transform", "rebirth", "becoming", "threshold"]):
        emotion = "transformational emergence"
    elif _contains_any(prompt, ["irony", "double", "hidden", "coded"]):
        emotion = "layered ambiguity"

    # Motion
    motion = "confession"
    if _contains_any(prompt, ["challenge", "threat", "dominate", "proof"]):
        motion = "public proof"
    elif _contains_any(prompt, ["flirt", "desire", "seduce"]):
        motion = "magnetic pull"
    elif _contains_any(prompt, ["grief", "loss", "goodbye"]):
        motion = "release"
    elif _contains_any(prompt, ["transform", "rebirth", "new form"]):
        motion = "transformation"

    # Pressure
    pressure = "silence and uncertainty"
    if _contains_any(prompt, ["time", "late", "clock", "last chance"]):
        pressure = "closing time window"
    elif _contains_any(prompt, ["room", "crowd", "public", "stage"]):
        pressure = "social witness pressure"
    elif _contains_any(prompt, ["fake", "betray", "mask", "lie"]):
        pressure = "trust fracture"

    # Reality
    reality = "interior monologue"
    if _contains_any(prompt, ["city", "night", "window", "moon"]):
        reality = "night-city introspection"
    elif _contains_any(prompt, ["club", "smoke", "bass", "floor"]):
        reality = "club pressure chamber"
    elif _contains_any(prompt, ["code", "syntax", "ai", "myth-tech"]):
        reality = "myth-tech ritual space"

    return Signal(reality=reality, emotion=emotion, pressure=pressure, motion=motion)


def score_engines(signal: Signal, persona: str, genre: str) -> Dict[str, float]:
    """Assign weighted fitness scores to candidate engines."""
    persona_l = persona.lower()
    genre_l = genre.lower()

    engine_profiles = {
        "Gaze": ["longing tenderness", "reflective", "rap-soul"],
        "Time-Weight": ["closing time window", "reflective", "confession"],
        "Room Tilt": ["social witness pressure", "club", "public proof"],
        "Pressure": ["dominant heat", "club", "public proof"],
        "Refraction": ["layered ambiguity", "coded", "double"],
        "Mask Leak": ["trust fracture", "sly", "ambiguity"],
        "Threshold Transformation": ["transformational emergence", "transformation", "myth"],
        "Attention": ["longing tenderness", "magnetic", "intimacy"],
        "Pivot": ["release", "transformation", "bridge"],
        "Proof": ["public proof", "dominant", "crowd"],
    }

    scores: Dict[str, float] = {}
    for engine, cues in engine_profiles.items():
        relevance_to_emotion = 1.0 if signal.emotion in cues else 0.3
        relevance_to_genre = 1.0 if any(c in genre_l for c in cues) else 0.4
        relevance_to_persona = 1.0 if any(c in persona_l for c in cues) else 0.4
        symbolic_depth = 0.8 if engine in {"Refraction", "Threshold Transformation", "Gaze"} else 0.6
        structural_usefulness = 0.9 if engine in {"Time-Weight", "Pressure", "Pivot", "Proof"} else 0.7

        scores[engine] = (
            relevance_to_emotion * 0.35
            + relevance_to_genre * 0.20
            + relevance_to_persona * 0.20
            + symbolic_depth * 0.15
            + structural_usefulness * 0.10
        )

        # Direct boosts from signal
        if signal.pressure == "closing time window" and engine == "Time-Weight":
            scores[engine] += 0.35
        if signal.pressure == "social witness pressure" and engine in {"Room Tilt", "Proof"}:
            scores[engine] += 0.30
        if signal.motion == "transformation" and engine == "Threshold Transformation":
            scores[engine] += 0.30
        if signal.emotion == "layered ambiguity" and engine == "Refraction":
            scores[engine] += 0.30

    return scores


def select_engines(signal: Signal, persona: str, genre: str) -> Tuple[str, List[str], str, Dict[str, float]]:
    """Select 1 lead engine, 2-4 support engines, and 1 structural engine."""
    scores = score_engines(signal, persona, genre)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

    primary = ranked[0][0]
    support = [name for name, _ in ranked[1:5]]  # next 4

    structural_candidates = ["Pivot", "Time-Weight", "Proof", "Pressure"]
    structural = max(structural_candidates, key=lambda e: scores.get(e, 0.0))

    if structural == primary and support:
        structural = support[-1]

    return primary, support[:4], structural, scores


def generate_motifs(signal: Signal, primary: str, support: List[str], persona: str, genre: str) -> List[str]:
    """Create a connected motif bank based on signal + engines."""
    motifs = []

    reality_motifs = {
        "night-city introspection": ["moon", "window", "dust", "clock", "door"],
        "club pressure chamber": ["smoke", "kick drum", "chain flash", "roof", "floor jump"],
        "myth-tech ritual space": ["syntax", "sigil", "chrome altar", "neon rune", "sequence"],
        "interior monologue": ["mirror", "handshake", "hallway", "breath", "lamp"],
    }

    engine_motifs = {
        "Gaze": ["eyes", "lens", "orbit"],
        "Time-Weight": ["hourglass", "pulse", "countdown"],
        "Room Tilt": ["section tilt", "gravity", "crowd sway"],
        "Pressure": ["heat", "compress", "faultline"],
        "Refraction": ["double meaning", "prism", "echo"],
        "Mask Leak": ["crack", "costume seam", "wet paint"],
        "Threshold Transformation": ["doorframe", "molting", "new name"],
        "Attention": ["spotlight", "whisper", "touchline"],
        "Pivot": ["turn", "hinge", "switchback"],
        "Proof": ["witness", "stamp", "verdict"],
    }

    motifs.extend(reality_motifs.get(signal.reality, []))
    motifs.extend(engine_motifs.get(primary, []))
    for e in support[:3]:
        motifs.extend(engine_motifs.get(e, [])[:2])

    if "gorgon" in persona.lower():
        motifs.extend(["serpent halo", "obsidian", "throne"])
    if "joshyua" in persona.lower() or "prompt guy" in persona.lower():
        motifs.extend(["notebook", "prayer hands", "bus stop light"])
    if "rap-soul" in genre.lower():
        motifs.extend(["falsetto ghost", "snare rain"])

    # De-duplicate while preserving order
    seen = set()
    ordered = []
    for m in motifs:
        if m not in seen:
            ordered.append(m)
            seen.add(m)
    return ordered[:14]


def assign_engines_to_sections(primary: str, support: List[str], structural: str, desired_motion: str) -> List[SongSection]:
    """Map engines to section-level functions."""
    bridge_secondary = support[3] if support[3] != structural else support[2]
    return [
        SongSection("Intro", "Frame reality and voice", [primary], 0.25),
        SongSection("Verse 1", "Introduce pressure and first claim", [primary, support[0]], 0.45),
        SongSection("Pre-Chorus", "Concentrate tension", [support[1], structural], 0.62),
        SongSection("Chorus", "Repeatable thesis", [primary, structural], 0.82),
        SongSection("Verse 2", "Complicate and deepen", [support[2], support[0], primary], 0.72),
        SongSection("Bridge", f"Pivot toward {desired_motion}", [structural, bridge_secondary], 0.90),
        SongSection("Final Chorus", "Resolved or intensified thesis", [primary, structural, support[0]], 0.95),
        SongSection("Outro", "Residue and symbolic close", [support[1]], 0.40),
    ]


def _line(seed_a: str, seed_b: str, seed_c: str, persona: str, intensity: float) -> str:
    vibe = "quiet" if intensity < 0.5 else "burning" if intensity > 0.8 else "steady"
    return f"{seed_a} in my {seed_b}, {seed_c} stays {vibe} ({persona.split('/')[0].strip()})"


def generate_section_lines(
    section: SongSection,
    persona: str,
    motifs: List[str],
    signal: Signal,
) -> List[str]:
    """Generate lines constrained by section function and active engines."""
    # Deterministic motif selection for repeatability
    offset = len(section.name)
    pool = motifs[offset % len(motifs):] + motifs[: offset % len(motifs)]

    lines = [
        _line(pool[0], pool[1], signal.pressure, persona, section.intensity),
        _line(pool[2], pool[3], section.function.lower(), persona, section.intensity),
        f"[{section.name}] {signal.reality} -> {', '.join(section.engines)}",
    ]

    if section.name in {"Chorus", "Final Chorus"}:
        lines.append(f"Hook: choose now before the {signal.pressure} closes")

    return lines


def audit_song(lyrics: Dict[str, List[str]], motifs: List[str]) -> Dict[str, List[str]]:
    """Run lightweight anti-regurgitation and coherence checks."""
    used = set()
    audited: Dict[str, List[str]] = {}

    for section, lines in lyrics.items():
        new_lines = []
        for line in lines:
            # Remove direct accidental duplication
            line_norm = re.sub(r"\s+", " ", line.strip().lower())
            if line_norm in used:
                continue
            used.add(line_norm)

            # Ensure embodiedness with motif injection if too abstract
            if len(re.findall(r"\b(is|are|was|were|feel|felt)\b", line_norm)) > 1:
                line = f"{line} / with {motifs[0]} and {motifs[1]}"
            new_lines.append(line)

        if not new_lines:
            new_lines = [f"[{section}] (compressed for coherence)"]
        audited[section] = new_lines

    return audited


def derive_thesis(signal: Signal, primary_engine: str) -> str:
    return (
        f"Through {primary_engine}, the song transforms {signal.reality} pressure "
        f"({signal.pressure}) into {signal.motion}."
    )


def build_song(song_input: SongInput) -> SongDraft:
    signal = parse_prompt(song_input.raw_prompt)
    primary, support, structural, scores = select_engines(signal, song_input.persona, song_input.genre)
    motifs = generate_motifs(signal, primary, support, song_input.persona, song_input.genre)
    sections = assign_engines_to_sections(primary, support, structural, signal.motion)

    lyrics: Dict[str, List[str]] = {}
    for section in sections:
        lyrics[section.name] = generate_section_lines(section, song_input.persona, motifs, signal)

    audited = audit_song(lyrics, motifs)
    thesis = derive_thesis(signal, primary)

    return SongDraft(
        primary_engine=primary,
        support_engines=support,
        motif_bank=motifs,
        section_map=sections,
        lyrics=audited,
        solved_statement=thesis,
        engine_trace={
            "signal": asdict(signal),
            "engine_scores": {k: round(v, 3) for k, v in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)},
            "structural_engine": structural,
        },
    )


def demo() -> None:
    example = SongInput(
        raw_prompt="late-night freestyle confession about perception, time, love, and regret",
        persona="Joshyua / Prompt Guy",
        genre="reflective rap-soul",
    )
    result = build_song(example)

    print("=== Engine Trace ===")
    print(result.engine_trace)
    print("\n=== Motif Bank ===")
    print(result.motif_bank)
    print("\n=== Solved Statement ===")
    print(result.solved_statement)
    print("\n=== Draft ===")
    for section, lines in result.lyrics.items():
        print(f"\n{section}:")
        for ln in lines:
            print(f"- {ln}")


if __name__ == "__main__":
    demo()
