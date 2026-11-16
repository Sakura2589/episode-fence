"""Explicit provenance, auditable train/validation boundaries."""
from .model import Clip, Policy, ManifestError
from .engine import audit, plan
__version__ = "0.1.0"
__all__ = ["Clip", "Policy", "ManifestError", "audit", "plan"]
