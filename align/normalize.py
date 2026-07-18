"""Action-space normalization, gripper-convention unification, and
coordinate-frame consistency checks between two embodiment manifests.

Everything here produces a *plan* describing what an engineer would need to
do to align two datasets' action spaces, based only on manifest fields. It
does not touch, resample, or transform any actual trajectory data.
"""


def action_dim_diff(manifest_a, manifest_b):
    return abs(int(manifest_a["action_dim"]) - int(manifest_b["action_dim"]))


def action_space_plan(manifest_a, manifest_b):
    """Describe what it would take to align the two action spaces."""
    dim_a = int(manifest_a["action_dim"])
    dim_b = int(manifest_b["action_dim"])
    diff = abs(dim_a - dim_b)
    if diff == 0:
        note = "action dimensions already match; no padding/truncation needed"
        feasible = True
    elif diff <= 2:
        note = (
            f"dimension mismatch of {diff}; the smaller action space would need "
            f"zero-padding (or the larger truncated) on {diff} channel(s) -- "
            "verify which channels those are (e.g. is it the gripper channel?) "
            "before mixing"
        )
        feasible = True
    else:
        note = f"dimension mismatch of {diff} is too large to bridge with padding/truncation alone"
        feasible = False
    return {
        "embodiment_a": manifest_a.get("embodiment_id"),
        "embodiment_b": manifest_b.get("embodiment_id"),
        "action_dim_a": dim_a,
        "action_dim_b": dim_b,
        "diff": diff,
        "feasible": feasible,
        "note": note,
    }


def gripper_plan(manifest_a, manifest_b):
    """Plan for unifying gripper conventions (e.g. open=1 vs open=0)."""
    ga = manifest_a.get("gripper_convention")
    gb = manifest_b.get("gripper_convention")
    conflict = ga is not None and gb is not None and ga != gb
    if conflict:
        note = (
            f"gripper conventions conflict ({ga} vs {gb}); invert the gripper "
            f"channel of '{manifest_b.get('embodiment_id')}' to match "
            f"'{manifest_a.get('embodiment_id')}' before mixing"
        )
    else:
        note = "gripper conventions already match; no inversion needed"
    return {
        "embodiment_a": manifest_a.get("embodiment_id"),
        "embodiment_b": manifest_b.get("embodiment_id"),
        "gripper_a": ga,
        "gripper_b": gb,
        "conflict": conflict,
        "note": note,
    }


def coord_frame_plan(manifest_a, manifest_b):
    """Plan for reconciling coordinate frames (e.g. robot_base vs world)."""
    ca = manifest_a.get("coord_frame")
    cb = manifest_b.get("coord_frame")
    mismatch = ca is not None and cb is not None and ca != cb
    if mismatch:
        note = (
            f"coordinate frames differ ({ca} vs {cb}); a known extrinsic "
            "transform between frames is required to align actions -- this "
            "cannot be derived from the manifest alone and must be supplied "
            "separately (e.g. from robot calibration)"
        )
    else:
        note = "coordinate frames already match; no transform needed"
    return {
        "embodiment_a": manifest_a.get("embodiment_id"),
        "embodiment_b": manifest_b.get("embodiment_id"),
        "coord_frame_a": ca,
        "coord_frame_b": cb,
        "mismatch": mismatch,
        "note": note,
    }
