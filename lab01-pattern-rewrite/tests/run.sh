#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
binary=${1:-"$project_dir/build/mlir-pattern-rewrite"}
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

for input in "$project_dir/test.mlir" "$project_dir/tests/edge-cases.mlir"; do
  mlir-opt-20 "$input" --verify-each > /dev/null
  "$binary" "$input" > "$temp_dir/output.mlir"
  FileCheck-20 "$input" < "$temp_dir/output.mlir"
  mlir-opt-20 "$temp_dir/output.mlir" --verify-each > /dev/null

  # 再运行一次，输出应保持不变：已达到此规则的不动点。
  "$binary" "$temp_dir/output.mlir" > "$temp_dir/second.mlir"
  diff -u "$temp_dir/output.mlir" "$temp_dir/second.mlir"
  printf 'PASS: %s (rewrite, verifier, idempotence)\n' "$(basename "$input")"
done

# 命令行用法错误、解析失败都必须返回非零状态。
if "$binary" > /dev/null 2>&1; then
  printf 'FAIL: missing argument accepted\n' >&2
  exit 1
fi
printf 'module { invalid.operation }\n' > "$temp_dir/invalid.mlir"
if "$binary" "$temp_dir/invalid.mlir" > /dev/null 2>&1; then
  printf 'FAIL: invalid input accepted\n' >&2
  exit 1
fi
printf 'PASS: error handling\n'
