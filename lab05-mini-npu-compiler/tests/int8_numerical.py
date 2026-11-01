from pathlib import Path
import math
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulator import execute, simulate
from quantize import (calibrate, quantize_int8, quantize_accumulator,
                      dequantize_accumulator, requantize_int8, accumulator_scale)
from int8_demo import run_demo

opt, translate = sys.argv[1:]


def run(args, text):
    result = subprocess.run(args, input=text, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def rejected(args, text, expected):
    result = subprocess.run(args, input=text, text=True, capture_output=True)
    assert result.returncode != 0 and expected in result.stderr, result.stderr
    assert not result.stdout, "failed compile/export emitted a partial program"


def kernel(m, n, k, integer=True, repeats=1):
    a, b, c = (f"memref<{m}x{k}x{'i8' if integer else 'f32'}>",
               f"memref<{k}x{n}x{'i8' if integer else 'f32'}>",
               f"memref<{m}x{n}x{'i32' if integer else 'f32'}>")
    body = f"linalg.matmul ins(%a, %b : {a}, {b}) outs(%c : {c})\n" * repeats
    return f"module {{ func.func @test(%a: {a}, %b: {b}, %c: {c}) {{ {body} return }} }}"


cases = 0
for m, n, k in [(1, 1, 1), (5, 6, 7), (3, 2, 9), (8, 8, 8), (2, 9, 1)]:
    for tile in (1, 2, 4, 8):
        planned = run([opt, f"--npu-compile=tile-size={tile}", "--verify-each"], kernel(m, n, k))
        isa = run([translate, "-"], planned)
        for seed in (0, 17, 42):
            simulate(isa, seed)
            cases += 1
planned = run([opt, "--npu-compile"], kernel(5, 6, 7, repeats=2))
simulate(run([translate, "-"], planned), 23, repeats=2)
cases += 1

# 明确核对 sign extension、INT32 模溢出，以及跨 K tile 累加。
planned = run([opt, "--npu-compile=tile-size=1"], kernel(1, 1, 3))
isa = run([translate, "-"], planned)
inputs = [[-128, 127, -128], [-128, -128, 127], [2147483640]]
assert execute(isa, inputs)[0]["values"] == [2147467512]
simulate(isa, inputs=inputs)
overflow = [[127, 127, 127], [127, 127, 127], [2147483640]]
assert execute(isa, overflow)[0]["values"] == [-2147435269]
simulate(isa, inputs=overflow)
cases += 2
print(f"PASS: {cases} INT8 exact integer cases (signed extremes, overflow, boundaries, repeated accumulation)")

# 真实位宽影响 SRAM：8x8x8 从 FP32 的 768 字节降到 INT8 的 384 字节。
rejected([opt, "--npu-compile=tile-size=8 sram-bytes=512"], kernel(8, 8, 8, False), "tile exceeds SRAM capacity")
planned = run([opt, "--npu-compile=tile-size=8 sram-bytes=512"], kernel(8, 8, 8))
assert "npu.sram_bytes = 384" in planned
simulate(run([translate, "-"], planned))

# 舍入采用 ties-to-even，对称窄范围饱和；全零张量也具有有效 scale。
assert calibrate([0.0, 0.0]) == 1.0
assert calibrate([-127.0, 42.0]) == 1.0
assert quantize_int8([-100, -1.25, -.75, -.25, .25, .75, 1.25, 100], .5) == [-127, -2, -2, 0, 0, 2, 2, 127]
assert quantize_int8([1e308, -1e308], 1e-308) == [127, -127]
assert quantize_accumulator([.125, .375, -.375], .5, .5) == [0, 2, -2]
assert dequantize_accumulator([4, -4], .5, .25) == [.5, -.5]
assert requantize_int8([100000, -100000, 8], .5, .25, 1.0) == [127, -127, 1]
for action in [lambda: calibrate([math.nan]), lambda: calibrate([]),
               lambda: quantize_int8([1], 0), lambda: quantize_int8([math.inf], 1),
               lambda: accumulator_scale(1e-300, 1e-300),
               lambda: quantize_accumulator([1e20], .1, .1)]:
    try:
        action()
    except ValueError:
        pass
    else:
        raise AssertionError("invalid quantization data was accepted")

# Compiler scale checks, correct pass order and duplicate quantization rejection.
fp = kernel(2, 2, 2, False)
for scales in ("a-scale=0", "b-scale=-1", "a-scale=1e308 b-scale=1e308", "a-scale=1e-300 b-scale=1e-300"):
    rejected([opt, f"--npu-compile=quantize-int8=true {scales}"], fp, "must be finite and positive")
rejected([opt, "--npu-compile=quantize-int8=true"], kernel(2, 2, 2), "unquantized f32 kernel")
rejected([opt, "--npu-quantize-int8"], fp, "after NPU lowering and before tiling")
lowered = run([opt, "--convert-linalg-to-npu", "--npu-quantize-int8=a-scale=0.125 b-scale=0.25"], fp)
rejected([opt, "--npu-quantize-int8"], lowered, "unquantized f32 kernel")
unsigned = kernel(2, 2, 2).replace("linalg.matmul ins", "linalg.matmul {cast = #linalg.type_fn<cast_unsigned>} ins")
rejected([opt, "--npu-compile"], unsigned, "failed to legalize")

# metadata and byte-accurate addresses are revalidated by the exporter.
planned = run([opt, "--npu-compile=quantize-int8=true a-scale=0.125 b-scale=0.25"], fp)
forged = planned.replace("npu.c_scale = 3.125000e-02", "npu.c_scale = 0.0", 1)
assert forged != planned
rejected([translate, "-"], forged, "quantization scales must be finite and positive")
forged = planned.replace("npu.c_scale = 3.125000e-02", "npu.c_scale = 6.250000e-02", 1)
rejected([translate, "-"], forged, "c_scale = a_scale * b_scale")
forged = re.sub(r"npu.a_scale = [^,]+, ", "", planned, count=1)
rejected([translate, "-"], forged, "three f64 scales")
forged = planned.replace("npu.bytes = 4 : i64", "npu.bytes = 16 : i64", 1)
assert forged != planned
rejected([translate, "-"], forged, "invalid or overlapping DRAM")

# 手写十进制元数据允许正常的 f64 舍入差异：.1 * .2 可写成 .02。
rounded = run([opt, "--npu-compile=quantize-int8=true a-scale=0.1 b-scale=0.2"], fp)
rounded = re.sub(r"npu.c_scale = [^:]+: f64", "npu.c_scale = 0.02 : f64", rounded, count=1)
simulate(run([translate, "-"], rounded))

with tempfile.TemporaryDirectory() as temp:
    report = run_demo(Path(opt).parent, Path(temp) / "random")
    assert report["integer_reference_exact"] and report["input_bytes_fp32"] == 4 * report["input_bytes_int8"]
    assert report["max_abs_error"] < .06
    for name, a, b in [("zeros", [0.0] * 6, [0.0] * 6),
                        ("constant", [-1.0] * 6, [.5] * 6)]:
        report = run_demo(Path(opt).parent, Path(temp) / name,
                          dict(m=2, n=2, k=3, a=a, b=b, c=[.25, -.25, .5, -.5]))
        assert report["integer_reference_exact"]
print("PASS: calibration, saturation, ties-to-even, FP32 error bounds, ABI, metadata and memory checks")
