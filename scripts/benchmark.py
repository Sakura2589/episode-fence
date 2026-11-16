"""Reproducible synthetic scale smoke check; no third-party dependencies."""
from pathlib import Path
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from episode_fence import Clip, Policy, audit

rows = [Clip(str(i), f"s{i//100}", i%100*10, i%100*10+8, 1000,
             "train" if i%2 == 0 else "validation") for i in range(100_000)]
started = time.perf_counter()
result = audit(rows, Policy(future=4))
print(json.dumps({"clips": len(rows), "affected": result["summary"]["affected_clips"],
                  "witnesses": len(result["witnesses"]),
                  "seconds": round(time.perf_counter()-started, 3)}, indent=2))
