"""Host-side symmetric per-tensor INT8 quantization, without NumPy dependencies.

INT8 uses [-127, 127], zero point 0, round-to-nearest ties-to-even and saturation.
C is quantized to INT32 with scale A_scale * B_scale (bias/initial accumulator).
"""
import math


def validate_scale(scale):
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be finite and positive")
    return scale


def accumulator_scale(a_scale, b_scale):
    return validate_scale(validate_scale(a_scale) * validate_scale(b_scale))


def _finite(values):
    values = list(values)
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError("tensor must be nonempty and contain finite values")
    return values


# 对称逐张量 AbsMax 校准：最大绝对值映射到 127；全零输入用 scale=1。
def calibrate(values):
    maximum = max(abs(x) for x in _finite(values))
    return validate_scale(maximum / 127 if maximum else 1.0)


# q = clamp(round(x/scale), -127, 127)，零点为 0；Python round 的中点取偶数。
# 返回的是表示设备整数值的列表，不是已经打包成 i8 的二进制文件。
def quantize_int8(values, scale):
    validate_scale(scale)
    # Clamp before round also handles finite/finite division overflowing to inf.
    return [round(max(-127.0, min(127.0, x / scale))) for x in _finite(values)]


# C 与 A*B 共用 scale=sa*sb，因此初始 C 必须量化到 INT32 的同一标度。
def quantize_accumulator(values, a_scale, b_scale):
    scale = accumulator_scale(a_scale, b_scale)
    result = []
    for value in _finite(values):
        scaled = value / scale
        if not math.isfinite(scaled):
            raise ValueError("initial accumulator cannot be represented as INT32")
        quantized = round(scaled)
        if not -(1 << 31) <= quantized < (1 << 31):
            raise ValueError("initial accumulator cannot be represented as INT32")
        result.append(quantized)
    return result


# 在宿主侧将 INT32 结果乘 sa*sb，恢复实数近似值；设备计算本身仍为整数。
def dequantize_accumulator(values, a_scale, b_scale):
    scale = accumulator_scale(a_scale, b_scale)
    values = list(values)
    if not values or not all(type(x) is int and -(1 << 31) <= x < (1 << 31) for x in values):
        raise ValueError("expected nonempty signed INT32 values")
    result = [x * scale for x in values]
    if not all(math.isfinite(x) for x in result):
        raise ValueError("dequantized output exceeds floating-point range")
    return result


def requantize_int8(values, a_scale, b_scale, output_scale):
    """Optional host-side INT8 output; the NPU itself retains INT32 accumulators."""
    return quantize_int8(dequantize_accumulator(values, a_scale, b_scale), output_scale)
