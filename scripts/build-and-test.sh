#!/usr/bin/env bash
set -euo pipefail
root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
llvm_prefix=${LLVM_PREFIX:-/usr/lib/llvm-20}
jobs=${JOBS:-2}
labs=(lab00-cmake-demo lab00-cpp-analyzer lab01-pattern-rewrite lab02-toy-dialect
      lab03-dialect-conversion lab04-compiler-pipeline lab05-mini-npu-compiler)
if (( $# > 0 )); then
  labs=("$@")
fi
for lab in "${labs[@]}"; do
  case "$lab" in
    lab00-cmake-demo|lab00-cpp-analyzer|lab01-pattern-rewrite|lab02-toy-dialect|lab03-dialect-conversion|lab04-compiler-pipeline|lab05-mini-npu-compiler) ;;
    *) printf 'Unknown lab: %s\n' "$lab" >&2; exit 1 ;;
  esac
  printf '\nBuilding and testing %s\n' "$lab"
  cmake -S "$root_dir/$lab" -B "$root_dir/$lab/build" -G Ninja \
    -DMLIR_DIR="$llvm_prefix/lib/cmake/mlir" \
    -DLLVM_DIR="$llvm_prefix/lib/cmake/llvm"
  cmake --build "$root_dir/$lab/build" -j "$jobs"
  case "$lab" in
    lab00-cmake-demo) "$root_dir/$lab/build/my_program" ;;
    lab00-cpp-analyzer) "$root_dir/$lab/build/mlir-analyzer" "$root_dir/$lab/test.mlir" ;;
    *) ctest --test-dir "$root_dir/$lab/build" --output-on-failure --no-tests=error ;;
  esac
done
printf '\nAll requested labs passed.\n'
