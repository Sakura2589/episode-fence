"""Interval witnesses and deterministic connected-component split planning."""
from collections import defaultdict
from dataclasses import replace
import hashlib
import math
from .model import Policy, ManifestError, validate, fingerprint, integer


def _buckets(clips, key):
    result = defaultdict(list)
    for clip in clips:
        result[getattr(clip, key)].append(clip)
    return result


def audit(clips, policy=Policy(), max_witnesses=200):
    """Complete affected-clip detection; bounded representative evidence, not all pairs."""
    clips = sorted(validate(list(clips), policy), key=lambda c: c.id)
    integer(max_witnesses, "max_witnesses")
    windows = {c.id: policy.window(c) for c in clips}
    affected, evidence, seen = set(), [], set()
    witness_visits = 0

    def witness(a, b, group=False):
        nonlocal witness_visits
        if a.split == b.split:
            return
        affected.update((a.id, b.id))
        witness_visits += 1
        a, b = sorted((a, b), key=lambda c: c.id)
        key = (a.id, b.id, group)
        if key in seen or len(evidence) >= max_witnesses:
            return
        seen.add(key)
        left, right = max(windows[a.id][0], windows[b.id][0]), min(windows[a.id][1], windows[b.id][1])
        raw_overlap = min(a.stop, b.stop) > max(a.start, b.start)
        kind = "group" if group else ("raw-overlap" if raw_overlap else
                                      "window-overlap" if left < right else "embargo")
        evidence.append({"a": a.id, "b": b.id, "splits": [a.split, b.split],
                         "kind": kind, "source": None if group else a.source,
                         "overlap": [left, right] if not group and left < right else None,
                         "gap": max(0, left-right) if not group else None,
                         "group": a.group if group else None})

    for rows in _buckets(clips, "source").values():
        # Forward: every interval with an earlier cross-split neighbour gets a witness.
        best = {}
        for clip in sorted(rows, key=lambda c: (windows[c.id][0], c.id)):
            start, end = windows[clip.id]
            for other in best.values():
                if windows[other.id][1] + policy.embargo > start:
                    witness(other, clip)
            if clip.split not in best or end > windows[best[clip.split].id][1]:
                best[clip.split] = clip
        # Reverse: also mark every earlier interval, including those hidden by a longer one.
        best = {}
        for clip in sorted(rows, key=lambda c: (-windows[c.id][0], c.id)):
            start, end = windows[clip.id]
            for other in best.values():
                if windows[other.id][0] < end + policy.embargo:
                    witness(clip, other)
            if clip.split not in best or start < windows[best[clip.split].id][0]:
                best[clip.split] = clip
    if policy.isolate_groups:
        for rows in _buckets(clips, "group").values():
            representatives = {}
            for clip in rows:
                representatives.setdefault(clip.split, clip)
            if len(representatives) > 1:
                for clip in rows:
                    for other in representatives.values():
                        witness(clip, other, group=True)
    counts = defaultdict(lambda: {"clips": 0, "clip_frames": 0, "affected": 0})
    for c in clips:
        counts[c.split]["clips"] += 1
        counts[c.split]["clip_frames"] += c.stop - c.start
        counts[c.split]["affected"] += c.id in affected
    warnings = []
    if len(counts) < 2:
        warnings.append("Only one split is present; no held-out evaluation was checked.")
    if len(evidence) >= max_witnesses and witness_visits > len(evidence):
        warnings.append("Evidence is capped or repeated; affected-clip detection remains complete.")
    return {"schema_version": 1, "status": "conflicts" if affected else "clear",
            "fingerprint": fingerprint(clips, policy), "policy": policy.to_dict(),
            "summary": {"clips": len(clips), "sources": len({c.source for c in clips}),
                        "affected_clips": len(affected), "splits": dict(sorted(counts.items()))},
            "affected_ids": sorted(affected), "witnesses": evidence,
            "evidence_limit": max_witnesses, "warnings": warnings,
            "scope": "Declared source/frame and optional group boundaries only; no content similarity or policy evaluation."}


class _Union:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}
        self.size = {i: 1 for i in self.parent}

    def find(self, x):
        while x != self.parent[x]:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        if self.size[a] < self.size[b]:
            a, b = b, a
        self.parent[b] = a
        self.size[a] += self.size[b]


def plan(clips, ratios=None, policy=Policy(), unit="source", seed=0):
    """Reassign entire components; never delete frames or mutate input records."""
    clips = sorted(validate(list(clips), policy), key=lambda c: c.id)
    ratios = {"train": 0.8, "validation": 0.2} if ratios is None else ratios
    if not isinstance(ratios, dict) or not 2 <= len(ratios) <= 16:
        raise ManifestError("ratios must contain 2 to 16 split names")
    from .model import label
    for name, value in ratios.items():
        label(name, "split")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ManifestError("ratios must be finite positive numbers")
    if not math.isclose(sum(ratios.values()), 1.0, abs_tol=1e-9):
        raise ManifestError("ratios must sum to 1")
    integer(seed, "seed")
    if unit not in ("source", "overlap"):
        raise ManifestError("unit must be source or overlap")
    uf = _Union(c.id for c in clips)
    for rows in _buckets(clips, "source").values():
        rows.sort(key=lambda c: (policy.window(c)[0], c.id))
        furthest = rows[0]
        for c in rows[1:]:
            if unit == "source" or policy.window(c)[0] < policy.window(furthest)[1] + policy.embargo:
                uf.join(furthest.id, c.id)
            if policy.window(c)[1] > policy.window(furthest)[1]:
                furthest = c
    if policy.isolate_groups:
        for rows in _buckets(clips, "group").values():
            for c in rows[1:]:
                uf.join(rows[0].id, c.id)
    components = defaultdict(list)
    for c in clips:
        components[uf.find(c.id)].append(c)
    if len(components) < len(ratios):
        raise ManifestError(f"only {len(components)} independent components for {len(ratios)} splits; "
                            "collect more independent sources or request fewer splits")
    total = sum(c.stop-c.start for c in clips)
    loads = {s: 0 for s in sorted(ratios)}
    targets = {s: total*ratios[s] for s in loads}
    def tie(rows):
        return hashlib.sha256((str(seed) + "\0" + "\0".join(c.id for c in rows)).encode()).hexdigest()
    components = sorted(components.values(), key=lambda rows: (-sum(c.stop-c.start for c in rows), tie(rows)))
    assignments = {}
    for i, rows in enumerate(components):
        weight = sum(c.stop-c.start for c in rows)
        empty = [s for s in loads if loads[s] == 0]
        candidates = empty if len(components)-i == len(empty) else list(loads)
        chosen = min(candidates, key=lambda s: ((loads[s]+weight-targets[s])**2 -
                                              (loads[s]-targets[s])**2, s))
        loads[chosen] += weight
        assignments.update({c.id: chosen for c in rows})
    planned = [replace(c, split=assignments[c.id]) for c in clips]
    verification = audit(planned, policy)
    if verification["status"] != "clear":
        raise RuntimeError("internal error: split plan failed its own audit")
    tasks = defaultdict(set)
    for c in planned:
        if c.task:
            tasks[c.task].add(c.split)
    missing = {task: sorted(set(ratios)-present) for task, present in sorted(tasks.items())
               if set(ratios)-present}
    return planned, {"schema_version": 1, "input_fingerprint": fingerprint(clips, policy),
                     "output_fingerprint": verification["fingerprint"], "unit": unit, "seed": seed,
                     "policy": policy.to_dict(), "components": len(components), "target_ratios": ratios,
                     "actual_ratios": {s: loads[s]/total for s in loads},
                     "missing_task_coverage": missing, "verification": verification,
                     "note": "Greedy balance by summed clip frames, not unique frames. Ratios are approximate. "
                             "No stratification, chronology guarantee, or model-quality guarantee."}
