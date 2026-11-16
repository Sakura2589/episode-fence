"""Self-contained, escaped HTML with source-coordinate timelines."""
from collections import defaultdict
from html import escape
from importlib.resources import files
import json
from .model import Policy

COLORS = ["#196c59", "#da7747", "#5974be", "#9374aa", "#aa8d25", "#4a8494"]


def text_report(report):
    s = report["summary"]
    lines = [f"EpisodeFence | {report['status'].upper()}",
             f"{s['affected_clips']} / {s['clips']} clips cross a declared split boundary",
             f"{s['sources']} physical sources | {len(s['splits'])} splits"]
    for e in report["witnesses"]:
        detail = f"frames [{e['overlap'][0]}, {e['overlap'][1]})" if e["overlap"] else (
            f"group {e['group']}" if e["kind"] == "group" else f"gap {e['gap']} frames")
        lines.append(f"  {e['kind']}: {e['a']} <-> {e['b']} | {detail}")
    lines.extend("NOTE: " + x for x in report["warnings"])
    lines.append(report["scope"])
    return "\n".join(lines) + "\n"


def markdown_report(report):
    # HTML escape plus pipe escaping prevents table/HTML injection in generated summaries.
    safe = lambda x: escape(str(x)).replace("|", "&#124;").replace("\n", " ")
    s = report["summary"]
    rows = ["# EpisodeFence", "", f"**{report['status'].upper()}** — {s['affected_clips']} of {s['clips']} clips affected.",
            "", "| Kind | Clip A | Clip B | Shared frames / gap |", "|---|---|---|---|"]
    for e in report["witnesses"]:
        detail = e["overlap"] if e["overlap"] else f"gap={e['gap']}" if e["kind"] != "group" else e["group"]
        rows.append("| " + " | ".join(safe(x) for x in (e["kind"], e["a"], e["b"], detail)) + " |")
    rows += ["", safe(report["scope"])]
    rows += ["", *[f"- {safe(w)}" for w in report["warnings"]]]
    return "\n".join(rows) + "\n"


def html_report(clips, report, title="Split boundary audit"):
    esc = lambda x: escape(str(x), quote=True)
    css = files("episode_fence").joinpath("report.css").read_text(encoding="utf-8")
    policy = Policy(**report["policy"])
    s = report["summary"]
    colors = {split: COLORS[i % len(COLORS)] for i, split in enumerate(s["splits"])}
    affected = set(report["affected_ids"])
    sources = defaultdict(list)
    for c in sorted(clips, key=lambda c: (c.source, c.start, c.id)):
        sources[c.source].append(c)
    blocks = []
    # Put affected sources first. Rendering caps never affect audit coverage.
    ordered = sorted(sources.items(), key=lambda item: (not any(c.id in affected for c in item[1]), item[0]))
    for source, all_rows in ordered[:30]:
        rows = all_rows[:80]
        width, x0, scale = 670, 270, 670 / rows[0].source_frames
        svg = [f'<svg viewBox="0 0 980 {len(rows)*36+34}" role="img" aria-label="Frame timeline for {esc(source)}">']
        for tick in range(5):
            x = x0 + tick*width/4
            frame = round(rows[0].source_frames*tick/4)
            svg.append(f'<line x1="{x}" x2="{x}" y1="24" y2="{len(rows)*36+22}" stroke="#e4e9e3"/>'
                       f'<text x="{x}" y="15" text-anchor="middle">{frame}</text>')
        for i, c in enumerate(rows):
            y = i*36+30
            start, stop = policy.window(c)
            color = colors[c.split]
            label = c.id if len(c.id) <= 25 else c.id[:22]+"..."
            svg.append(f'<text x="0" y="{y+13}">{esc(label)}<title>{esc(c.id)} · {esc(c.split)}</title></text>')
            svg.append(f'<rect x="{x0+start*scale:.3f}" y="{y}" width="{max(.5,(stop-start)*scale):.3f}" '
                       f'height="20" rx="3" fill="{color}" opacity=".20"/>')
            svg.append(f'<rect x="{x0+c.start*scale:.3f}" y="{y+4}" width="{max(.5,(c.stop-c.start)*scale):.3f}" '
                       f'height="12" rx="2" fill="{color}"><title>{esc(c.id)} · {esc(c.split)} · '
                       f'raw [{c.start}, {c.stop}) · window [{start}, {stop})</title></rect>')
            if c.id in affected:
                svg.append(f'<circle cx="960" cy="{y+10}" r="4" fill="#ae3e32"><title>Cross-split conflict</title></circle>')
        svg.append("</svg>")
        bad = any(c.id in affected for c in all_rows)
        note = f'<p class="muted">Showing 80 of {len(all_rows)} clips in this source.</p>' if len(all_rows)>80 else ""
        blocks.append(f'<details class="source {"" if bad else "clean"}" open><summary>{esc(source)} '
                      f'<small> / {len(all_rows)} clips</small></summary><div class="plot">{"".join(svg)}</div>{note}</details>')
    table_rows = []
    for e in report["witnesses"]:
        detail = f"[{e['overlap'][0]}, {e['overlap'][1]})" if e["overlap"] else (
            f"group: {e['group']}" if e["kind"] == "group" else f"gap: {e['gap']} frames")
        table_rows.append(f'<tr><td><span class="badge">{esc(e["kind"])}</span></td><td><code>{esc(e["a"])}'
                          f'</code><br><small>{esc(e["splits"][0])}</small></td><td><code>{esc(e["b"])}</code>'
                          f'<br><small>{esc(e["splits"][1])}</small></td><td><code>{esc(detail)}</code></td></tr>')
    if not table_rows:
        table_rows = ['<tr><td colspan="4">No stored conflict witnesses. See affected count and evidence limit.</td></tr>']
    legend = "".join(f'<span><i class="dot" style="background:{color}"></i>{esc(name)}</span>' for name,color in colors.items())
    notices = "".join(f'<p class="notice">{esc(w)}</p>' for w in report["warnings"])
    split_rows = "".join(f'<tr><td>{esc(name)}</td><td>{v["clips"]}</td><td>{v["clip_frames"]}</td><td>{v["affected"]}</td></tr>'
                         for name,v in s["splits"].items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>EpisodeFence — {esc(title)}</title><style>{css}</style></head>
<body><main><header><div><div class="eyebrow">EpisodeFence / dataset observability</div>
<h1>Trust the boundary.</h1><p>{esc(title)}. Follow the frames your model actually reads, across every declared split.</p></div>
<span class="status {'bad' if affected else ''}">{'Conflicts found' if affected else 'No declared conflicts'}</span></header>
<div class="cards"><div class="card"><small>Affected clips</small><b class="number">{s['affected_clips']}</b></div>
<div class="card"><small>Total clips</small><b class="number">{s['clips']}</b></div>
<div class="card"><small>Physical sources</small><b class="number">{s['sources']}</b></div>
<div class="card"><small>Dataset splits</small><b class="number">{len(s['splits'])}</b></div></div>
<div class="policy">HISTORY {policy.history} frames &nbsp; / &nbsp; FUTURE {policy.future} frames &nbsp; / &nbsp;
EMBARGO {policy.embargo} frames &nbsp; / &nbsp; GROUP ISOLATION {'ON' if policy.isolate_groups else 'OFF'}</div>
{notices}<h2>See where the splits meet</h2><p class="muted">Solid bars: declared clips. Pale bars: full read windows, clipped to the physical source.
Red dots: affected clips. Intervals exclude their stop frame. Hover a bar for exact coordinates.</p>
<div class="legend">{legend}</div><input id="conflicts-only" type="checkbox"> <label class="view-toggle" for="conflicts-only">Show only sources with conflicts</label>
<div class="timelines">{''.join(blocks)}</div><p class="muted">Displaying {min(30,len(sources))} of {len(sources)} sources; up to 80 clips per source. All clips are audited.</p>
<h2>Evidence you can reproduce</h2><p class="muted">Representative witnesses, not an exhaustive list of pairs. Complete affected IDs are available in JSON.</p>
<div class="table-wrap"><table><thead><tr><th>Reason</th><th>Clip A</th><th>Clip B</th><th>Evidence</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<h2>Split inventory</h2><div class="table-wrap"><table><thead><tr><th>Split</th><th>Clips</th><th>Clip frames*</th><th>Affected</th></tr></thead><tbody>{split_rows}</tbody></table></div>
<p class="muted">*Sum of clip lengths; overlapping clips and camera views are counted separately.</p>
<footer><b>Scope, not a certification.</b> {esc(report['scope'])} A clear result does not establish statistical independence,
detect mislabeled provenance, or measure robot success. No dataset contents were uploaded.<br>
Manifest + policy SHA-256: <code>{report['fingerprint']}</code><br>EpisodeFence 0.1.0 · offline report · no external assets or scripts</footer>
</main></body></html>"""
