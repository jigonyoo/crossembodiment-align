# Cross-Embodiment Dataset Alignment & Mixability

Answers whether several robot demonstration datasets can safely be mixed,
from their manifests alone. It validates each embodiment's metadata, builds
a per-pair normalization plan (action-space padding/truncation feasibility,
gripper-convention unification, coordinate-frame consistency), analyzes
control-frequency resampling with a warning on downsampling information
loss, and detects metadata problems such as an empty `robot_type` field,
inconsistent units, or an "inherited label" shared by embodiments with
differing action_dim/control_hz. Every pair gets a 0-1 mixability score with
the specific measured reasons and a `mix-all` / `mix-subset` / `do-not-mix`
recommendation, plus an overall recommendation for the whole collection --
all of it before any GPU time is spent.

**Positioning:** this is written by a data engineer, not a robot-learning
researcher. It answers one narrow, honest question -- *given the manifests
for several robot demonstration datasets, can they be mixed?* -- by
inspecting **metadata and statistics only**. It does **not** train a model,
run a robot or a policy, or verify that mixing datasets actually improves
(or hurts) a policy's real-world performance.

## Why this exists

Teams increasingly want to mix robot demonstration datasets (RT-X, DROID,
Bridge, an in-house arm) to get more training data. In practice the
metadata needed to safely mix them is often missing or inconsistent --
public BridgeData v3 conversions, for example, are known to ship with an
empty `robot_type` field. Silently mixing datasets with different action
spaces, control frequencies, or gripper conventions is a fast way to train
on noise. This tool surfaces those problems from the manifests before any
GPU time is spent.

## What it does

Given one JSON manifest per embodiment (action-space dimensionality,
control frequency, gripper convention, coordinate frame, episode/frame
counts, plus optional units and action ranges), it:

1. **Ingests & validates** each manifest, flagging missing/empty required
   fields and obviously invalid values (`align/ingest.py`).
2. **Builds a normalization plan** per pair: action-space padding/truncation
   feasibility, gripper-convention unification, coordinate-frame consistency
   (`align/normalize.py`).
3. **Analyzes control-frequency resampling**: picks a target frequency,
   computes the up/down-sampling factor per embodiment, and warns about
   information loss on downsampling (`align/resample.py`).
4. **Detects metadata problems**: missing/empty embodiment metadata (the
   empty-`robot_type` case), inconsistent units across datasets, and
   "inherited label" warnings when two embodiments share an identical
   `robot_type` string despite differing action_dim/control_hz -- a smell
   for copy-pasted metadata (`align/metadata.py`).
5. **Scores pairwise mixability** (0-1) with the specific measured reasons,
   and issues a recommendation -- `mix-all` / `mix-subset` / `do-not-mix`
   -- for every pair, plus an overall recommendation for the whole
   collection (`align/mixability.py`).
6. **Writes a report**: a Markdown mixability report, a pairwise CSV, and
   an alignment-plan CSV (`align/report.py`).

## Quickstart

```bash
python3 run_demo.py
python3 -m unittest discover -s tests -v
```

`run_demo.py` first writes three synthetic, deterministic embodiment
manifests (`data/generate_datasets.py`) with planted issues -- a missing
`robot_type`, a 5Hz-vs-20Hz control-frequency mismatch, and a flipped
gripper convention -- then runs the full pipeline and writes
`sample_output/`:

- `sample_output/mixability_report.md` -- the human-readable report
- `sample_output/pairwise.csv` -- per-pair scores and recommendations
- `sample_output/alignment_plan.csv` -- per-embodiment resampling plan
- `sample_output/run_summary.txt` -- plain-text run summary

Re-running `run_demo.py` is safe: it never deletes `sample_output/`, it
only overwrites the files it writes (`os.makedirs(..., exist_ok=True)` +
overwrite). Running it twice produces byte-identical output files (no
wall-clock timestamps anywhere in the pipeline).

## Docker

```bash
docker compose build
docker compose up
```

`docker-compose.yml` runs with `network_mode: none` -- the tool needs no
network access at any point (stdlib only, no API keys, no external data
fetches).

## Layout

```
align/            core package (stdlib only)
  ingest.py        manifest loading + validation
  normalize.py     action-space / gripper / coord-frame alignment plans
  resample.py      control-frequency resampling analysis
  metadata.py      missing-metadata / inconsistent-units / inherited-label detection
  mixability.py    pairwise scoring + mix-all/mix-subset/do-not-mix recommendation
  report.py        Markdown report + CSV writers
  run.py           pipeline orchestration
  util.py          deterministic JSON/CSV/text I/O helpers
data/
  generate_datasets.py   deterministic synthetic manifests (3 embodiments, planted issues)
tests/
  test_align.py    35 unittest tests
run_demo.py        generates manifests, runs the pipeline, writes sample_output/
SCHEMA.md          manifest JSON schema reference
```

## Limitations

- This tool assesses mixability from **manifests/metadata/statistics
  only**. It never reads, trains on, or validates demonstration
  trajectories, images, or rewards -- it has no idea whether the actual
  frames are any good.
- It does **not** train a model, run a policy, or verify that mixing
  datasets actually improves (or hurts) real robot performance. "Mixable"
  here means "structurally/statistically compatible enough to attempt,"
  nothing more.
- Alignment plans (padding, gripper inversion, resampling target) are
  **recommendations for a human to review and implement** -- nothing is
  auto-applied to any real dataset.
- Compatibility scores use fixed, hand-chosen weights for this sample. They
  are heuristics over schema/statistics fields, not empirically calibrated
  against transfer-learning outcomes, and are not a guarantee of anything.
- Coordinate-frame mismatches are flagged but not resolved: the actual
  extrinsic transform between frames has to come from robot calibration,
  which a manifest cannot tell you.
- The "inherited label" heuristic is a smell detector (same `robot_type`
  string, different action_dim/control_hz), not proof that metadata was
  copy-pasted -- it can both miss real cases and flag coincidental ones.

## License

MIT. See `LICENSE`.
