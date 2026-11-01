"""Execute the FP32/INT8 teaching ISA; addresses are bytes, strides are elements.

python3 simulator.py program.npu [seed]
execute() accepts real host data; simulate() additionally checks a scalar reference.
"""
import math
import random
import struct
import sys
from pathlib import Path


def f32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


def wrap_i32(value):
    return ((value + (1 << 31)) % (1 << 32)) - (1 << 31)


def execute(program, inputs=None, seed=0):
    """Return kernel results; inputs is [A, B, C] or a name -> [A, B, C] map.

    Matrices are flat row-major lists. C is an initial accumulator, not zeroed.
    Memory cells track their byte widths to detect malformed mixed-width DMA.
    """
    rng = random.Random(seed)
    active = False
    results = []
    dram, sram, buffers = {}, {}, []
    peak, name, quant = 0, "", None

    def local(address, width):
        assert width in (1, 4) and address % width == 0
        assert 0 <= address and address + width <= peak, "SRAM access out of bounds"
        return address

    def read_sram(address, width):
        value, actual_width = sram[local(address, width)]
        assert actual_width == width, "SRAM element width mismatch"
        return value

    for line in program.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        opcode = parts[0]
        fields = dict(item.split("=", 1) for item in parts[2 if opcode == "FUNC" else 1:])
        if opcode == "FUNC":
            assert not active
            active, name, peak, quant = True, parts[1], int(fields["sram"]), None
            dram, sram, buffers = {}, {}, []
        elif opcode == "QUANT":
            assert active and quant is None and not buffers
            assert fields["scheme"] == "symmetric-per-tensor"
            quant = {key: float(fields[key]) for key in ("a_scale", "b_scale", "c_scale")}
            assert all(math.isfinite(x) and x > 0 for x in quant.values())
            assert math.isclose(quant["c_scale"], quant["a_scale"] * quant["b_scale"], rel_tol=1e-15)
        elif opcode == "BUFFER":
            assert active and int(fields["id"]) == len(buffers) and len(buffers) < 3
            base, rows, cols = (int(fields[key]) for key in ("g", "rows", "cols"))
            dtype = fields.get("dtype", "f32")
            assert dtype in ("f32", "i8", "i32") and rows > 0 and cols > 0 and base % 64 == 0
            width = 1 if dtype == "i8" else 4
            host = inputs[name] if isinstance(inputs, dict) else inputs
            if host is not None:
                assert isinstance(inputs, dict) or not results, "pass a name map for multiple kernels"
                assert len(host) == 3
                values = list(host[len(buffers)])
                assert len(values) == rows * cols
            elif dtype == "f32":
                values = [rng.randint(-16, 16) / 8 for _ in range(rows * cols)]
            else:
                lo, hi = (-128, 127) if dtype == "i8" else (-1000, 1000)
                values = [rng.randint(lo, hi) for _ in range(rows * cols)]
                if dtype == "i8":
                    values[:min(2, len(values))] = [-128, 127][:len(values)]
            if dtype == "f32":
                assert all(math.isfinite(x) for x in values)
                values = [f32(x) for x in values]
            else:
                lo, hi = (-128, 127) if dtype == "i8" else (-(1 << 31), (1 << 31) - 1)
                assert all(type(x) is int and lo <= x <= hi for x in values), "integer host value out of range"
            for i, value in enumerate(values):
                address = base + i * width
                assert address not in dram, "overlapping global buffers"
                dram[address] = (value, width)
            buffers.append(dict(base=base, rows=rows, cols=cols, dtype=dtype, width=width, initial=values))
            if len(buffers) == 3:
                assert tuple(b["dtype"] for b in buffers) in (("f32", "f32", "f32"), ("i8", "i8", "i32"))
                assert quant is None or dtype == "i32"
        elif opcode in ("LOAD2D", "STORE2D"):
            assert active and len(buffers) == 3
            p = {key: int(value) for key, value in fields.items()}
            width = p.get("bytes", 4)
            for row in range(p["rows"]):
                for col in range(p["cols"]):
                    g = p["g"] + (row * p["stride"] + col) * width
                    s = local(p["s"] + (row * p["cols"] + col) * width, width)
                    assert g in dram and dram[g][1] == width, "DRAM access/element width mismatch"
                    if opcode == "LOAD2D":
                        sram[s] = dram[g]
                    else:
                        dram[g] = (read_sram(s, width), width)
        elif opcode in ("MATMUL", "MATMUL_I8"):
            assert active and len(buffers) == 3
            p = {key: int(value) for key, value in fields.items()}
            m, n, k = (p[key] for key in ("m", "n", "k"))
            width = 1 if opcode == "MATMUL_I8" else 4
            assert m > 0 and n > 0 and k > 0
            for row in range(m):
                for col in range(n):
                    c = local(p["c"] + (row * n + col) * 4, 4)
                    value = read_sram(c, 4)
                    for red in range(k):
                        a = read_sram(p["a"] + (row * k + red) * width, width)
                        b = read_sram(p["b"] + (red * n + col) * width, width)
                        value = wrap_i32(value + a * b) if width == 1 else f32(value + f32(a * b))
                    sram[c] = (value, 4)
        elif opcode == "END":
            assert active and len(buffers) == 3
            a, b, c = buffers
            assert (a["cols"], c["rows"], c["cols"]) == (b["rows"], a["rows"], b["cols"])
            for source in (a, b):
                assert [dram[source["base"] + i * source["width"]][0] for i in range(len(source["initial"]))] == source["initial"], "input buffer was modified"
            values = [dram[c["base"] + i * 4][0] for i in range(len(c["initial"]))]
            results.append(dict(name=name, buffers=buffers, values=values, quantization=quant))
            active = False
        else:
            raise AssertionError(f"unknown instruction: {opcode}")
    assert not active and results, "incomplete or empty program"
    return results


def simulate(program, seed=0, repeats=1, inputs=None):
    reports = []
    for result in execute(program, inputs, seed):
        a, b, c = result["buffers"]
        m, n, k = a["rows"], b["cols"], a["cols"]
        expected = list(c["initial"])
        integer = a["dtype"] == "i8"
        for _ in range(repeats):
            for row in range(m):
                for col in range(n):
                    pos = row * n + col
                    if integer:
                        # 独立大整数参考：完整点积后再按模 2^32 解释为有符号值。
                        total = expected[pos] + sum(a["initial"][row * k + red] * b["initial"][red * n + col] for red in range(k))
                        bits = total & 0xFFFFFFFF
                        expected[pos] = bits - 0x100000000 if bits >= 0x80000000 else bits
                    else:
                        for red in range(k):
                            expected[pos] = f32(expected[pos] + f32(a["initial"][row * k + red] * b["initial"][red * n + col]))
        error = max(abs(x - y) for x, y in zip(result["values"], expected))
        assert (error == 0 if integer else error <= 1e-5), f"incorrect result, max error={error}"
        suffix = " (INT8 exact)" if integer else ""
        reports.append(f"PASS: {m}x{k} @ {k}x{n}, initial C preserved, max error={error}{suffix}")
    return reports


if __name__ == "__main__":
    for report in simulate(Path(sys.argv[1]).read_text(), int(sys.argv[2]) if len(sys.argv) > 2 else 0):
        print(report)
