"""小型辅助程序：精确检查 calculator 的失败状态，再输出诊断供 FileCheck 匹配。"""
import subprocess
import sys

completed = subprocess.run(sys.argv[1:], text=True, capture_output=True)
if completed.returncode != 2 or completed.stdout:
    sys.exit(f"expected exit 2 and empty stdout; got {completed!r}")
sys.stdout.write(completed.stderr)
