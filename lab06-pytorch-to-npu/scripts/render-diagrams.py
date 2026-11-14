#!/usr/bin/env python3
"""Generate five native SVG diagrams; --png additionally requires CairoSVG."""
import argparse
import importlib.util
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("learning_diagrams", root.parent / "scripts/render-learning-diagrams.py")
diagrams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagrams)
diagrams.OUT = root / "docs/images"
diagrams.OUT.mkdir(parents=True, exist_ok=True)


def save_english(figure, name):
    # Diagrams use Latin text so PNG generation needs no extra Chinese font.
    figure.text(42, figure.height - 22, "MLIR learning labs - Lab6", 16, diagrams.GRAY)
    figure.parts.append("</svg>")
    path = diagrams.OUT / f"{name}.svg"
    path.write_text("\n".join(figure.parts) + "\n")
    return path


diagrams.Figure.save = save_english


def generate():
    return [
        diagrams.flow("pipeline", "Lab6: PyTorch to the teaching NPU", "Actual exported graph + actual input data + actual simulated instructions", [
            ("PyTorch", "forward(a, b)", "return a @ b"),
            ("torch.export", "ATen graph", "static metadata"),
            ("Small frontend", "validate graph", "emit Linalg"),
            ("Lab5 backend", "lower / tile", "plan / emit"),
            ("Simulator", "run FP32 / INT8", "compare outputs")],
            "A narrow frontend reuses the existing MLIR 20 backend."),
        diagrams.compare("frontend", "A frontend checks meaning, not just matrix sizes", "Unsupported operations are rejected before emitting MLIR.",
            "Exported graph", ["placeholder A", "placeholder B", "aten.matmul(A, B)", "output(matmul)"],
            "Accepted contract", ["Two CPU float32 rank-2 inputs", "Static shapes and contiguous layout", "Exactly one matmul in input order", "One direct result; no model state"],
            "Adding relu() must fail until a lowering is implemented."),
        diagrams.compare("abi", "Bridge a tensor result to an output-buffer ABI", "The frontend and host runtime must agree on the output initialization.",
            "PyTorch interface", ["Inputs: A, B", "Result: a new C", "C = A @ B"],
            "Lab5 interface", ["Arguments: A, B, C", "Caller clears C before EVERY call", "Backend executes C += A * B"],
            "A zeroed C makes both interfaces compute the same matrix product."),
        diagrams.flow("artifacts", "Inspect each representation", "Every successful run saves artifacts under build/demo/fp32 or build/demo/int8.", [
            ("Graph", "model.pt2", "exported_graph.txt"),
            ("Linalg", "01-linalg.mlir", "buffer ABI"),
            ("NPU", "02-npu.mlir", "03-quantized*"),
            ("Tiles", "04-tiled.mlir", "05-planned.mlir"),
            ("Instructions", "program.npu", "report.json")],
            "* Quantization is optional; stages 02 to 05 use the same NPU dialect."),
        diagrams.compare("validation", "Two execution paths, one numerical check", "The reference result is never substituted for the simulated device result.",
            "Reference path", ["Actual A and B", "PyTorch model(a, b)", "FP32 reference"],
            "Compiled path", ["Same A and B; quantize if INT8", "NPU pseudo-ISA + Lab5 simulator", "FP32 output or dequantized INT32"],
            "FP32: tolerance check. INT8: exact integer check + quantization bound."),
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    paths = generate()
    if args.png:
        import cairosvg
        for path in paths:
            cairosvg.svg2png(url=str(path), write_to=str(path.with_suffix(".png")))
    print(f"Generated {len(paths)} diagrams")
