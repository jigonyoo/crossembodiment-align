# Manifest Schema

Each embodiment's dataset is described by one JSON manifest file under
`data/manifests/<embodiment_id>.json`. The tool never reads anything else
about the dataset -- no frames, images, or trajectories.

## Required fields

| field | type | meaning |
|---|---|---|
| `embodiment_id` | string | unique identifier for this dataset/robot combination |
| `robot_type` | string | robot hardware identifier (e.g. `franka_panda`). **Known real-world gap: some public dataset conversions ship this as an empty string.** |
| `action_dim` | int | dimensionality of the action vector, including the gripper channel |
| `control_hz` | number | native control frequency the demonstrations were recorded/executed at |
| `gripper_convention` | string | `"open=1"` or `"open=0"` -- which action value means "gripper open" |
| `coord_frame` | string | coordinate frame actions are expressed in (e.g. `robot_base`, `world`) |
| `episode_count` | int | number of demonstration episodes |
| `frame_count` | int | total number of demonstration frames/timesteps |

## Optional fields

| field | type | meaning |
|---|---|---|
| `units` | string | units of the action values (e.g. `radians`, `normalized`) |
| `gripper_channel_index` | int | which index in the action vector is the gripper channel |
| `action_ranges` | list of `[min, max]` | per-dimension action value range; length should equal `action_dim` |

## Example

```json
{
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
    [-2.8973, 2.8973]
  ]
}
```

## Validation

`align/ingest.py:validate_manifest()` flags, per manifest:

- any required field missing or empty (including a `robot_type` key that is
  present but set to `""`)
- non-positive `action_dim` or `control_hz`
- negative `episode_count` or `frame_count`
- a `gripper_convention` value other than `"open=1"` / `"open=0"`
- an `action_ranges` list whose length does not equal `action_dim`

Validation is a schema/sanity check only -- it cannot tell you whether the
underlying demonstration data is correct or useful.
