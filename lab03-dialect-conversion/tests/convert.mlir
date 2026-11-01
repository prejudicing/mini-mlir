// RUN: %toy-opt %s --convert-toy-to-arith --verify-each | %FileCheck %s
// RUN: %toy-opt %s --convert-toy-to-arith | %toy-opt --convert-toy-to-arith | %FileCheck %s
// CHECK-NOT: toy.
// CHECK-LABEL: func.func @main()
// CHECK: %[[A:.*]] = arith.constant 10 : i32
// CHECK: %[[Z:.*]] = arith.constant 0 : i32
// CHECK: %[[B:.*]] = arith.addi %[[A]], %[[Z]] : i32
// CHECK: %[[C:.*]] = arith.addi %[[B]], %[[Z]] : i32
// CHECK: return %[[C]] : i32
// CHECK-NOT: toy.
// CHECK-LABEL: func.func @add64(
// CHECK: arith.addi
// CHECK: return
module {
  func.func @main() -> i32 {
    %a = toy.constant 10 : i32
    %zero = toy.constant 0 : i32
    %b = toy.add %a, %zero : i32
    %c = toy.add %b, %zero : i32
    return %c : i32
  }
  func.func @add64(%a: i64, %b: i64) -> i64 {
    %sum = toy.add %a, %b : i64
    return %sum : i64
  }
}
