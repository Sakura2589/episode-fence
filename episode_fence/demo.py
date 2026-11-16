"""Synthetic examples; no claims about real datasets."""
from .model import Clip

def demo_clips():
    rows = [
        ("pick-01/front", "recording-01", 0, 100, 300, "train", "pick cup", "session-a"),
        ("pick-01/wrist", "recording-01", 40, 140, 300, "validation", "pick cup", "session-a"),
        ("pick-02/early", "recording-02", 0, 100, 300, "train", "pick cup", "session-b"),
        ("pick-02/late", "recording-02", 110, 200, 300, "validation", "pick cup", "session-b"),
        ("place-03", "recording-03", 0, 160, 160, "train", "place cup", "session-c"),
        ("place-04", "recording-04", 0, 140, 140, "validation", "place cup", "session-d"),
        ("pick-05", "recording-05", 0, 180, 180, "train", "pick cup", "session-e"),
        ("pick-06", "recording-06", 0, 150, 150, "train", "pick cup", "session-f"),
        ("place-07", "recording-07", 0, 170, 170, "train", "place cup", "session-g"),
        ("place-08", "recording-08", 0, 120, 120, "validation", "place cup", "session-h"),
    ]
    return [Clip(*row) for row in rows]
