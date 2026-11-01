// RUN: %compiler-opt %s --lab4-optimize --verify-each 2>/dev/null | %FileCheck %s
// CHECK-LABEL: func.func @identity(
// CHECK-SAME: %[[X:.*]]: i64)
// CHECK-NOT: arith.addi
// CHECK: return %[[X]] : i64
// CHECK-LABEL: func.func @sum(
// CHECK: arith.addi
// CHECK: return
module {
  func.func @identity(%x: i64) -> i64 {
    %z = toy.constant 0 : i64
    %a = toy.add %x, %z : i64
    %b = toy.add %a, %z : i64
    return %b : i64
  }
  func.func @sum(%x: i64, %y: i64) -> i64 {
    %a = toy.add %x, %y : i64
    return %a : i64
  }
}
