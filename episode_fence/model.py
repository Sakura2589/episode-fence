"""The frame coordinate contract. Intervals are always [start, stop)."""
from dataclasses import dataclass, asdict
import hashlib
import json


class ManifestError(ValueError):
    pass


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ManifestError(f"{name} must be an integer >= {minimum}")
    return value


def label(value, name, optional=False):
    if not isinstance(value, str) or (not optional and not value.strip()):
        raise ManifestError(f"{name} must be a non-empty string")
    if len(value) > 512 or any(ord(c) < 32 for c in value):
        raise ManifestError(f"{name} must be <=512 characters without control characters")
    return value


@dataclass(frozen=True)
class Clip:
    id: str
    source: str
    start: int
    stop: int
    source_frames: int
    split: str
    task: str = ""
    group: str = ""

    def __post_init__(self):
        for name in ("id", "source", "split"):
            label(getattr(self, name), name)
        for name in ("task", "group"):
            label(getattr(self, name), name, optional=True)
        for name in ("start", "stop", "source_frames"):
            integer(getattr(self, name), name)
            if getattr(self, name) > 2**53 - 1:
                raise ManifestError(f"{name} exceeds the maximum exact frame index (2**53-1)")
        if not 0 <= self.start < self.stop <= self.source_frames:
            raise ManifestError("expected 0 <= start < stop <= source_frames")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Policy:
    history: int = 0
    future: int = 0
    embargo: int = 0
    isolate_groups: bool = False

    def __post_init__(self):
        for name in ("history", "future", "embargo"):
            integer(getattr(self, name), name)
        if type(self.isolate_groups) is not bool:
            raise ManifestError("isolate_groups must be a boolean")

    def window(self, clip):
        return max(0, clip.start - self.history), min(clip.source_frames, clip.stop + self.future)

    def to_dict(self):
        return asdict(self)


def validate(clips, policy):
    if not clips:
        raise ManifestError("manifest contains no clips")
    if len(clips) > 100_000:
        raise ManifestError("limit: 100,000 clips per audit")
    ids, lengths, splits = set(), {}, set()
    for clip in clips:
        if not isinstance(clip, Clip):
            raise ManifestError("expected Clip objects")
        if clip.id in ids:
            raise ManifestError(f"duplicate clip id: {clip.id}")
        ids.add(clip.id)
        if clip.source in lengths and lengths[clip.source] != clip.source_frames:
            raise ManifestError(f"inconsistent source_frames for {clip.source}")
        lengths[clip.source] = clip.source_frames
        splits.add(clip.split)
        if policy.isolate_groups and not clip.group:
            raise ManifestError(f"{clip.id}: group is required with isolate_groups")
    if len(splits) > 16:
        raise ManifestError("limit: 16 split labels")
    return clips


def fingerprint(clips, policy):
    payload = {"clips": [c.to_dict() for c in sorted(clips, key=lambda c: c.id)],
               "policy": policy.to_dict()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True,
                                     separators=(",", ":")).encode()).hexdigest()
