"""Command line entry point. Exit 0 clear, 1 conflicts, 2 invalid input."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .model import Policy, ManifestError
from .io import read_manifest, manifest_text, import_lerobot, decode, read_text
from .engine import audit, plan
from .report import text_report, markdown_report, html_report


def write_output(path, text, force=False, protected=()):
    target = Path(path)
    if target.resolve() in {Path(p).resolve() for p in protected}:
        raise ManifestError("output must not replace an input file")
    if not target.parent.is_dir():
        raise ManifestError(f"output parent does not exist: {target.parent}")
    if not force:
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        return
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=target.parent, delete=False) as stream:
            name = stream.name
            stream.write(text)
        os.replace(name, target)
        name = None
    finally:
        if name:
            Path(name).unlink(missing_ok=True)


def _policy(parser):
    parser.add_argument("--history", type=int, default=0, help="additional frames read before each clip")
    parser.add_argument("--future", type=int, default=0, help="additional frames read after each clip (H-1 for H actions)")
    parser.add_argument("--embargo", type=int, default=0, help="minimum gap between effective windows")
    parser.add_argument("--isolate-groups", action="store_true", help="keep each declared group inside one split")


def parser():
    p = argparse.ArgumentParser(prog="episode-fence", description="Find robot dataset split leakage in source frame coordinates.")
    p.add_argument("--version", action="version", version="EpisodeFence 0.1.0")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("audit", help="check a JSONL/CSV clip manifest")
    a.add_argument("manifest")
    _policy(a)
    a.add_argument("--format", choices=("text", "json", "html", "markdown"), default="text")
    a.add_argument("--max-witnesses", type=int, default=200)
    a.add_argument("-o", "--output")
    a.add_argument("--force", action="store_true")
    a = sub.add_parser("plan", help="generate and verify a new split assignment")
    a.add_argument("manifest")
    _policy(a)
    a.add_argument("--ratios", default="train=0.8,validation=0.2")
    a.add_argument("--unit", choices=("source", "overlap"), default="source")
    a.add_argument("--seed", type=int, default=0)
    a.add_argument("-o", "--output", required=True, help="new JSONL manifest")
    a.add_argument("--report", help="optional JSON planning diagnostics")
    a.add_argument("--force", action="store_true")
    a = sub.add_parser("import-lerobot", help="import local v2.x/v3.0 episode metadata")
    a.add_argument("root")
    a.add_argument("--dataset-id", required=True, help="stable namespace, e.g. owner/dataset")
    a.add_argument("--split-map", help="JSON object mapping episode indices to split labels")
    a.add_argument("--provenance", help="JSON object mapping indices to original source/offset/length")
    a.add_argument("-o", "--output", required=True)
    a.add_argument("--force", action="store_true")
    a = sub.add_parser("demo", help="write synthetic before/after reports; no downloads")
    a.add_argument("-o", "--output", default="episode-fence-demo", help="new directory (must not exist)")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "demo":
            from .demo import demo_clips
            clips = demo_clips()
            policy = Policy(history=8, future=24)
            fixed, diagnostics = plan(clips, policy=policy)
            before, after = audit(clips, policy), audit(fixed, policy)
            payloads = {
                "clips.jsonl": manifest_text(clips), "planned.jsonl": manifest_text(fixed),
                "before.html": html_report(clips, before, "Synthetic demo / before"),
                "after.html": html_report(fixed, after, "Synthetic demo / after"),
                "before.json": json.dumps(before, indent=2), "plan.json": json.dumps(diagnostics, indent=2)}
            directory = Path(args.output)
            directory.mkdir(parents=False, exist_ok=False)
            for name, content in payloads.items():
                write_output(directory/name, content)
            print(f"Demo: {before['summary']['affected_clips']} affected clips -> {after['summary']['affected_clips']}")
            print(f"Open {(directory/'before.html').resolve()}")
            return 0
        if args.command == "import-lerobot":
            clips = import_lerobot(args.root, args.dataset_id,
                                   decode(read_text(args.split_map)) if args.split_map else None,
                                   decode(read_text(args.provenance)) if args.provenance else None)
            root = Path(args.root).resolve()
            if Path(args.output).resolve().is_relative_to(root):
                raise ManifestError("import output must be outside the source dataset")
            write_output(args.output, manifest_text(clips), args.force,
                         [p for p in (args.split_map, args.provenance) if p])
            print(f"Imported {len(clips)} episodes. Review source IDs before combining dataset exports.")
            return 0
        clips = read_manifest(args.manifest)
        policy = Policy(args.history, args.future, args.embargo, args.isolate_groups)
        if args.command == "audit":
            report = audit(clips, policy, args.max_witnesses)
            content = {"text": lambda: text_report(report),
                       "markdown": lambda: markdown_report(report),
                       "json": lambda: json.dumps(report, indent=2, ensure_ascii=False)+"\n",
                       "html": lambda: html_report(clips, report)}[args.format]()
            if args.output:
                write_output(args.output, content, args.force, [args.manifest])
                print(text_report(report), end="")
            else:
                print(content, end="")
            return 1 if report["status"] == "conflicts" else 0
        ratios = {}
        for part in args.ratios.split(","):
            name, value = part.split("=", 1)
            name = name.strip()
            if name in ratios:
                raise ManifestError(f"duplicate ratio: {name}")
            ratios[name] = float(value)
        planned, diagnostics = plan(clips, ratios, policy, args.unit, args.seed)
        if args.report:
            if Path(args.report).resolve() in (Path(args.output).resolve(), Path(args.manifest).resolve()):
                raise ManifestError("manifest, output and report paths must differ")
            if Path(args.report).exists() and not args.force:
                raise ManifestError(f"report already exists: {args.report}")
            if not Path(args.report).parent.is_dir():
                raise ManifestError("report parent directory must exist")
        write_output(args.output, manifest_text(planned), args.force, [args.manifest])
        if args.report:
            write_output(args.report, json.dumps(diagnostics, indent=2)+"\n", args.force, [args.manifest])
        print(f"Planned {len(planned)} clips in {diagnostics['components']} components; verified no declared conflicts.")
        print("Actual clip-frame ratios: " + ", ".join(f"{k}={v:.3f}" for k,v in diagnostics["actual_ratios"].items()))
        if diagnostics["missing_task_coverage"]:
            print("NOTE: some tasks are absent from some splits; inspect the planning report.")
        return 0
    except (OSError, ManifestError, ValueError, TypeError) as exc:
        print(f"episode-fence: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
