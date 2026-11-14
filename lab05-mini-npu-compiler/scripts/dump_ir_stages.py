"""Save every Lab5 IR stage and the final pseudo-ISA, with a readable index.

Uses only Python stdlib and the existing Lab5 tools. INT8 mode demonstrates
IR/type lowering with supplied scales; it does not quantize a floating dataset.
"""
import argparse
import math
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]


def run(arguments, source=None):
    result = subprocess.run([str(x) for x in arguments], input=source,
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{' '.join(map(str, arguments))}\n{result.stderr}")
    return result.stdout


def dump(args):
    opt = args.build_dir / "npu-opt"
    translate = args.build_dir / "npu-translate"
    if not opt.is_file() or not translate.is_file():
        raise ValueError("先构建 Lab5：bash scripts/build-and-test.sh lab05-mini-npu-compiler")
    if not all(math.isfinite(x) and x > 0 for x in
               (args.a_scale, args.b_scale, args.a_scale * args.b_scale)):
        raise ValueError("scale 及其乘积必须有限且为正")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    modes = ("fp32", "int8") if args.mode == "both" else (args.mode,)
    document = ["# Lab5：逐阶段的实际 IR 与伪指令", "",
                "由 scripts/dump_ir_stages.py 调用实际编译工具生成；下面保留完整输出。", "",
                "输入是静态 buffer 矩阵乘加 C += A×B，不是自动清零的 C=A×B。", "",
                "INT8 分支只演示类型、scale 和指令变化；若运行实际浮点数据，仍须在宿主端按相同 scale 量化。", ""]
    for mode in modes:
        folder = args.output_dir / mode
        folder.mkdir(parents=True, exist_ok=True)
        document.extend([f"## {mode.upper()} 路径", ""])
        stages = []

        def save(filename, title, content, language="mlir"):
            (folder / filename).write_text(content)
            stages.append(filename)
            document.extend([f"### {title}", "", f"文件：[{mode}/{filename}]({mode}/{filename})", "",
                             f"```{language}", content.rstrip(), "```", ""])

        source = (LAB / "examples/matmul.mlir").read_text()
        save("00-linalg.mlir", "输入：Linalg buffer IR", source)
        source = run([opt, "--convert-linalg-to-npu", "--verify-each"], source)
        save("01-npu.mlir", "转换：linalg.matmul → npu.matmul", source)
        if mode == "int8":
            source = run([opt, f"--npu-quantize-int8=a-scale={args.a_scale:.17g} b-scale={args.b_scale:.17g}",
                          "--verify-each"], source)
            save("02-quantized.mlir", "可选量化：i8/i8/i32 接口与 scale", source)
        source = run([opt, f"--npu-tile=tile-size={args.tile_size}", "--verify-each"], source)
        save("03-tiled.mlir", "分块：一个 matmul → 多个 tile", source)
        source = run([opt, f"--npu-plan-memory=sram-bytes={args.sram_bytes}", "--verify-each"], source)
        save("04-planned.mlir", "规划：添加 DRAM/SRAM 地址与大小", source)
        program = run([translate, "-"], source)
        save("05-program.npu", "代码生成：离开 MLIR，输出伪指令", program, "text")
        # Generated random inputs validate instruction execution at its declared
        # dtype; this is not a real floating-data quantization accuracy test.
        report = run([sys.executable, LAB / "simulator.py", folder / "05-program.npu"])
        (folder / "simulation.txt").write_text(report)
        document.extend(["模拟器验证（其自行生成的测试数据，与独立参考计算比较）：", "",
                         "```text", report.rstrip(), "```", ""])
        print(f"{mode}: {len(stages)} 个阶段，{report.strip()}")
    (args.output_dir / "README.md").write_text("\n".join(document) + "\n")
    print(f"完整对照：{args.output_dir / 'README.md'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=LAB / "build")
    parser.add_argument("--output-dir", type=Path, default=LAB / "build/ir-stages")
    parser.add_argument("--mode", choices=("fp32", "int8", "both"), default="fp32")
    parser.add_argument("--tile-size", type=int, default=4)
    parser.add_argument("--sram-bytes", type=int, default=4096)
    parser.add_argument("--a-scale", type=float, default=0.125)
    parser.add_argument("--b-scale", type=float, default=0.25)
    dump(parser.parse_args())
