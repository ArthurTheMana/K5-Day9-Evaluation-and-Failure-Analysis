"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    # TODO M7
    problems = []

    for name, report in (("PR", pr), ("baseline", base)):
        manifest = report.get("manifest", {})
        rows = report.get("rows", [])
        seeds = manifest.get("seeds", [])
        items = manifest.get("items", 0)
        expected = items * len(seeds)
        if len(rows) != expected:
            problems.append(f"{name}: expected {expected} rows, got {len(rows)}")

        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if len(set(pairs)) != len(pairs):
            problems.append(f"{name}: duplicate item/seed pairs")
        if len({item for item, _ in pairs}) != items:
            problems.append(f"{name}: item count differs from manifest")
        if {seed for _, seed in pairs} != set(seeds):
            problems.append(f"{name}: seeds differ from manifest")

        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures present")
        for mid, val in report.get("metrics", {}).items():
            if isinstance(val, (int, float)) and not math.isfinite(val):
                problems.append(f"{name}: non-finite metric {mid}")

    pr_pairs = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_pairs = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_pairs != base_pairs:
        problems.append("PR and baseline have different item/seed pairs")

    # Only code-graded metrics live in each row. Aggregate metrics such as pass_hat_5
    # and cost_per_success are stored at report level instead.
    from lab9.graders import GRADERS
    graded = {m["id"] for m in spec.get("metrics", []) if m["id"] in GRADERS}
    for name, report in (("PR", pr), ("baseline", base)):
        for i, row in enumerate(report.get("rows", [])):
            missing = [mid for mid in graded if row.get(mid) is None]
            if missing:
                problems.append(f"{name}: row {i} missing graded values: {', '.join(sorted(missing))}")
                break

    def item_tags(report):
        tags = {}
        for row in report.get("rows", []):
            item = row.get("item_id")
            value = frozenset(row.get("slices") or [])
            if item in tags and tags[item] != value:
                problems.append(f"inconsistent slice tags for item {item}")
            tags[item] = value
        return tags

    if item_tags(pr) != item_tags(base):
        problems.append("PR slice tags differ from baseline")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def thresholds(kind, entries):
            if kind == "metrics":
                return {m["id"]: m for m in entries}
            return {(m["name"], m["metric"]): m for m in entries}

        for kind in ("metrics", "slices"):
            old = thresholds(kind, base_spec.get(kind, []))
            current = thresholds(kind, spec.get(kind, []))
            for key, prior in old.items():
                if key not in current:
                    problems.append(f"{kind}: removed {key}")
                    continue
                updated = current[key]
                if prior.get("blocking") and not updated.get("blocking"):
                    problems.append(f"{kind}: blocking disabled for {key}")
                old_limits = prior.get("threshold", {}) if kind == "metrics" else prior
                new_limits = updated.get("threshold", {}) if kind == "metrics" else updated
                for bound in ("min", "max", "max_increase"):
                    if bound not in old_limits:
                        continue
                    if bound not in new_limits:
                        problems.append(f"{kind}: removed {bound} for {key}")
                    elif (bound == "min" and new_limits[bound] < old_limits[bound]) or (
                          bound != "min" and new_limits[bound] > old_limits[bound]):
                        problems.append(f"{kind}: loosened {bound} for {key}")
                if old_limits.get("no_significant_drop") and not new_limits.get("no_significant_drop"):
                    problems.append(f"{kind}: removed no_significant_drop for {key}")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    # TODO M5
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for item in spec.get("slices", []):
        name, metric = item["name"], item["metric"]
        sid = f"slice:{name}/{metric}"
        pr_values = per_item(pr, metric, slice_name=name)
        base_values = per_item(base, metric, slice_name=name)
        threshold = {k: item[k] for k in ("min", "no_significant_drop") if k in item}
        verdict, note = "ok", ""
        value = sum(pr_values.values()) / len(pr_values) if pr_values else None

        if value is None:
            verdict = "missing"
        elif "min" in item and value < item["min"]:
            verdict = "fail"

        if item.get("no_significant_drop"):
            if not pr_values or set(pr_values) != set(base_values):
                verdict = "missing"
                note = "missing or unmatched paired slice items"
            else:
                keys = sorted(pr_values)
                d, lo, hi = stats.paired_bootstrap(
                    [pr_values[k] for k in keys], [base_values[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        if verdict != "ok" and item.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(
            verdict, "BLOCK" if item.get("blocking") else "warn")
        lines.append(f"  {sid:<34} {str(round(value, 4)) if value is not None else 'None':<8} "
                     f"{json.dumps(threshold):<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
