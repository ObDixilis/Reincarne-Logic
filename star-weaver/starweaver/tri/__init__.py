"""Star Weaver v0.3 (EXPERIMENTAL): three-axis skills, heredity, emergence and ecosystem.

This package lives beside the approved v0.2 baseline (``starweaver.engine`` /
``starweaver.heredity``) and does not modify it. Finity is a full axis here;
that change needs explicit approval before it supersedes SW-SKILL-001.
"""
from pathlib import Path

__version__ = "0.3.0"
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "v3"
AXES = ("Affinity", "Techfinity", "Finity")
RESOURCES = ("focus", "charge", "resonance")
