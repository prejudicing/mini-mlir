"""Export a real PyTorch matmul, compile with Lab5, and compare actual outputs."""
import argparse
import importlib.util
import json
import math
import subprocess
from pathlib import Path

import torch

from frontend import emit_linalg, export_model
from model import MatmulModel

LAB_DIR = Path(__file__).resolve().parent
BACKEND_DIR = LAB_DIR.parent / "lab05-mini-npu-compiler"


# 按文件路径复用 Lab5 的执行模型和量化函数；不复制、也不重新实现后端。
def load_backend_module(name):
    spec = importlib.util.spec_from_file_location(f"lab5_{name}", BACKEND_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


simulator = load_backend_module("simulator")
quantize = load_backend_module("quantize")


# source 从标准输入传入编译工具，返回值是工具标准输出中的 IR 或伪指令。
# stderr 留给诊断，非零退出码立即中止，避免把错误信息当作下一阶段输入。
def run_tool(arguments, source):
    completed = subprocess.run([str(arg) for arg in arguments], input=source,
                               text=True, capture_output=True)
    if completed.returncode:
        raise RuntimeError(f"{arguments[0]} failed:\n{completed.stderr}")
    return completed.stdout


# 使用局部随机数生成器，固定 seed 后可复现实验输入。
def make_inputs(m=5, n=6, k=7, seed=42):
    if any(type(dim) is not int or not 1 <= dim <= 4096 for dim in (m, n, k)):
        raise ValueError("M/N/K must be integers in [1, 4096]")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    a = torch.rand((m, k), generator=generator, dtype=torch.float32) * 4 - 2
    b = torch.rand((k, n), generator=generator, dtype=torch.float32) * 4 - 2
    return a, b


def compile_and_run(a, b, backend_dir, output_dir, *, mode="fp32", tile_size=4,
                    sram_bytes=4096, model=None):
    """Execute the emitted pseudo-ISA, never substitute PyTorch's answer."""
    if mode not in ("fp32", "int8"):
        raise ValueError("mode must be fp32 or int8")
    if type(tile_size) is not int or not 1 <= tile_size <= 64:
        raise ValueError("tile size must be an integer in [1, 64]")
    if type(sram_bytes) is not int or sram_bytes <= 0:
        raise ValueError("SRAM capacity must be a positive integer")
    backend_dir, output_dir = Path(backend_dir).resolve(), Path(output_dir).resolve()
    opt, translate = backend_dir / "npu-opt", backend_dir / "npu-translate"
    if not opt.is_file() or not translate.is_file():
        raise ValueError("Lab5 tools not found; build the backend first")

    model = MatmulModel() if model is None else model
    # 阶段 1：导出并验证图，同时获取后端需要的静态矩阵尺寸。
    program, spec = export_model(model, a, b)
    # PyTorch 只产生独立参考答案；后面的 actual 必须来自模拟器执行。
    # The model executes only to provide a reference, not the NPU result.
    with torch.no_grad():
        reference = model(a, b).detach()
    if not torch.isfinite(reference).all().item():
        raise ValueError("PyTorch result must be finite")
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.export.save(program, output_dir / "model.pt2")
    (output_dir / "exported_graph.txt").write_text(str(program.graph_module.graph) + "\n")
    (output_dir / "abi.json").write_text(json.dumps(spec.manifest(), indent=2) + "\n")

    # 阶段 2：生成 buffer 形式 Linalg，再调用实际 C++ Pass 转成 npu.matmul。
    source = emit_linalg(spec)
    (output_dir / "01-linalg.mlir").write_text(source)
    lowered = run_tool([opt, "--convert-linalg-to-npu", "--verify-each"], source)
    (output_dir / "02-npu.mlir").write_text(lowered)
    # 指令流与数据流分开：IR 描述计算与类型/形状，这些列表才是设备实际读取的数值。
    av, bv = a.detach().flatten().tolist(), b.detach().flatten().tolist()
    # 后端执行 C += A*B；此处清零 C 才能实现 PyTorch 的 C = A@B。
    # Lab5 implements accumulation; a fresh zeroed C implements torch.matmul.
    initial_c = [0] * (spec.m * spec.n)
    scales, exact_integer = None, None
    if mode == "int8":
        # 两个动作必须配套：C++ Pass 改接口与元数据，Python 真正量化 A/B 数据。
        sa, sb = quantize.calibrate(av), quantize.calibrate(bv)
        scales = dict(a_scale=sa, b_scale=sb, c_scale=sa * sb)
        lowered = run_tool([opt, f"--npu-quantize-int8=a-scale={sa:.17g} b-scale={sb:.17g}",
                            "--verify-each"], lowered)
        (output_dir / "03-quantized.mlir").write_text(lowered)
        input_a, input_b = quantize.quantize_int8(av, sa), quantize.quantize_int8(bv, sb)
    else:
        input_a, input_b = av, bv
    # 阶段 3：将整矩阵运算展开为 tile，随后为 DRAM/SRAM 分配地址属性。
    tiled = run_tool([opt, f"--npu-tile=tile-size={tile_size}", "--verify-each"], lowered)
    (output_dir / "04-tiled.mlir").write_text(tiled)
    planned = run_tool([opt, f"--npu-plan-memory=sram-bytes={sram_bytes}",
                        "--verify-each"], tiled)
    (output_dir / "05-planned.mlir").write_text(planned)
    # 阶段 4：Emitter 将规划后的 NPU IR 发射成文本伪指令，不经过 LLVM IR。
    isa = run_tool([translate, "-"], planned)
    (output_dir / "program.npu").write_text(isa)
    # 阶段 5：把指令和量化/浮点输入一起交给设备功能模型，获取真实模拟结果。
    result = simulator.execute(isa, [input_a, input_b, initial_c])[0]
    if mode == "int8":
        # 先验证整数计算精确正确，再反量化讨论它与原始浮点计算的误差。
        expected = [sum(input_a[row * spec.k + red] * input_b[red * spec.n + col]
                        for red in range(spec.k))
                    for row in range(spec.m) for col in range(spec.n)]
        if result["values"] != expected or result["quantization"] != scales:
            raise AssertionError("INT8 result/scales differ from independent integer reference")
        exact_integer = True
        values = quantize.dequantize_accumulator(result["values"], sa, sb)
    else:
        values = result["values"]
    actual = torch.tensor(values, dtype=torch.float32).reshape(spec.m, spec.n)
    error = (actual - reference).abs()
    if mode == "fp32":
        # FP32 参考与模拟器的运算顺序/FMA 策略可能不同，因此按容差比较。
        # CPU BLAS may use FMA/reorder additions; Lab5 rounds mul and add separately.
        torch.testing.assert_close(actual, reference, rtol=1e-4, atol=1e-5)
        bound = None
    else:
        # No clipping after max-abs calibration: account for input rounding and
        # measured PyTorch-vs-double accumulation differences at each position.
        # 利用 |eA|<=sa/2、|eB|<=sb/2 推导每个输出的误差界，
        # 再计入参考累加精度差异；这不是“任意量化误差都可以接受”。
        double_ref = (a.double() @ b.double()).flatten().tolist()
        ref_values = reference.flatten().tolist()
        bounds = [sum(abs(av[row * spec.k + red]) * sb / 2 +
                      abs(bv[red * spec.n + col]) * sa / 2 + sa * sb / 4
                      for red in range(spec.k)) +
                  abs(double_ref[row * spec.n + col] - ref_values[row * spec.n + col]) +
                  1e-6 * max(1, abs(ref_values[row * spec.n + col]))
                  for row in range(spec.m) for col in range(spec.n)]
        if any(abs(value - ref) > limit for value, ref, limit in zip(values, ref_values, bounds)):
            raise AssertionError("dequantized result exceeds the per-element rounding bound")
        bound = max(bounds)
    # 保留阶段 IR、输入/输出和误差报告，使一次失败能够脱离完整模型复现。
    report = dict(mode=mode, shape=dict(m=spec.m, n=spec.n, k=spec.k),
                  torch_version=torch.__version__, tile_size=tile_size, sram_bytes=sram_bytes,
                  max_abs_error=error.max().item(),
                  rmse=math.sqrt(error.double().square().mean().item()),
                  quantization=scales, integer_reference_exact=exact_integer,
                  max_element_error_bound=bound, output_initialization="zero-before-each-call",
                  passed=True)
    tensors = dict(a=a.tolist(), b=b.tolist(), initial_c=initial_c,
                   device_a=input_a, device_b=input_b, output_device=result["values"],
                   output=actual.tolist(), pytorch_reference=reference.tolist())
    (output_dir / "tensors.json").write_text(json.dumps(tensors, indent=2, allow_nan=False) + "\n")
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-dir", type=Path, default=BACKEND_DIR / "build")
    parser.add_argument("--output-dir", type=Path, default=LAB_DIR / "build/demo")
    parser.add_argument("--mode", choices=("fp32", "int8", "both"), default="both")
    parser.add_argument("--m", type=int, default=5)
    parser.add_argument("--n", type=int, default=6)
    parser.add_argument("--k", type=int, default=7)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tile-size", type=int, default=4)
    parser.add_argument("--sram-bytes", type=int, default=4096)
    parser.add_argument("--input", type=Path, help="JSON with two nested matrices a and b")
    args = parser.parse_args()
    if args.input:
        data = json.loads(args.input.read_text())
        a, b = (torch.tensor(data[key], dtype=torch.float32) for key in ("a", "b"))
    else:
        a, b = make_inputs(args.m, args.n, args.k, args.seed)
    modes = ("fp32", "int8") if args.mode == "both" else (args.mode,)
    for mode in modes:
        destination = args.output_dir / mode
        report = compile_and_run(a, b, args.backend_dir, destination, mode=mode,
                                 tile_size=args.tile_size, sram_bytes=args.sram_bytes)
        print(f"PASS: {mode}, max_abs_error={report['max_abs_error']:.8g}, artifacts: {destination}")


if __name__ == "__main__":
    main()
