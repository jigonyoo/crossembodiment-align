"""Per-pair mixability scoring and mix-all / mix-subset / do-not-mix
recommendations.

Scores are schema/statistic heuristics computed purely from manifest fields
(action_dim, control_hz, gripper_convention, coord_frame, robot_type). They
are a compatibility signal, NOT a measurement of transfer-learning
performance -- see the README Limitations section.
"""
from . import metadata as metadata_mod
from . import normalize
from . import resample

WEIGHT_ACTION_DIM = 0.30
WEIGHT_FREQ = 0.25
WEIGHT_GRIPPER = 0.15
WEIGHT_COORD = 0.10
WEIGHT_METADATA = 0.20

MIX_ALL_THRESHOLD = 0.85
MIX_SUBSET_THRESHOLD = 0.50

assert abs(
    (WEIGHT_ACTION_DIM + WEIGHT_FREQ + WEIGHT_GRIPPER + WEIGHT_COORD + WEIGHT_METADATA) - 1.0
) < 1e-9


def _action_dim_score(diff):
    if diff == 0:
        return 1.0
    if diff <= 2:
        return 0.4
    return 0.0


def _gripper_score(conflict):
    return 0.5 if conflict else 1.0


def _coord_score(mismatch):
    return 0.6 if mismatch else 1.0


def _metadata_score(a_ok, b_ok):
    return 1.0 if (a_ok and b_ok) else 0.0


def score_pair(manifest_a, manifest_b):
    """Compute the full mixability breakdown for one unordered pair of manifests."""
    dim_diff = normalize.action_dim_diff(manifest_a, manifest_b)
    dim_score = _action_dim_score(dim_diff)

    freq_score = resample.freq_compatibility_score(
        manifest_a["control_hz"], manifest_b["control_hz"]
    )

    gripper_conflict = (
        manifest_a.get("gripper_convention") is not None
        and manifest_b.get("gripper_convention") is not None
        and manifest_a.get("gripper_convention") != manifest_b.get("gripper_convention")
    )
    gripper_score = _gripper_score(gripper_conflict)

    coord_mismatch = (
        manifest_a.get("coord_frame") is not None
        and manifest_b.get("coord_frame") is not None
        and manifest_a.get("coord_frame") != manifest_b.get("coord_frame")
    )
    coord_score = _coord_score(coord_mismatch)

    a_ok = metadata_mod.has_robot_type(manifest_a)
    b_ok = metadata_mod.has_robot_type(manifest_b)
    meta_score = _metadata_score(a_ok, b_ok)

    overall = (
        WEIGHT_ACTION_DIM * dim_score
        + WEIGHT_FREQ * freq_score
        + WEIGHT_GRIPPER * gripper_score
        + WEIGHT_COORD * coord_score
        + WEIGHT_METADATA * meta_score
    )

    reasons = []
    if dim_diff > 0:
        reasons.append(
            f"action_dim mismatch: {manifest_a['action_dim']} vs {manifest_b['action_dim']} (diff={dim_diff})"
        )
    if freq_score < 1.0:
        reasons.append(
            f"control_hz mismatch: {manifest_a['control_hz']}Hz vs {manifest_b['control_hz']}Hz "
            f"(compatibility ratio={freq_score:.3f})"
        )
    if gripper_conflict:
        reasons.append(
            f"gripper convention conflict: {manifest_a.get('gripper_convention')} vs "
            f"{manifest_b.get('gripper_convention')}"
        )
    if coord_mismatch:
        reasons.append(
            f"coordinate frame mismatch: {manifest_a.get('coord_frame')} vs {manifest_b.get('coord_frame')}"
        )
    if not a_ok:
        reasons.append(f"missing robot_type metadata for '{manifest_a.get('embodiment_id')}'")
    if not b_ok:
        reasons.append(f"missing robot_type metadata for '{manifest_b.get('embodiment_id')}'")

    recommendation, hard_reasons = _recommend(overall, dim_diff, a_ok and b_ok, freq_score)

    all_reasons = sorted(set(reasons + hard_reasons))

    return {
        "embodiment_a": manifest_a.get("embodiment_id"),
        "embodiment_b": manifest_b.get("embodiment_id"),
        "action_dim_score": round(dim_score, 4),
        "freq_score": round(freq_score, 4),
        "gripper_score": round(gripper_score, 4),
        "coord_score": round(coord_score, 4),
        "metadata_score": round(meta_score, 4),
        "overall_score": round(overall, 4),
        "recommendation": recommendation,
        "reasons": all_reasons,
    }


def _recommend(overall, dim_diff, metadata_ok, freq_score):
    """Return (recommendation, extra_hard_reasons).

    Two hard blocks override the weighted score entirely, because no amount
    of compatibility elsewhere makes up for them:
      1. an action-space gap too large to bridge with padding/truncation
      2. embodiment identity unverifiable (missing robot_type) combined with
         a large control-frequency mismatch
    """
    if dim_diff > 2:
        return "do-not-mix", [
            f"HARD BLOCK: action-space dimension mismatch (diff={dim_diff}) "
            "exceeds what padding/truncation can bridge"
        ]
    if not metadata_ok and freq_score < 0.5:
        return "do-not-mix", [
            "HARD BLOCK: embodiment identity is unverifiable (missing robot_type) "
            "and control frequencies differ substantially -- too risky to mix "
            "without manual review"
        ]
    if overall >= MIX_ALL_THRESHOLD:
        return "mix-all", []
    if overall >= MIX_SUBSET_THRESHOLD:
        return "mix-subset", []
    return "do-not-mix", []


def score_all_pairs(manifests_by_id):
    """Score every unordered pair, in deterministic (sorted) order."""
    ids = sorted(manifests_by_id.keys())
    results = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            results.append(score_pair(manifests_by_id[a], manifests_by_id[b]))
    return results
