"""Shared deterministic helpers for the cross-embodiment alignment tool.

No network access, no third-party dependencies, no wall-clock timestamps in
any output -- running the pipeline twice must produce byte-identical files.
"""
import csv
import json
import os


REQUIRED_MANIFEST_FIELDS = (
    "embodiment_id",
    "robot_type",
    "action_dim",
    "control_hz",
    "gripper_convention",
    "coord_frame",
    "episode_count",
    "frame_count",
)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def write_csv(path, header, rows):
    """Write rows deterministically with a fixed line terminator."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def write_text(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def is_missing(value):
    """True if a manifest field is missing/empty/None.

    Covers the real-world case this sample is built around: a manifest that
    has a 'robot_type' key present, but set to an empty string.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False
