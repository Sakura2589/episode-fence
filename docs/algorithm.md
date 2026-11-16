# Detection and planning

## Detection

Two clips conflict if their split labels differ and either:

1. They share a source and their effective read windows overlap, or the gap is less than embargo.
2. Group isolation is enabled and their group labels match.

We detect affected clips without enumerating all conflicting pairs:

- For each source, sort intervals by start. A forward sweep stores the furthest-reaching interval for each split. A clip with an earlier conflicting neighbour is marked.
- Sweep in descending **start** order, retaining the nearest later start for each split. This marks earlier clips whose later neighbours were hidden by a longer same-split interval during the first pass.
- For group isolation, keep one representative per split per group and mark every member of groups that span splits.

Both directions are necessary. An interval contained by another same-split interval must still be marked when either conflicts with a third clip.

At most two interval sweeps visit N × S candidates, where N is clips and S is split labels (<=16). Sorting is O(N log N). Group work is O(N × S). Memory is O(N + W), where W is the evidence cap. Affected-clip coverage is complete within the declared contract. Witnesses are **representative, not an exhaustive pair count**.

The engine stores the first W unique witnesses in deterministic traversal order (default 200). Hitting that cap does not change the outcome or affected IDs. A warning may also occur when repeated witness visits exceed the cap; it is not a count of omitted unique pairs.

Reason categories:
- raw-overlap: clip anchor ranges overlap;
- window-overlap: only the expanded windows overlap;
- embargo: no frames overlap, but the requested gap is violated;
- group: the declared group occurs in different splits.

## Planning

Planning ignores existing split assignments and creates a new evaluation split.

1. Build a disjoint-set forest. Default unit=source joins every clip from each physical recording. unit=overlap joins overlapping/too-close expanded windows instead.
2. Join group members when group isolation is enabled. Joins are transitive across sources and groups.
3. Sort connected components by descending summed clip length, with a seeded SHA-256 tie-break.
4. Assign each entire component to the split minimizing the increase in squared error from the requested frame-count targets. Reserve the remaining components for empty splits when necessary.
5. Re-run the audit with the identical policy. Return only if it is clear.

There must be at least as many independent components as requested splits. Otherwise planning fails with exit 2. Every positive target receives a component, even if the resulting ratio is poor.

The same input records, seed, policy, unit, and ratios produce the same output regardless of input order. The seed only breaks equal-size component ties.

This is a greedy heuristic, **not** an optimal allocator. Weight is the sum of raw clip lengths; repeated camera views count multiple times. Ratios are approximate and may be far from targets for large components. Task coverage is reported but not optimized. No chronological ordering, stratification, preservation of the original holdout, or temporal independence claim is made.

## Test strategy

Randomized audits are compared with an independent quadratic all-pairs oracle. Randomized plans are independently checked for pair conflicts and group violations. Regression tests cover half-open endpoints, exact embargo gaps, hidden nested intervals, source clipping, and transitive group joins.

These tests validate implementation invariants, not the truth of user-provided provenance or improved robot performance.
