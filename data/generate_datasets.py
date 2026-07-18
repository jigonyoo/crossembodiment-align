#!/usr/bin/env python3
"""Deterministically generate synthetic manifests for three robot embodiments.

Planted issues (intentional, for the tool to detect -- this mirrors real
gaps seen in public cross-embodiment dataset conversions):
  - bridge_v3_7dof has an EMPTY robot_type (mirrors real-world BridgeData v3
    conversions that ship with robot_type unset)
  - bridge_v3_7dof runs at 5Hz vs 20Hz for the other two embodiments
  - so101_6dof uses a flipped gripper convention (open=0) vs the others (open=1)

No randomness, no network calls, no timestamps -- running this twice
produces byte-identical files.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from align import util  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MANIFEST_DIR = os.path.join(HERE, "manifests")

FRANKA = {
    "embodiment_id": "franka_7dof",
    "robot_type": "franka_panda",
    "action_dim": 7,
    "control_hz": 20,
    "gripper_convention": "open=1",
    "gripper_channel_index": 6,
    "coord_frame": "robot_base",
    "units": "radians",
    "episode_count": 1200,
    "frame_count": 240000,
    "action_ranges": [
        [-2.8973, 2.8973], [-1.7628, 1.7628], [-2.8973, 2.8973],
        [-3.0718, -0.0698], [-2.8973, 2.8973], [-0.0175, 3.7525],
        [-2.8973, 2.8973],
    ],
}

SO101 = {
    "embodiment_id": "so101_6dof",
    "robot_type": "so101",
    "action_dim": 6,
    "control_hz": 20,
    "gripper_convention": "open=0",
    "gripper_channel_index": 5,
    "coord_frame": "robot_base",
    "units": "radians",
    "episode_count": 800,
    "frame_count": 96000,
    "action_ranges": [
        [-3.14, 3.14], [-1.57, 1.57], [-1.57, 1.57],
        [-1.57, 1.57], [-1.57, 1.57], [0.0, 1.0],
    ],
}

BRIDGE = {
    "embodiment_id": "bridge_v3_7dof",
    "robot_type": "",
    "action_dim": 7,
    "control_hz": 5,
    "gripper_convention": "open=1",
    "gripper_channel_index": 6,
    "coord_frame": "world",
    "units": "normalized",
    "episode_count": 5000,
    "frame_count": 900000,
    "action_ranges": [
        [-1, 1], [-1, 1], [-1, 1], [-1, 1], [-1, 1], [-1, 1], [0, 1],
    ],
}

DATASETS = [FRANKA, SO101, BRIDGE]


def generate(manifest_dir=DEFAULT_MANIFEST_DIR):
    """Write the deterministic manifest set to manifest_dir. Returns sorted paths."""
    for manifest in DATASETS:
        path = os.path.join(manifest_dir, f"{manifest['embodiment_id']}.json")
        util.write_json(path, manifest)
    return sorted(
        os.path.join(manifest_dir, f"{m['embodiment_id']}.json") for m in DATASETS
    )


def main():
    paths = generate()
    for p in paths:
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
