"""A deliberately small torch.export -> Linalg-on-buffers frontend.

This is not Torch-MLIR or a general tensor bufferization pass. It validates
the actual exported graph before specializing it to Lab5's static A/B/C ABI.
"""
from dataclasses import asdict, dataclass

import torch
from torch.export.graph_signature import InputKind, OutputKind


@dataclass(frozen=True)
# 只保存编译需要的静态 M/N/K；实际张量数据由 run.py 单独传给模拟器。
class MatmulSpec:
    m: int
    n: int
    k: int

    # ABI 是调用约定：参数顺序、布局，以及每次执行前必须清零输出 C。
    def manifest(self):
        return dict(**asdict(self), dtype="f32", layout="row-major",
                    arguments=["A", "B", "C"], output="C",
                    output_initialization="zero-before-each-call",
                    semantics="C = A @ B", backend_semantics="C += A * B")


# 将前端接受范围限制为后端真正支持的类型和布局，避免生成无法执行的 IR。
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
    # 参数/常量状态也会出现在导出签名中；本实验只接受两个纯用户输入。
    signature = program.graph_signature
    if (len(signature.input_specs) != 2 or
            any(s.kind != InputKind.USER_INPUT for s in signature.input_specs) or
            len(signature.output_specs) != 1 or
            signature.output_specs[0].kind != OutputKind.USER_OUTPUT or
            program.state_dict or program.constants or program.range_constraints):
        raise ValueError("expected two user inputs, one output, no state or dynamic shapes")
    # 检查图的结构和连接关系；不能只看到一个 matmul 名字就忽略额外计算。
    nodes = list(program.graph.nodes)
    if ([node.op for node in nodes] !=
            ["placeholder", "placeholder", "call_function", "output"]):
        raise ValueError("only a single matrix multiplication is supported; extra operations rejected")
    a, b, product, output = nodes
    if (product.target not in (torch.ops.aten.matmul.default, torch.ops.aten.mm.default)
            or product.args != (a, b) or product.kwargs
            or output.args != ((product,),)):
        raise ValueError("expected exactly A @ B in input order and its direct output")
    # meta["val"] 提供形状/类型元数据（通常是 FakeTensor），不是要执行的实际数据。
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
    # 捕获真实 ATen 图；eval 设置推理模式，strict=True 使用严格导出路径。
    program = torch.export.export(model.eval(), (a, b), strict=True)
    return program, analyze_exported(program)


def emit_linalg(spec):
    """Lower the validated operation directly to Lab5's output-buffer ABI.

    The caller MUST initialize C to zero on every invocation. This contract
    replaces allocating/filling a tensor result; it is recorded in abi.json.
    """
    # 这里直接拼出 Linalg-on-Buffers 文本，没有执行 Tensor IR -> MemRef 的 Bufferization。
    a = f"memref<{spec.m}x{spec.k}xf32>"
    b = f"memref<{spec.k}x{spec.n}xf32>"
    c = f"memref<{spec.m}x{spec.n}xf32>"
    return ("// ABI: A, B, C are distinct contiguous buffers; C must be zeroed per call.\n"
            f"module {{\n  func.func @matmul(%a: {a}, %b: {b}, %c: {c}) {{\n"
            f"    linalg.matmul ins(%a, %b : {a}, {b}) outs(%c : {c})\n"
            "    return\n  }\n}\n")
