"""Read and validate per-dataset (per-embodiment) manifests.

A manifest describes one robot embodiment's demonstration dataset at the
level of metadata/statistics only: action-space dimensionality, control
frequency, gripper convention, coordinate frame, and episode/frame counts.
No demonstration frames, images, or trajectories are read or required --
this module only ever touches the small JSON manifest file.
"""
import glob
import os

from . import util


class ManifestError(ValueError):
    pass


def load_manifest(path):
    """Load a single manifest JSON file. Raises ManifestError on malformed JSON."""
    try:
        manifest = util.read_json(path)
    except (OSError, ValueError) as exc:
        raise ManifestError(f"could not read manifest {path}: {exc}") from exc
    manifest = dict(manifest)
    manifest["_source_path"] = path
    return manifest


def load_all(manifest_dir):
    """Load every *.json manifest in manifest_dir, sorted by filename for determinism.

    Returns (order, manifests) where order is a list of embodiment_id in
    deterministic (filename-sorted) order and manifests is a dict keyed by
    embodiment_id.
    """
    paths = sorted(glob.glob(os.path.join(manifest_dir, "*.json")))
    manifests = {}
    order = []
    for path in paths:
        m = load_manifest(path)
        eid = m.get("embodiment_id") or os.path.splitext(os.path.basename(path))[0]
        manifests[eid] = m
        order.append(eid)
    return order, manifests


def validate_manifest(manifest):
    """Return a sorted list of validation flag strings for one manifest.

    Flags cover missing/empty required fields and obviously invalid values
    (negative counts, non-positive control_hz/action_dim, unrecognized
    gripper convention strings, action_ranges length mismatch). This is a
    schema/sanity check only -- it says nothing about whether the underlying
    demonstration data is any good.
    """
    flags = []
    eid = manifest.get("embodiment_id") or "<unknown>"

    for field in util.REQUIRED_MANIFEST_FIELDS:
        if field not in manifest or util.is_missing(manifest.get(field)):
            flags.append(f"{eid}: missing/empty required field '{field}'")

    action_dim = manifest.get("action_dim")
    if isinstance(action_dim, (int, float)) and not isinstance(action_dim, bool) and action_dim <= 0:
        flags.append(f"{eid}: action_dim must be positive, got {action_dim}")

    control_hz = manifest.get("control_hz")
    if isinstance(control_hz, (int, float)) and not isinstance(control_hz, bool) and control_hz <= 0:
        flags.append(f"{eid}: control_hz must be positive, got {control_hz}")

    for count_field in ("episode_count", "frame_count"):
        val = manifest.get(count_field)
        if isinstance(val, (int, float)) and not isinstance(val, bool) and val < 0:
            flags.append(f"{eid}: {count_field} must be non-negative, got {val}")

    gripper = manifest.get("gripper_convention")
    if gripper is not None and gripper not in ("open=1", "open=0"):
        flags.append(
            f"{eid}: unrecognized gripper_convention '{gripper}' (expected 'open=1' or 'open=0')"
        )

    ranges = manifest.get("action_ranges")
    if ranges is not None and isinstance(action_dim, (int, float)) and not isinstance(action_dim, bool):
        if len(ranges) != action_dim:
            flags.append(
                f"{eid}: action_ranges has {len(ranges)} entries but action_dim={action_dim}"
            )

    return sorted(flags)
