"""Detect missing/empty embodiment metadata, inconsistent units, and
suspicious 'inherited' labels (metadata that looks copy-pasted between
embodiments without being updated) -- entirely from manifest fields.

This module is deliberately named for the real-world failure mode that
motivates this whole sample: dataset conversions (e.g. some public
BridgeData v3 conversions) that ship with 'robot_type' present in the
schema but left as an empty string.
"""
from . import util


def missing_metadata_flags(manifest):
    eid = manifest.get("embodiment_id") or "<unknown>"
    flags = []
    for field in ("robot_type", "coord_frame", "gripper_convention", "units"):
        if util.is_missing(manifest.get(field)):
            flags.append(f"{eid}: missing/empty metadata field '{field}'")
    return flags


def has_robot_type(manifest):
    return not util.is_missing(manifest.get("robot_type"))


def inconsistent_units(manifests_by_id):
    """Flag when embodiments report different 'units' for action values."""
    seen = {}
    for eid, m in sorted(manifests_by_id.items()):
        units = m.get("units")
        if util.is_missing(units):
            continue
        seen.setdefault(units, []).append(eid)
    flags = []
    if len(seen) > 1:
        parts = ", ".join(f"{u!r}={ids}" for u, ids in sorted(seen.items(), key=lambda kv: kv[0] or ""))
        flags.append(f"inconsistent 'units' across embodiments: {parts}")
    return flags


def inherited_label_warnings(manifests_by_id):
    """Heuristic: two different embodiment_ids sharing an identical
    robot_type string despite differing action_dim or control_hz suggest the
    robot_type metadata was copy-pasted/inherited rather than authored
    per-dataset (a real, if imperfect, metadata-hygiene smell).
    """
    by_robot_type = {}
    for eid, m in sorted(manifests_by_id.items()):
        rt = m.get("robot_type")
        if util.is_missing(rt):
            continue
        by_robot_type.setdefault(rt, []).append(eid)

    warnings = []
    for rt, eids in sorted(by_robot_type.items(), key=lambda kv: kv[0]):
        if len(eids) < 2:
            continue
        dims = {manifests_by_id[e].get("action_dim") for e in eids}
        hzs = {manifests_by_id[e].get("control_hz") for e in eids}
        if len(dims) > 1 or len(hzs) > 1:
            warnings.append(
                f"embodiments {eids} share robot_type={rt!r} but differ in "
                "action_dim/control_hz -- check for copy-pasted/inherited metadata"
            )
    return warnings
