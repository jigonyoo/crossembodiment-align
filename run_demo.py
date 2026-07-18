#!/usr/bin/env python3
"""Generate synthetic manifests and run the full alignment pipeline,
writing sample_output/.

Safe to re-run: this script never deletes sample_output/ (no rmtree, no
unlink of the directory) -- it only calls os.makedirs(..., exist_ok=True)
and overwrites the specific files it produces.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from data import generate_datasets  # noqa: E402
from align import run as run_mod  # noqa: E402


def main():
    manifest_dir = os.path.join(HERE, "data", "manifests")
    output_dir = os.path.join(HERE, "sample_output")

    os.makedirs(manifest_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    generate_datasets.generate(manifest_dir)
    result = run_mod.run(manifest_dir, output_dir)

    print(f"embodiments: {len(result['manifests'])}")
    print(f"manifest validation flags: {len(result['ingest_flags'])}")
    print(f"metadata flags: {len(result['meta_flags'])}")
    for r in result["pair_results"]:
        print(
            f"  {r['embodiment_a']} <-> {r['embodiment_b']}: "
            f"score={r['overall_score']:.4f} rec={r['recommendation']}"
        )
    print(f"wrote outputs to {output_dir}")


if __name__ == "__main__":
    main()
