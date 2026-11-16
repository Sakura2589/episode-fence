# Manifest contract (schema 1)

A UTF-8 JSONL file, one object per line, or CSV with a header. Unknown fields, duplicate IDs, duplicate JSON keys, invalid integers and inconsistent source lengths are errors. Blank JSONL lines are ignored. Input files are bounded to 64 MiB. Audit accepts at most 100,000 clips and 16 split labels.

| Field | Required | Meaning |
|---|---|---|
| id | yes | Unique clip identity, <=512 characters. |
| source | yes | Global identity of the original physical recording. |
| start | yes | First anchor frame, included. |
| stop | yes | Last anchor frame + 1, excluded. |
| source_frames | yes | Total number of frames in this original recording. |
| split | yes | Explicit split label; labels are case-sensitive. |
| task | no | Optional task label for coverage diagnostics. |
| group | no | Optional group ID for session/scene/operator holdout. |

Integers must satisfy `0 <= start < stop <= source_frames <= 2**53-1`. Booleans are not integers. Strings cannot contain control characters. Every clip with the same source must declare the same source_frames.

## Read windows

For a clip with anchor interval [start, stop), a global policy expands it to:

```text
read_start = max(0, start - history)
read_stop  = min(source_frames, stop + future)
```

With 8 past observations, set history=8. With an action sequence of length H containing the current action, set future=H-1. If your loader already exports actual read ranges, set both to zero.

Use the same frame clock for all copies of a recording. Alternate cameras need time alignment. Resampled or sped-up clips need their coordinates mapped back to the original clock; the tool does not do that conversion. Sparse offsets are represented by their contiguous envelope, which may over-report conflicts. Per-clip horizons are not supported in v0.1; encode precomputed read intervals to handle heterogeneous windows.

LeRobot pads/clamps at episode boundaries. Do not declare a longer physical read window when your loader clamps inside the clip. Padded copies of a boundary frame do not create new source frames.

## Source and group identities

A source identifies one physical take, **not** a file, MP4 shard, camera, dataset name, or task. Multiple episodes can share a v3 MP4 shard without sharing source frames. Conversely, two files can contain copies of one original take.

Set source IDs from collection provenance. Prefix unrelated IDs with a collection namespace. If two converted datasets contain slices of the same take, give those records the same source ID and original offsets.

By default, different sources are independent for this check. Use `--isolate-groups` to keep every declared session/operator/scene group within one split. In that mode every record requires a non-empty group. This is a user-declared holdout policy; matching groups are not evidence of byte-identical data. Compound group policies can be precomputed externally.

## Embargo

An embargo of N requires at least N unused frames between effective read windows in different splits from the same source. With embargo=0, touching half-open windows are allowed. With embargo=1, [0,10) and [10,20) conflict, but [0,10) and [11,20) do not.

An embargo does not establish statistical independence; choose a gap appropriate to your dynamics.

## Output semantics

JSON reports contain:
- schema_version, policy, and a SHA-256 of canonical manifest content plus policy;
- complete sorted affected_ids and per-split clip/frame counts;
- bounded representative witnesses, with reason, clip IDs and overlap/gap evidence;
- warnings and scope.

The fingerprint is a reproducibility identifier, not an authenticity signature. Files with the same records in different orders produce the same fingerprint.

All file writes are local. Existing outputs require --force. Manifests contain provenance labels, not video bytes, but these labels may still be sensitive.
