"""Render the mixability report (Markdown) and pairwise/alignment CSVs.

All output here is derived deterministically from the input manifests and
the scoring/resample modules -- no timestamps, no randomness, no external
calls.
"""
from . import resample
from . import util


def build_alignment_rows(manifests_by_id, target_hz):
    rows = []
    for eid in sorted(manifests_by_id):
        m = manifests_by_id[eid]
        rs = resample.compute_resample(m["control_hz"], target_hz)
        rows.append([
            eid,
            m.get("robot_type") or "(missing)",
            m["action_dim"],
            m["control_hz"],
            target_hz,
            f"{rs['factor']:.4f}",
            rs["action"],
            rs["warning"] or "",
            m.get("gripper_convention") or "(missing)",
            m.get("coord_frame") or "(missing)",
        ])
    return rows


def write_alignment_plan_csv(path, manifests_by_id, target_hz):
    header = [
        "embodiment_id", "robot_type", "action_dim", "native_hz", "target_hz",
        "resample_factor", "resample_action", "resample_warning",
        "gripper_convention", "coord_frame",
    ]
    rows = build_alignment_rows(manifests_by_id, target_hz)
    util.write_csv(path, header, rows)
    return rows


def write_pairwise_csv(path, pair_results):
    header = [
        "embodiment_a", "embodiment_b", "action_dim_score", "freq_score",
        "gripper_score", "coord_score", "metadata_score", "overall_score",
        "recommendation", "reasons",
    ]
    rows = []
    for r in pair_results:
        rows.append([
            r["embodiment_a"], r["embodiment_b"], r["action_dim_score"],
            r["freq_score"], r["gripper_score"], r["coord_score"],
            r["metadata_score"], r["overall_score"], r["recommendation"],
            " | ".join(r["reasons"]),
        ])
    util.write_csv(path, header, rows)
    return rows


def render_markdown_report(manifests_by_id, pair_results, target_hz, ingest_flags, meta_flags):
    lines = []
    lines.append("# Cross-Embodiment Dataset Alignment & Mixability Report")
    lines.append("")
    lines.append(
        "This report assesses whether the listed robot demonstration datasets "
        "can be mixed for training, based **only** on their "
        "manifests/metadata/statistics. It does not train a model, run a "
        "policy, or verify that mixing actually helps or hurts downstream "
        "performance. See Limitations in the README."
    )
    lines.append("")

    lines.append("## Embodiments")
    lines.append("")
    lines.append(
        "| embodiment_id | robot_type | action_dim | control_hz | gripper | "
        "coord_frame | episodes | frames |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for eid in sorted(manifests_by_id):
        m = manifests_by_id[eid]
        rt = m.get("robot_type") or "**(missing)**"
        lines.append(
            f"| {eid} | {rt} | {m.get('action_dim')} | {m.get('control_hz')} | "
            f"{m.get('gripper_convention')} | {m.get('coord_frame')} | "
            f"{m.get('episode_count')} | {m.get('frame_count')} |"
        )
    lines.append("")

    if ingest_flags:
        lines.append("## Manifest Validation Flags")
        lines.append("")
        for f in ingest_flags:
            lines.append(f"- {f}")
        lines.append("")

    if meta_flags:
        lines.append("## Metadata Flags")
        lines.append("")
        for f in meta_flags:
            lines.append(f"- {f}")
        lines.append("")

    lines.append(f"## Control-Frequency Alignment (target = {target_hz:g}Hz)")
    lines.append("")
    lines.append(
        f"Target frequency chosen as the minimum native control_hz across all "
        f"embodiments ({target_hz:g}Hz), so every kept frame after resampling "
        f"is real measured data rather than interpolated."
    )
    lines.append("")
    lines.append("| embodiment_id | native_hz | factor | action | warning |")
    lines.append("|---|---|---|---|---|")
    for eid in sorted(manifests_by_id):
        m = manifests_by_id[eid]
        rs = resample.compute_resample(m["control_hz"], target_hz)
        lines.append(
            f"| {eid} | {rs['native_hz']:g} | {rs['factor']:.4f} | "
            f"{rs['action']} | {rs['warning'] or '-'} |"
        )
    lines.append("")

    lines.append("## Pairwise Mixability")
    lines.append("")
    for r in pair_results:
        lines.append(f"### {r['embodiment_a']} <-> {r['embodiment_b']}")
        lines.append("")
        lines.append(f"- **Overall score:** {r['overall_score']:.4f}")
        lines.append(f"- **Recommendation:** **{r['recommendation']}**")
        lines.append(
            f"- Component scores: action_dim={r['action_dim_score']:.2f}, "
            f"freq={r['freq_score']:.2f}, gripper={r['gripper_score']:.2f}, "
            f"coord={r['coord_score']:.2f}, metadata={r['metadata_score']:.2f}"
        )
        if r["reasons"]:
            lines.append("- Reasons:")
            for reason in r["reasons"]:
                lines.append(f"  - {reason}")
        else:
            lines.append("- Reasons: none -- manifests fully agree on the checked fields")
        lines.append("")

    lines.append("## Overall Recommendation")
    lines.append("")
    counts = {"mix-all": 0, "mix-subset": 0, "do-not-mix": 0}
    for r in pair_results:
        counts[r["recommendation"]] = counts.get(r["recommendation"], 0) + 1
    total = len(pair_results)
    lines.append(
        f"Of {total} embodiment pair(s): {counts.get('mix-all', 0)} mix-all, "
        f"{counts.get('mix-subset', 0)} mix-subset, "
        f"{counts.get('do-not-mix', 0)} do-not-mix."
    )
    if total > 0 and counts.get("do-not-mix", 0) == total:
        overall = "do-not-mix"
    elif total > 0 and counts.get("mix-all", 0) == total:
        overall = "mix-all"
    else:
        overall = "mix-subset"
    lines.append("")
    lines.append(
        f"**Overall recommendation for this dataset collection: {overall}** "
        "(driven by the pair with the weakest measured compatibility -- see "
        "per-pair reasons above before acting on this)."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("")
    lines.append(
        "- This tool assesses mixability from manifests/metadata/statistics "
        "**only**. It does not read, train on, or verify demonstration "
        "trajectories, images, or rewards."
    )
    lines.append(
        "- It does not train a model, run a policy, or verify that mixing "
        "datasets actually improves (or hurts) real robot performance."
    )
    lines.append(
        "- Alignment plans (padding, gripper inversion, resampling) are "
        "recommendations for a human to validate and implement, not "
        "auto-applied transforms."
    )
    lines.append(
        "- Compatibility scores are schema/statistic heuristics with fixed "
        "weights chosen for this sample -- they are not empirically "
        "calibrated against transfer-learning outcomes and are not a "
        "guarantee of anything."
    )
    lines.append(
        "- Coordinate-frame mismatches are flagged but not resolved -- the "
        "actual extrinsic transform must come from robot calibration, which "
        "is outside what a manifest can tell you."
    )
    lines.append("")

    return "\n".join(lines) + "\n"
