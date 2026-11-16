"""Bounded local manifests. No network, video decoding, or dataset modification."""
import csv
import json
from pathlib import Path
from .model import Clip, ManifestError, Policy, validate

MAX_BYTES = 64 * 1024 * 1024
FIELDS = ("id", "source", "start", "stop", "source_frames", "split", "task", "group")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(text):
    try:
        return json.loads(text, object_pairs_hook=unique_object,
                          parse_constant=lambda x: (_ for _ in ()).throw(ManifestError(f"invalid number: {x}")))
    except (ValueError, RecursionError) as exc:
        raise ManifestError(f"invalid JSON: {exc}") from exc


def read_text(path):
    path = Path(path)
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ManifestError(f"{path.name}: exceeds 64 MiB limit")
    try:
        return data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise ManifestError(f"{path.name}: expected UTF-8") from exc


def parse_manifest(text, format="jsonl"):
    if format == "csv":
        import io
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ManifestError("CSV requires unique header names")
        rows = []
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ManifestError(f"CSV line {line}: inconsistent column count")
            for key in ("start", "stop", "source_frames"):
                try:
                    if key in row:
                        row[key] = int(row[key])
                except ValueError as exc:
                    raise ManifestError(f"CSV line {line}: {key} must be an integer") from exc
            rows.append((line, row))
    elif format == "jsonl":
        rows = [(i, decode(line)) for i, line in enumerate(text.splitlines(), 1) if line.strip()]
    else:
        raise ManifestError("manifest format must be jsonl or csv")
    clips = []
    for line, row in rows:
        if not isinstance(row, dict):
            raise ManifestError(f"line {line}: expected an object")
        unknown = set(row)-set(FIELDS)
        if unknown:
            raise ManifestError(f"line {line}: unknown fields: {', '.join(sorted(unknown))}")
        try:
            clips.append(Clip(**row))
        except (TypeError, ManifestError) as exc:
            raise ManifestError(f"line {line}: {exc}") from exc
    return validate(clips, Policy())


def read_manifest(path):
    return parse_manifest(read_text(path), "csv" if Path(path).suffix.lower() == ".csv" else "jsonl")


def manifest_text(clips):
    return "".join(json.dumps(c.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for c in clips)


def import_lerobot(root, dataset_id, split_map=None, provenance=None):
    """Read v2.x JSONL or v3.0 episode metadata only; IDs never derive from file names."""
    root = Path(root)
    info = decode(read_text(root/"meta"/"info.json"))
    if not isinstance(info, dict):
        raise ManifestError("meta/info.json must be an object")
    version = info.get("codebase_version", "")
    if not isinstance(version, str):
        raise ManifestError("codebase_version must be a string")
    if version.startswith("v2."):
        rows = [decode(line) for line in read_text(root/"meta"/"episodes.jsonl").splitlines() if line.strip()]
    elif version == "v3.0":
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise ManifestError('v3.0 import needs pyarrow: pip install ".[lerobot]"') from exc
        files = sorted((root/"meta"/"episodes").rglob("*.parquet"))
        if not files:
            raise ManifestError("no meta/episodes/*.parquet metadata found")
        rows = []
        for file in files:
            parquet = pq.ParquetFile(file)
            columns = [c for c in ("episode_index", "length", "tasks") if c in parquet.schema_arrow.names]
            if "episode_index" not in columns or "length" not in columns:
                raise ManifestError(f"{file.name}: missing episode_index or length")
            for batch in parquet.iter_batches(batch_size=4096, columns=columns):
                rows.extend(batch.to_pylist())
                if len(rows) > 100_000:
                    raise ManifestError("limit: 100,000 episodes")
    else:
        raise ManifestError(f"unsupported LeRobot version {version!r}; supported: v2.x and v3.0")
    return convert_episodes(rows, dataset_id, split_map, provenance, info.get("total_episodes"))


def convert_episodes(rows, dataset_id, split_map=None, provenance=None, expected=None):
    from .model import integer, label
    label(dataset_id, "dataset_id")
    if split_map is not None and not isinstance(split_map, dict):
        raise ManifestError("split map must be an object keyed by episode index")
    if provenance is not None and not isinstance(provenance, dict):
        raise ManifestError("provenance must be an object keyed by episode index")
    if expected is not None:
        integer(expected, "total_episodes")
        if expected != len(rows):
            raise ManifestError("episode metadata count differs from total_episodes")
    seen, clips = set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise ManifestError("episode metadata must contain objects")
        index = integer(row.get("episode_index"), "episode_index")
        length = integer(row.get("length"), "length", 1)
        key = str(index)
        if key in seen:
            raise ManifestError(f"duplicate episode_index: {index}")
        seen.add(key)
        if split_map is not None and key not in split_map:
            raise ManifestError(f"split map missing episode {index}")
        if provenance is not None and key not in provenance:
            raise ManifestError(f"provenance missing episode {index}")
        origin = {} if provenance is None else provenance[key]
        if not isinstance(origin, dict) or set(origin)-{"source", "offset", "source_frames", "group"}:
            raise ManifestError(f"invalid provenance for episode {index}")
        if provenance is not None and not {"source", "offset", "source_frames"} <= set(origin):
            raise ManifestError("provenance requires source, offset and source_frames")
        offset = integer(origin.get("offset", 0), "offset")
        tasks = row.get("tasks", [])
        if not isinstance(tasks, list) or not all(isinstance(t, str) for t in tasks):
            raise ManifestError(f"episode {index}: tasks must be a list of strings")
        task = " | ".join(sorted(set(tasks)))
        clips.append(Clip(id=f"{dataset_id}::{index}", source=origin.get("source", f"{dataset_id}::{index}"),
                          start=offset, stop=offset+length, source_frames=origin.get("source_frames", length),
                          split="unassigned" if split_map is None else split_map[key],
                          group=origin.get("group", ""), task=task))
    for name, mapping in (("split map", split_map), ("provenance", provenance)):
        if mapping is not None and set(mapping) != seen:
            raise ManifestError(f"{name} contains unknown episode indices")
    return validate(clips, Policy())
