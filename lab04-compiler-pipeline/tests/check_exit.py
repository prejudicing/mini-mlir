import subprocess
import sys
result = subprocess.run(sys.argv[1:3])
expected = int(sys.argv[3])
if result.returncode != expected:
    raise SystemExit(f"expected exit {expected}, got {result.returncode}")
print(f"PASS: LLVM IR executes with exit code {expected}")
