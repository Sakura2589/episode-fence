# LeRobot integration

The adapter reads local episode metadata only:

- v2.x: meta/info.json and meta/episodes.jsonl;
- v3.0: meta/info.json and all Parquet shards under meta/episodes/.

v3.0 needs PyArrow: `python -m pip install ".[lerobot]"`. No torch, video decoder, Hub token, or network connection is used. Unsupported format versions fail explicitly.

Example:
```sh
python -m episode_fence import-lerobot examples/lerobot-v2 --dataset-id demo/pick --split-map examples/splits.json -o imported.jsonl
python -m episode_fence audit imported.jsonl
```

The adapter reads episode_index, length and optional tasks. It verifies unique episode indices and total_episodes when present. It does not validate Parquet frame rows, video sync, stats, or complete LeRobot compatibility.

## Original datasets

By default source and clip IDs are both `dataset-id::episode-index`. This avoids accidental collisions across unrelated collections. Every complete episode occupies [0,length) and its own source. An audit of disjoint full episodes will be clear by construction, unless group metadata links them.

A split map must cover every episode exactly:
```json
{"0":"train","1":"validation","2":"train"}
```

Without a map, all records are unassigned. This is useful before planning, but it is not a validation split.

## Converted, sliced, or duplicated data

The importer cannot infer that differently named datasets contain the same physical recording. Supply a complete provenance object for each export:
```json
{
  "0":{"source":"lab/day1/take9","offset":0,"source_frames":600,"group":"day1"},
  "1":{"source":"lab/day1/take9","offset":180,"source_frames":600,"group":"day1"},
  "2":{"source":"lab/day2/take2","offset":0,"source_frames":400,"group":"day2"}
}
```

```sh
episode-fence import-lerobot /data/converted --dataset-id lab/converted --split-map splits.json --provenance provenance.json -o converted.jsonl
episode-fence audit converted.jsonl --isolate-groups
```

Each exported interval is [offset, offset + episode length). Source_frames must describe the **original** take. Same-source copies across exports must share its global ID and frame clock. Concatenate exported JSONL manifests only when clip IDs remain unique and provenance is consistent.

If your converted loader clamps inside the newly created episode, history/future expansion beyond it overestimates the read range. Use zero expansion for full clamped episodes, or construct a manifest of actual read intervals. This adapter is not a claim about LeRobot's training implementation.

## Connect the planned assignment to your loader

EpisodeFence writes manifests, not a modified LeRobot dataset. For whole-episode imports, select the original episode indices whose IDs belong to each planned split and pass those indices to your training/evaluation loader. Keep source metadata and task fields for review. For arbitrary clip manifests, your sampler needs a custom mapping.

Refit normalization statistics using training data as appropriate for your pipeline. EpisodeFence does not check statistics, training state, or evaluation leakage outside frame/group boundaries.
