"""A deliberately small torch.export -> Linalg-on-buffers frontend.

This is not Torch-MLIR or a general tensor bufferization pass. It validates
the actual exported graph before specializing it to Lab5's static A/B/C ABI.
"""
from dataclasses import asdict, dataclass

import torch
from torch.export.graph_signature import InputKind, OutputKind


@dataclass(frozen=True)
class MatmulSpec:
    m: int
    n: int
    k: int

    def manifest(self):
        return dict(**asdict(self), dtype="f32", layout="row-major",
                    arguments=["A", "B", "C"], output="C",
                    output_initialization="zero-before-each-call",
                    semantics="C = A @ B", backend_semantics="C += A * B")


def check_tensor(value, label):
    if not isinstance(value, torch.Tensor):
        raise ValueError(f"{label}: expected a Tensor")
    if value.dtype != torch.float32 or value.device.type != "cpu":
        raise ValueError(f"{label}: only CPU float32 tensors are supported")
    if value.layout != torch.strided or value.ndim != 2 or not value.is_contiguous():
        raise ValueError(f"{label}: expected a contiguous rank-2 tensor")
    if any(type(dim) is not int or not 1 <= dim <= 4096 for dim in value.shape):
        raise ValueError(f"{label}: dimensions must be static integers in [1, 4096]")


def analyze_exported(program):
    """Accept only (A, B) -> aten.matmul(A, B), with one tensor result."""
    signature = program.graph_signature
    if (len(signature.input_specs) != 2 or
            any(s.kind != InputKind.USER_INPUT for s in signature.input_specs) or
            len(signature.output_specs) != 1 or
            signature.output_specs[0].kind != OutputKind.USER_OUTPUT or
            program.state_dict or program.constants or program.range_constraints):
        raise ValueError("expected two user inputs, one output, no state or dynamic shapes")
    nodes = list(program.graph.nodes)
    if ([node.op for node in nodes] !=
            ["placeholder", "placeholder", "call_function", "output"]):
        raise ValueError("only a single matrix multiplication is supported; extra operations rejected")
    a, b, product, output = nodes
    if (product.target not in (torch.ops.aten.matmul.default, torch.ops.aten.mm.default)
            or product.args != (a, b) or product.kwargs
            or output.args != ((product,),)):
        raise ValueError("expected exactly A @ B in input order and its direct output")
    values = [node.meta.get("val") for node in (a, b, product)]
    for label, value in zip(("A", "B", "result"), values):
        check_tensor(value, label)
    av, bv, cv = values
    m, k = av.shape
    kb, n = bv.shape
    if k != kb or tuple(cv.shape) != (m, n):
        raise ValueError("matrix/result shapes are inconsistent")
    return MatmulSpec(m, n, k)


def export_model(model, a, b):
    for label, value in (("A", a), ("B", b)):
        check_tensor(value, label)
        if not torch.isfinite(value).all().item():
            raise ValueError(f"{label}: all values must be finite")
    if a.shape[1] != b.shape[0]:
        raise ValueError("A columns must equal B rows")
    program = torch.export.export(model.eval(), (a, b), strict=True)
    return program, analyze_exported(program)


def emit_linalg(spec):
    """Lower the validated operation directly to Lab5's output-buffer ABI.

    The caller MUST initialize C to zero on every invocation. This contract
    replaces allocating/filling a tensor result; it is recorded in abi.json.
    """
    a = f"memref<{spec.m}x{spec.k}xf32>"
    b = f"memref<{spec.k}x{spec.n}xf32>"
    c = f"memref<{spec.m}x{spec.n}xf32>"
    return ("// ABI: A, B, C are distinct contiguous buffers; C must be zeroed per call.\n"
            f"module {{\n  func.func @matmul(%a: {a}, %b: {b}, %c: {c}) {{\n"
            f"    linalg.matmul ins(%a, %b : {a}, {b}) outs(%c : {c})\n"
            "    return\n  }\n}\n")
