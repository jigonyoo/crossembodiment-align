"""Pipeline: ingest manifests -> validate -> metadata checks -> pairwise
mixability -> alignment plan -> report + CSV outputs.

Writing to output_dir never deletes the directory -- only os.makedirs(...,
exist_ok=True) plus overwriting the specific files this pipeline produces.
"""
import os

from . import ingest
from . import metadata as metadata_mod
from . import mixability
from . import report
from . import resample


def run(manifest_dir, output_dir):
    order, manifests = ingest.load_all(manifest_dir)
    if not manifests:
        raise SystemExit(f"no manifests found in {manifest_dir}")

    ingest_flags = []
    for eid in sorted(manifests):
        ingest_flags.extend(ingest.validate_manifest(manifests[eid]))
    ingest_flags = sorted(ingest_flags)

    meta_flags = []
    for eid in sorted(manifests):
        meta_flags.extend(metadata_mod.missing_metadata_flags(manifests[eid]))
    meta_flags.extend(metadata_mod.inconsistent_units(manifests))
    meta_flags.extend(metadata_mod.inherited_label_warnings(manifests))
    meta_flags = sorted(meta_flags)

    pair_results = mixability.score_all_pairs(manifests)

    target_hz = resample.recommend_target_hz([m["control_hz"] for m in manifests.values()])

    os.makedirs(output_dir, exist_ok=True)

    md = report.render_markdown_report(manifests, pair_results, target_hz, ingest_flags, meta_flags)
    md_path = os.path.join(output_dir, "mixability_report.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)

    pairwise_path = os.path.join(output_dir, "pairwise.csv")
    report.write_pairwise_csv(pairwise_path, pair_results)

    alignment_path = os.path.join(output_dir, "alignment_plan.csv")
    report.write_alignment_plan_csv(alignment_path, manifests, target_hz)

    summary_lines = []
    summary_lines.append("Cross-Embodiment Alignment run summary")
    summary_lines.append(f"embodiments: {len(manifests)} ({', '.join(sorted(manifests))})")
    summary_lines.append(f"manifest validation flags: {len(ingest_flags)}")
    summary_lines.append(f"metadata flags: {len(meta_flags)}")
    summary_lines.append(f"pairs scored: {len(pair_results)}")
    for r in pair_results:
        summary_lines.append(
            f"  {r['embodiment_a']} <-> {r['embodiment_b']}: "
            f"score={r['overall_score']:.4f} recommendation={r['recommendation']}"
        )
    summary_lines.append(f"target_hz: {target_hz:g}")
    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = os.path.join(output_dir, "run_summary.txt")
    with open(summary_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(summary_text)

    return {
        "manifests": manifests,
        "pair_results": pair_results,
        "ingest_flags": ingest_flags,
        "meta_flags": meta_flags,
        "target_hz": target_hz,
        "outputs": {
            "mixability_report.md": md_path,
            "pairwise.csv": pairwise_path,
            "alignment_plan.csv": alignment_path,
            "run_summary.txt": summary_path,
        },
    }
