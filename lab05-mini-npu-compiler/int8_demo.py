"""Calibrate real FP32 data, compile an INT8 kernel, execute and report error.

python3 int8_demo.py --build-dir build --output-dir build/int8-demo
Optional --input JSON has m,n,k,a,b,c, with flat row-major matrices (c optional).
"""
import argparse
import json
import math
import random
import subprocess
from pathlib import Path

from quantize import calibrate, quantize_int8, quantize_accumulator, dequantize_accumulator
from simulator import execute, f32


def matmul_source(m, n, k):
    a, b, c = f"memref<{m}x{k}xf32>", f"memref<{k}x{n}xf32>", f"memref<{m}x{n}xf32>"
    return (f"module {{ func.func @matmul(%a: {a}, %b: {b}, %c: {c}) {{\n"
            f"  linalg.matmul ins(%a, %b : {a}, {b}) outs(%c : {c})\n  return\n}} }}\n")


def run_tool(args, text):
    result = subprocess.run(args, input=text, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout


def run_demo(build_dir, output_dir, data=None):
    if data is None:
        rng = random.Random(42)
        data = dict(m=5, n=6, k=7,
                    a=[rng.uniform(-2, 2) for _ in range(35)],
                    b=[rng.uniform(-2, 2) for _ in range(42)],
                    c=[rng.uniform(-0.5, 0.5) for _ in range(30)])
    m, n, k = (data[key] for key in ("m", "n", "k"))
    if any(type(dim) is not int or not 1 <= dim <= 4096 for dim in (m, n, k)):
        raise ValueError("dimensions must be integers in [1, 4096]")
    a, b, c = ([f32(x) for x in data["a"]], [f32(x) for x in data["b"]],
               [f32(x) for x in data.get("c", [0.0] * (m * n))])
    if (len(a), len(b), len(c)) != (m * k, k * n, m * n):
        raise ValueError("flat tensor lengths do not match M/N/K")
    sa, sb = calibrate(a), calibrate(b)
    qa, qb = quantize_int8(a, sa), quantize_int8(b, sb)
    qc = quantize_accumulator(c, sa, sb)

    # 用无限精度整数参考核对精确结果；此演示要求结果未溢出，以便讨论量化误差。
    expected = [qc[row * n + col] + sum(qa[row * k + red] * qb[red * n + col] for red in range(k))
                for row in range(m) for col in range(n)]
    if any(not -(1 << 31) <= value < (1 << 31) for value in expected):
        raise ValueError("INT32 accumulator would overflow; rescale the initial C")

    build_dir, output_dir = Path(build_dir).resolve(), Path(output_dir).resolve()
    source = matmul_source(m, n, k)
    planned = run_tool([str(build_dir / "npu-opt"),
                        f"--npu-compile=quantize-int8=true a-scale={sa:.17g} b-scale={sb:.17g}",
                        "--verify-each"], source)
    program = run_tool([str(build_dir / "npu-translate"), "-"], planned)
    actual = execute(program, [qa, qb, qc])[0]
    if actual["values"] != expected:
        raise AssertionError("INT8 execution differs from exact integer reference")
    if actual["quantization"] != dict(a_scale=sa, b_scale=sb, c_scale=sa * sb):
        raise AssertionError("compiler did not preserve calibration scales")
    dequantized = dequantize_accumulator(actual["values"], sa, sb)

    reference, bounds = [], []
    for row in range(m):
        for col in range(n):
            value = c[row * n + col]
            for red in range(k):
                value = f32(value + f32(a[row * k + red] * b[red * n + col]))
            reference.append(value)
            # 未裁剪时 |eA| <= sA/2, |eB| <= sB/2，再计入 C 量化误差。
            bound = sa * sb / 2 + sum(abs(a[row * k + red]) * sb / 2 +
                    abs(b[red * n + col]) * sa / 2 + sa * sb / 4 for red in range(k))
            bounds.append(bound + 1e-5 * max(1, abs(value)))
    errors = [abs(x - y) for x, y in zip(dequantized, reference)]
    if any(error > bound for error, bound in zip(errors, bounds)):
        raise AssertionError("quantization error exceeds the rounding bound")
    report = dict(shape=[m, n, k], a_scale=sa, b_scale=sb, c_scale=sa * sb,
                  max_abs_error=max(errors), rmse=math.sqrt(sum(x * x for x in errors) / len(errors)),
                  input_bytes_fp32=4 * (len(a) + len(b)), input_bytes_int8=len(a) + len(b),
                  integer_reference_exact=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "input.mlir").write_text(source)
    (output_dir / "planned.mlir").write_text(planned)
    (output_dir / "program.npu").write_text(program)
    (output_dir / "tensors.json").write_text(json.dumps(dict(
        a=a, b=b, c=c, qa=qa, qb=qb, qc=qc, output_i32=actual["values"],
        output_dequantized=dequantized, output_fp32=reference, **report), indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=Path(__file__).resolve().parent / "build")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "build/int8-demo")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    report = run_demo(args.build_dir, args.output_dir,
                      json.loads(args.input.read_text()) if args.input else None)
    print(json.dumps(report, indent=2))
    print(f"PASS: INT8 integer reference exact; artifacts: {args.output_dir}")
