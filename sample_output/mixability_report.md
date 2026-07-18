# Cross-Embodiment Dataset Alignment & Mixability Report

This report assesses whether the listed robot demonstration datasets can be mixed for training, based **only** on their manifests/metadata/statistics. It does not train a model, run a policy, or verify that mixing actually helps or hurts downstream performance. See Limitations in the README.

## Embodiments

| embodiment_id | robot_type | action_dim | control_hz | gripper | coord_frame | episodes | frames |
|---|---|---|---|---|---|---|---|
| bridge_v3_7dof | **(missing)** | 7 | 5 | open=1 | world | 5000 | 900000 |
| franka_7dof | franka_panda | 7 | 20 | open=1 | robot_base | 1200 | 240000 |
| so101_6dof | so101 | 6 | 20 | open=0 | robot_base | 800 | 96000 |

## Manifest Validation Flags

- bridge_v3_7dof: missing/empty required field 'robot_type'

## Metadata Flags

- bridge_v3_7dof: missing/empty metadata field 'robot_type'
- inconsistent 'units' across embodiments: 'normalized'=['bridge_v3_7dof'], 'radians'=['franka_7dof', 'so101_6dof']

## Control-Frequency Alignment (target = 5Hz)

Target frequency chosen as the minimum native control_hz across all embodiments (5Hz), so every kept frame after resampling is real measured data rather than interpolated.

| embodiment_id | native_hz | factor | action | warning |
|---|---|---|---|---|
| bridge_v3_7dof | 5 | 1.0000 | none | - |
| franka_7dof | 20 | 0.2500 | downsample | downsampling 20Hz -> 5Hz drops ~75.0% of frames (information loss) |
| so101_6dof | 20 | 0.2500 | downsample | downsampling 20Hz -> 5Hz drops ~75.0% of frames (information loss) |

## Pairwise Mixability

### bridge_v3_7dof <-> franka_7dof

- **Overall score:** 0.5725
- **Recommendation:** **do-not-mix**
- Component scores: action_dim=1.00, freq=0.25, gripper=1.00, coord=0.60, metadata=0.00
- Reasons:
  - HARD BLOCK: embodiment identity is unverifiable (missing robot_type) and control frequencies differ substantially -- too risky to mix without manual review
  - control_hz mismatch: 5Hz vs 20Hz (compatibility ratio=0.250)
  - coordinate frame mismatch: world vs robot_base
  - missing robot_type metadata for 'bridge_v3_7dof'

### bridge_v3_7dof <-> so101_6dof

- **Overall score:** 0.3175
- **Recommendation:** **do-not-mix**
- Component scores: action_dim=0.40, freq=0.25, gripper=0.50, coord=0.60, metadata=0.00
- Reasons:
  - HARD BLOCK: embodiment identity is unverifiable (missing robot_type) and control frequencies differ substantially -- too risky to mix without manual review
  - action_dim mismatch: 7 vs 6 (diff=1)
  - control_hz mismatch: 5Hz vs 20Hz (compatibility ratio=0.250)
  - coordinate frame mismatch: world vs robot_base
  - gripper convention conflict: open=1 vs open=0
  - missing robot_type metadata for 'bridge_v3_7dof'

### franka_7dof <-> so101_6dof

- **Overall score:** 0.7450
- **Recommendation:** **mix-subset**
- Component scores: action_dim=0.40, freq=1.00, gripper=0.50, coord=1.00, metadata=1.00
- Reasons:
  - action_dim mismatch: 7 vs 6 (diff=1)
  - gripper convention conflict: open=1 vs open=0

## Overall Recommendation

Of 3 embodiment pair(s): 0 mix-all, 1 mix-subset, 2 do-not-mix.

**Overall recommendation for this dataset collection: mix-subset** (driven by the pair with the weakest measured compatibility -- see per-pair reasons above before acting on this).

## Limitations

- This tool assesses mixability from manifests/metadata/statistics **only**. It does not read, train on, or verify demonstration trajectories, images, or rewards.
- It does not train a model, run a policy, or verify that mixing datasets actually improves (or hurts) real robot performance.
- Alignment plans (padding, gripper inversion, resampling) are recommendations for a human to validate and implement, not auto-applied transforms.
- Compatibility scores are schema/statistic heuristics with fixed weights chosen for this sample -- they are not empirically calibrated against transfer-learning outcomes and are not a guarantee of anything.
- Coordinate-frame mismatches are flagged but not resolved -- the actual extrinsic transform must come from robot calibration, which is outside what a manifest can tell you.

