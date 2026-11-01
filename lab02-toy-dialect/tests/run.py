"""Run round-trip, FileCheck and verifier checks using only Python stdlib."""

from pathlib import Path
import subprocess
import sys


def run(args, *, text=None):
    result = subprocess.run(args, input=text, text=True, capture_output=True)
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise SystemExit(f"FAILED: {' '.join(map(str, args))}")
    return result.stdout


tool, filecheck, builder = sys.argv[1:]
root = Path(__file__).resolve().parent.parent
for source in [root / "test.mlir", root / "tests/valid.mlir"]:
    output = run([tool, str(source), "--verify-each"])
    run([filecheck, str(source)], text=output)
    assert run([tool], text=output) == output, "Round trip changed the IR"
    generic = run([tool, "--mlir-print-op-generic"], text=output)
    assert run([tool], text=generic) == output, "Generic round trip changed the IR"
    print(f"PASS: {source.name} (FileCheck, round trip, generic syntax)")

run([tool, str(root / "tests/invalid.mlir"),
     "--split-input-file", "--verify-diagnostics"])
print("PASS: invalid.mlir (five expected verifier diagnostics)")

# verify-diagnostics 在诊断符合预期时返回成功；另外确认普通模式真的拒绝非法 IR。
bad = "module { func.func @bad() -> i8 { %c = toy.constant 1 : i8 return %c : i8 } }"
result = subprocess.run([tool], input=bad, text=True, capture_output=True)
assert result.returncode != 0, "Invalid IR was accepted"
assert "only supports scalar i32 or i64" in result.stderr
print("PASS: invalid IR returns nonzero exit status")

built = run([builder])
run([tool], text=built)
run([filecheck, str(root / "test.mlir")], text=built)
print("PASS: C++ builder output matches the input example")
