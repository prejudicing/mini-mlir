// CHECK-LABEL: func.func @main()
// CHECK: %[[A:.*]] = toy.constant 10 : i32
// CHECK: %[[B:.*]] = toy.constant 20 : i32
// CHECK: %[[SUM:.*]] = toy.add %[[A]], %[[B]] : i32
// CHECK: return %[[SUM]] : i32
module {
  func.func @main() -> i32 {
    %a = toy.constant 10 : i32
    %b = toy.constant 20 : i32
    %sum = toy.add %a, %b : i32
    return %sum : i32
  }
}
