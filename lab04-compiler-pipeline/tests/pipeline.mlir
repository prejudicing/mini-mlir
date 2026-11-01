// RUN: %compiler-opt %s --lab4-optimize --verify-each 2>%t.log | %FileCheck %s
// RUN: %FileCheck %s --check-prefix=STATS < %t.log
// RUN: %compiler-opt %s --lab4-lower-to-llvm --verify-each 2>/dev/null | %FileCheck %s --check-prefix=LLVM
// RUN: %compiler-opt %s --lab4-lower-to-llvm 2>/dev/null | %translate --mlir-to-llvmir > %t.ll
// RUN: %python %S/check_exit.py %lli %t.ll 30
// CHECK-LABEL: func.func @main()
// CHECK: %[[C:.*]] = arith.constant 30 : i32
// CHECK-NOT: arith.addi
// CHECK: return %[[C]] : i32
// STATS: [lab4-analysis] total={{[0-9]+}} toy.add=3 arith.addi=0
// STATS: [lab4-analysis] total={{[0-9]+}} toy.add=0 arith.addi=0
// LLVM-LABEL: llvm.func @main()
// LLVM: %[[C:.*]] = llvm.mlir.constant(30 : i32)
// LLVM: llvm.return %[[C]] : i32
module {
  func.func @main() -> i32 {
    %a = toy.constant 10 : i32
    %b = toy.constant 20 : i32
    %zero = toy.constant 0 : i32
    %sum = toy.add %a, %b : i32
    %x = toy.add %sum, %zero : i32
    %y = toy.add %x, %zero : i32
    return %y : i32
  }
}
