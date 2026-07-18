"""Control-frequency resampling analysis.

Given a target control frequency, computes the up/down-sampling factor for
each embodiment's native control_hz and flags information loss on
downsampling / fabricated-frame risk on upsampling. This is arithmetic on
manifest fields (native_hz, target_hz), not an actual resampling of
trajectory data -- no frames are read or produced.
"""


def recommend_target_hz(hz_values):
    """Recommend the lowest native control_hz among the datasets.

    Downsampling higher-hz data to match a lower rate is lossy but every kept
    frame is still real measured data. Upsampling the lowest-hz dataset to
    match a higher rate would fabricate frames via interpolation, which is
    worse for a mixed training set. So: pick the minimum native control_hz.
    """
    if not hz_values:
        raise ValueError("hz_values must be non-empty")
    return min(hz_values)


def compute_resample(native_hz, target_hz):
    native_hz = float(native_hz)
    target_hz = float(target_hz)
    factor = target_hz / native_hz
    if factor < 1.0:
        action = "downsample"
        dropped_pct = (1.0 - factor) * 100.0
        warning = (
            f"downsampling {native_hz:g}Hz -> {target_hz:g}Hz drops "
            f"~{dropped_pct:.1f}% of frames (information loss)"
        )
    elif factor > 1.0:
        action = "upsample"
        warning = (
            f"upsampling {native_hz:g}Hz -> {target_hz:g}Hz requires "
            "interpolation; the extra frames are not measured data"
        )
    else:
        action = "none"
        warning = None
    return {
        "native_hz": native_hz,
        "target_hz": target_hz,
        "factor": factor,
        "action": action,
        "warning": warning,
    }


def freq_compatibility_score(hz_a, hz_b):
    """0-1 score: 1.0 = identical control rates, lower = bigger mismatch.

    Symmetric: score(a, b) == score(b, a).
    """
    hz_a = float(hz_a)
    hz_b = float(hz_b)
    if hz_a <= 0 or hz_b <= 0:
        return 0.0
    return min(hz_a, hz_b) / max(hz_a, hz_b)
