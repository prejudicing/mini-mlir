from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from simulator import simulate

opt, translate = sys.argv[1:]


def run(args, text):
    result = subprocess.run(args, input=text, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout


def kernel(m, n, k, repeats=1):
    at, bt, ct = f"memref<{m}x{k}xf32>", f"memref<{k}x{n}xf32>", f"memref<{m}x{n}xf32>"
    body = f"linalg.matmul ins(%a, %b : {at}, {bt}) outs(%c : {ct})\n" * repeats
    return f"module {{ func.func @test(%a: {at}, %b: {bt}, %c: {ct}) {{ {body} return }} }}"


cases = 0
for m, n, k in [(1, 1, 1), (5, 6, 7), (3, 2, 9), (8, 8, 8), (2, 9, 1)]:
    for tile in [1, 2, 4, 8]:
        planned = run([opt, f"--npu-compile=tile-size={tile}", "--verify-each"], kernel(m, n, k))
        isa = run([translate, "-"], planned)
        for seed in [0, 17, 42]:
            simulate(isa, seed)
            cases += 1

planned = run([opt, "--npu-compile"], kernel(5, 6, 7, repeats=2))
simulate(run([translate, "-"], planned), 23, repeats=2)
cases += 1
print(f"PASS: {cases} numerical cases (tile boundaries, K accumulation, nonzero C, scratch reuse)")

for option, expected in [("tile-size=0", "tile-size must be"),
                         ("tile-size=65", "tile-size must be"),
                         ("sram-bytes=0", "sram-bytes must be positive")]:
    result = subprocess.run([opt, f"--npu-compile={option}"], input=kernel(2, 2, 2), text=True, capture_output=True)
    assert result.returncode != 0 and expected in result.stderr

reordered = kernel(2, 2, 2).replace("ins(%a, %b", "ins(%b, %a")
result = subprocess.run([opt, "--npu-compile"], input=reordered, text=True, capture_output=True)
assert result.returncode != 0 and "failed to legalize" in result.stderr

unplanned = run([opt, "--convert-linalg-to-npu"], kernel(2, 2, 2))
result = subprocess.run([translate, "-"], input=unplanned, text=True, capture_output=True)
assert result.returncode != 0 and "missing memory plan" in result.stderr and not result.stdout

# 发射器重新校验地址，不能信任手工篡改后的规划属性。
forged = planned.replace("npu.address = 192", "npu.address = 0", 1)
assert forged != planned
result = subprocess.run([translate, "-"], input=forged, text=True, capture_output=True)
assert result.returncode != 0 and "invalid or overlapping DRAM" in result.stderr and not result.stdout
print("PASS: invalid options, reordered buffers, unplanned input and overlapping addresses rejected")
