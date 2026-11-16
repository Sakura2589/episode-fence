import random
from dataclasses import replace
import unittest
from episode_fence import Clip, Policy, audit, plan, ManifestError
from episode_fence.io import parse_manifest, manifest_text, decode, convert_episodes


def clip(id="a", source="s", start=0, stop=10, frames=100, split="train", group=""):
    return Clip(id, source, start, stop, frames, split, group=group)


def oracle(rows, policy):
    affected = set()
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            if a.split == b.split:
                continue
            a0, a1 = policy.window(a)
            b0, b1 = policy.window(b)
            conflict = a.source == b.source and max(a0,b0) < min(a1,b1)+policy.embargo
            conflict |= policy.isolate_groups and a.group == b.group
            if conflict:
                affected.update((a.id,b.id))
    return affected


class IntervalTests(unittest.TestCase):
    def test_half_open_and_embargo_exact_boundary(self):
        rows = [clip(), clip("b", start=10, stop=20, split="val")]
        self.assertEqual(audit(rows)["status"], "clear")
        self.assertEqual(audit(rows, Policy(embargo=1))["status"], "conflicts")
        rows[1] = replace(rows[1], start=11)
        self.assertEqual(audit(rows, Policy(embargo=1))["status"], "clear")

    def test_future_and_history_witness(self):
        rows = [clip(), clip("b", start=15, stop=25, split="val")]
        result = audit(rows, Policy(history=2, future=4))
        self.assertEqual(result["affected_ids"], ["a", "b"])
        self.assertEqual(result["witnesses"][0]["overlap"], [13,14])
        self.assertEqual(result["witnesses"][0]["kind"], "window-overlap")

    def test_windows_clamped_to_source(self):
        self.assertEqual(Policy(1000,1000).window(clip()), (0,100))

    def test_nested_intervals_are_all_detected(self):
        rows = [clip("long", stop=90)] + [clip(str(i), start=i, stop=i+1) for i in range(1,30)]
        rows.append(clip("v", start=0, stop=90, split="val"))
        self.assertEqual(audit(rows)["summary"]["affected_clips"], len(rows))

    def test_contained_later_neighbor_marks_both_outer_intervals(self):
        rows=[clip("a",start=90,stop=100,split="val"),
              clip("b",start=91,stop=100,split="val"),clip("c",start=92,stop=99)]
        self.assertEqual(audit(rows)["affected_ids"],["a","b","c"])

    def test_different_sources_and_same_split_do_not_conflict(self):
        self.assertEqual(audit([clip(), clip("b", source="t", split="val")])["status"], "clear")
        self.assertEqual(audit([clip(), clip("b")])["status"], "clear")

    def test_groups_link_sources(self):
        rows = [clip(group="session"), clip("b", source="t", split="val", group="session")]
        self.assertEqual(audit(rows, Policy(isolate_groups=True))["summary"]["affected_clips"], 2)

    def test_witness_cap_does_not_hide_affected_clips(self):
        rows = [clip(), clip("b", split="val")]
        report = audit(rows, max_witnesses=0)
        self.assertEqual(report["witnesses"], [])
        self.assertEqual(report["affected_ids"], ["a","b"])

    def test_randomized_against_exhaustive_oracle(self):
        rng = random.Random(173)
        for _ in range(300):
            rows = []
            for i in range(rng.randint(2,60)):
                start = rng.randrange(99)
                rows.append(clip(str(i), source=str(rng.randrange(4)), start=start,
                                 stop=rng.randint(start+1,100), split=rng.choice(["train","val","test"]),
                                 group=str(rng.randrange(5))))
            policy = Policy(rng.randrange(10), rng.randrange(10), rng.randrange(5), rng.choice([True,False]))
            self.assertEqual(set(audit(rows,policy,max_witnesses=3)["affected_ids"]), oracle(rows,policy))

    def test_fingerprint_order_invariant_policy_sensitive(self):
        rows = [clip(), clip("b", source="t", split="val")]
        self.assertEqual(audit(rows)["fingerprint"], audit(rows[::-1])["fingerprint"])
        self.assertNotEqual(audit(rows)["fingerprint"], audit(rows,Policy(future=1))["fingerprint"])

    def test_single_split_warning(self):
        self.assertIn("Only one split",audit([clip()])["warnings"][0])


class PlanTests(unittest.TestCase):
    def test_plan_is_deterministic_and_preserves_data(self):
        rows = [clip(str(i),source=str(i//2),start=0,stop=10+i,split="old") for i in range(20)]
        a, report = plan(rows,seed=42)
        b, _ = plan(rows[::-1],seed=42)
        self.assertEqual(a,b)
        self.assertEqual(report["verification"]["status"],"clear")
        self.assertEqual({x.split for x in a},{"train","validation"})
        self.assertEqual([replace(x,split="old") for x in a],sorted(rows,key=lambda c:c.id))

    def test_transitive_group_component(self):
        rows = [clip("a",group="g"),clip("b",group="h"),
                clip("c",source="t",group="h"),clip("d",source="u",group="j")]
        fixed,_ = plan(rows,policy=Policy(isolate_groups=True))
        assignment={c.id:c.split for c in fixed}
        self.assertEqual(assignment["a"],assignment["c"])
        self.assertNotEqual(assignment["a"],assignment["d"])

    def test_impossible_plan_fails(self):
        with self.assertRaisesRegex(ManifestError,"independent components"):
            plan([clip(),clip("b")])

    def test_overlap_mode_respects_expanded_windows(self):
        rows=[clip(),clip("b",start=20,stop=30),clip("c",start=70,stop=80)]
        fixed,details=plan(rows,policy=Policy(future=15),unit="overlap")
        self.assertEqual(fixed[0].split,fixed[1].split)
        self.assertEqual(details["components"],2)
        self.assertEqual(oracle(fixed,Policy(future=15)),set())

    def test_invalid_ratios(self):
        for ratios in ({}, {"a":.5,"b":.4}, {"a":float("nan"),"b":1}, {"a":0,"b":1}):
            with self.assertRaises(ManifestError):
                plan([clip(),clip("b",source="t")],ratios)

    def test_randomized_plan_passes_oracle(self):
        rng=random.Random(20)
        for _ in range(100):
            rows=[clip(str(i),source=str(i//3),start=rng.randrange(40),stop=rng.randrange(50,100),
                       group=str(i//6)) for i in range(36)]
            policy=Policy(3,7,2,True)
            fixed,_=plan(rows,{"train":.6,"val":.2,"test":.2},policy,unit="overlap")
            self.assertEqual(oracle(fixed,policy),set())

    def test_task_coverage_is_not_silently_promised(self):
        rows=[replace(clip("a"),task="rare"),clip("b",source="b")]
        _,details=plan(rows)
        self.assertIn("rare",details["missing_task_coverage"])


class InputTests(unittest.TestCase):
    def test_jsonl_round_trip(self):
        rows=[clip(),clip("b",source="t")]
        self.assertEqual(parse_manifest(manifest_text(rows)),rows)

    def test_csv(self):
        rows=parse_manifest('id,source,start,stop,source_frames,split\na,s,0,10,100,train\n',"csv")
        self.assertEqual(rows,[clip()])

    def test_invalid_inputs_fail_closed(self):
        for text in ('', '{"id":"x"}', '[]', '{"id":"a","id":"b"}', '{"x":NaN}'):
            with self.assertRaises(ManifestError):
                parse_manifest(text)

    def test_invalid_intervals(self):
        for args in ({"start":True},{"stop":0},{"frames":5},{"start":-1}):
            with self.assertRaises(ManifestError):
                clip(**args)

    def test_duplicate_ids_and_source_lengths(self):
        for rows in ([clip(),clip()], [clip(),clip("b",frames=200)]):
            with self.assertRaises(ManifestError):
                audit(rows)

    def test_group_policy_requires_metadata(self):
        with self.assertRaises(ManifestError):
            audit([clip()],Policy(isolate_groups=True))

    def test_converter_provenance(self):
        rows=[{"episode_index":0,"length":10,"tasks":["pick"]}]
        result=convert_episodes(rows,"owner/demo",{"0":"validation"},
                                {"0":{"source":"original","offset":20,"source_frames":100,"group":"day1"}},1)
        self.assertEqual((result[0].source,result[0].start,result[0].stop),("original",20,30))

    def test_converter_rejects_incomplete_or_ambiguous_maps(self):
        rows=[{"episode_index":0,"length":10}]
        for mapping in ({},{"0":"train","1":"val"}):
            with self.assertRaises(ManifestError):
                convert_episodes(rows,"demo",mapping)
        with self.assertRaises(ManifestError):
            convert_episodes(rows,"demo",expected=2)
        with self.assertRaises(ManifestError):
            convert_episodes(rows*2,"demo")

if __name__ == "__main__":
    unittest.main()
